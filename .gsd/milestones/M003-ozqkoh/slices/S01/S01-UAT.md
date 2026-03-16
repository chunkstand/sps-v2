# S01: Reviewer API authority boundary — UAT

**Milestone:** M003-ozqkoh
**Written:** 2026-03-15

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: S01's entire proof is the HTTP → Postgres → Temporal signal → workflow resume path against a real docker-compose stack. Artifact-only or unit checks cannot prove signal delivery or workflow resume. The integration test and runbook together cover all assertion surfaces.

## Preconditions

1. docker-compose stack is running: `docker compose up -d` (services: `postgres`, `temporal`, `temporal-ui`)
2. Alembic migrations applied: `docker compose exec postgres psql -U sps -d sps -c "\dt"` shows `review_decisions` and `case_transition_ledger` tables
3. Temporal worker running: `python -m sps.workflows.worker` (or via docker-compose `api` service)
4. FastAPI server running on `http://localhost:8000`
5. `SPS_REVIEWER_API_KEY` env var set (default: `dev-reviewer-key`)
6. A `PermitCase` exists in Postgres for the `case_id` used in tests, or the `ensure_permit_case_exists` activity is registered (worker handles this)

**Quick pre-flight:** `curl -s http://localhost:8000/healthz` → `{"status":"ok"}`

---

## Smoke Test

Confirm the reviewer endpoint is reachable and the auth guard is active:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/reviews/decisions
```

**Expected:** `401` — confirms the auth middleware is live without a valid API key.

---

## Test Cases

### 1. Happy path — HTTP POST unblocks a waiting workflow

**Goal:** Prove the full HTTP → Postgres → Temporal signal → workflow resume → `APPROVED_FOR_SUBMISSION` chain.

**Automated:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py::test_reviewer_api_unblocks_workflow -v -s`

**Manual steps (operator-style):**

1. Start a workflow: use the operator CLI or the temporal UI to start `PermitCaseWorkflow` for a fresh `case_id`. Note the `case_id`.
2. Wait for the workflow to reach `REVIEW_PENDING` — confirm via:
   ```bash
   docker compose exec postgres psql -U sps -d sps -c \
     "SELECT event_type, to_state FROM case_transition_ledger WHERE case_id = '<case_id>' ORDER BY created_at;"
   ```
   Expected rows include `APPROVAL_GATE_DENIED` (workflow paused in `REVIEW_PENDING`).
3. POST a review decision:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -X POST http://localhost:8000/api/v1/reviews/decisions \
     -H "Content-Type: application/json" \
     -H "X-Reviewer-Api-Key: dev-reviewer-key" \
     -d '{
       "decision_id": "DEC-test-001",
       "idempotency_key": "review/permit-case/<case_id>/run-001",
       "case_id": "<case_id>",
       "reviewer_id": "reviewer-alice",
       "outcome": "ACCEPT",
       "notes": "UAT manual acceptance"
     }'
   ```
4. **Expected:** HTTP `201`; response body includes `decision_id`, `outcome: "ACCEPT"`, `idempotency_key`.
5. Assert `review_decisions` row:
   ```bash
   docker compose exec postgres psql -U sps -d sps -c \
     "SELECT decision_id, idempotency_key, outcome FROM review_decisions WHERE decision_id = 'DEC-test-001';"
   ```
   **Expected:** One row with the correct `decision_id` and `outcome`.
6. Wait ~5s, then check the ledger:
   ```bash
   docker compose exec postgres psql -U sps -d sps -c \
     "SELECT event_type, to_state FROM case_transition_ledger WHERE case_id = '<case_id>' ORDER BY created_at;"
   ```
7. **Expected:** Final row is `CASE_STATE_CHANGED / APPROVED_FOR_SUBMISSION` — workflow completed.
8. Check API logs for the decision lifecycle sequence:
   ```bash
   docker compose logs api | grep reviewer_api
   ```
   **Expected:** Lines for `decision_received`, `decision_persisted`, `signal_sent` — in order; no `signal_failed`.

---

### 2. Idempotency — same key, identical payload returns 200

**Goal:** Prove that re-POSTing with the same `idempotency_key` AND same `decision_id` is a safe no-op (idempotent OK).

1. Use the same POST from Test Case 1 (same `decision_id` + same `idempotency_key`).
2. POST the exact same request body a second time.
3. **Expected:** HTTP `200`; response body includes `decision_id` matching the original.
4. Assert no duplicate row in `review_decisions`:
   ```bash
   docker compose exec postgres psql -U sps -d sps -c \
     "SELECT COUNT(*) FROM review_decisions WHERE idempotency_key = 'review/permit-case/<case_id>/run-001';"
   ```
   **Expected:** `count = 1`.

---

### 3. Idempotency conflict — same key, different decision_id returns 409

**Goal:** Prove that a conflicting second write is rejected with a stable error shape.

**Automated:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py::test_reviewer_api_idempotency_conflict_409 -v -s`

**Manual steps:**

1. POST a review decision as in Test Case 1 (succeeds with 201). Note `idempotency_key` and `decision_id`.
2. POST again with the **same `idempotency_key`** but a **different `decision_id`**:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -X POST http://localhost:8000/api/v1/reviews/decisions \
     -H "Content-Type: application/json" \
     -H "X-Reviewer-Api-Key: dev-reviewer-key" \
     -d '{
       "decision_id": "DEC-test-CONFLICT",
       "idempotency_key": "review/permit-case/<case_id>/run-001",
       "case_id": "<case_id>",
       "reviewer_id": "reviewer-alice",
       "outcome": "ACCEPT",
       "notes": "This is a conflicting write"
     }'
   ```
3. **Expected:** HTTP `409`; response body:
   ```json
   {
     "error": "IDEMPOTENCY_CONFLICT",
     "existing_decision_id": "DEC-test-001",
     "idempotency_key": "review/permit-case/<case_id>/run-001"
   }
   ```
4. Assert only the original row persists:
   ```bash
   docker compose exec postgres psql -U sps -d sps -c \
     "SELECT decision_id FROM review_decisions WHERE idempotency_key = 'review/permit-case/<case_id>/run-001';"
   ```
   **Expected:** Only `DEC-test-001` — no `DEC-test-CONFLICT` row.

---

### 4. Auth guard — missing API key returns 401

1. POST without the `X-Reviewer-Api-Key` header:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -X POST http://localhost:8000/api/v1/reviews/decisions \
     -H "Content-Type: application/json" \
     -d '{"decision_id": "DEC-no-auth"}'
   ```
2. **Expected:** HTTP `401`; body `{"detail": {"error": "missing_api_key", "hint": "Supply X-Reviewer-Api-Key header"}}`.

---

### 5. Auth guard — wrong API key returns 401

1. POST with an incorrect API key:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -X POST http://localhost:8000/api/v1/reviews/decisions \
     -H "Content-Type: application/json" \
     -H "X-Reviewer-Api-Key: totally-wrong-key" \
     -d '{"decision_id": "DEC-wrong-auth"}'
   ```
2. **Expected:** HTTP `401`; body `{"detail": {"error": "invalid_api_key"}}`.

---

### 6. Read-only decision inspection

1. After Test Case 1, GET the decision:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -H "X-Reviewer-Api-Key: dev-reviewer-key" \
     http://localhost:8000/api/v1/reviews/decisions/DEC-test-001
   ```
2. **Expected:** HTTP `200`; body includes `decision_id: "DEC-test-001"`, `outcome: "ACCEPT"`, `case_id`.

---

### 7. Decision not found — 404

1. GET a non-existent decision:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" \
     -H "X-Reviewer-Api-Key: dev-reviewer-key" \
     http://localhost:8000/api/v1/reviews/decisions/DEC-does-not-exist
   ```
2. **Expected:** HTTP `404`.

---

## Edge Cases

### Signal delivery failure leaves Postgres row durable

**Scenario:** Temporal becomes unreachable between the Postgres commit and the signal dispatch.

1. Simulate by stopping Temporal: `docker compose stop temporal`
2. POST a review decision (new unique `decision_id` + `idempotency_key`).
3. **Expected:** HTTP `201` (Postgres write succeeded); `review_decisions` row is present in Postgres.
4. Check API logs: `docker compose logs api | grep reviewer_api` — expect `reviewer_api.signal_failed signal_error=...`; the `signal_sent` line will be absent.
5. Restart Temporal: `docker compose start temporal`
6. Re-signal manually:
   ```bash
   temporal workflow signal \
     --workflow-id permit-case/<case_id> \
     --name ReviewDecision \
     --input '{"decision_id":"<id>","decision_outcome":"ACCEPT","reviewer_id":"reviewer-alice"}'
   ```
7. **Expected:** Workflow resumes and completes `APPROVED_FOR_SUBMISSION`.

---

### Full runbook

Run the operator runbook end-to-end:

```bash
bash scripts/verify_m003_s01.sh
```

**Expected:** Script exits 0; all assertion phases print `ok`; 401/409/201 paths all pass.

---

## Failure Signals

- HTTP `500` from POST/GET → check `docker compose logs api` for Python traceback; likely a DB connection or model schema issue
- HTTP `501` from POST → T02 stubs are still in place; re-verify the `sps.api.routes.reviews` import
- `workflow.review_received` absent from worker log after POST succeeds → `reviewer_api.signal_failed` in API logs; check Temporal connectivity
- `APPROVED_FOR_SUBMISSION` never appears in ledger → workflow stuck; confirm worker is registered with `ensure_permit_case_exists` + `apply_state_transition` activities and that signal was delivered
- `409` on first POST → stale `review_decisions` row with same `idempotency_key` from a prior test run; use a fresh `idempotency_key`
- `decision_id is None` RuntimeError in worker logs → legacy `ReviewDecisionSignal` sent without the API path; confirm POST endpoint is live and signal payload carries `decision_id`

---

## Requirements Proved By This UAT

- R006 — Reviewer service records ReviewDecision and unblocks workflows: HTTP POST is the sole writer of `review_decisions`; idempotency conflict returns 409 with stable error shape; Temporal signal unblocks the waiting workflow; workflow completes `APPROVED_FOR_SUBMISSION`; auth guard prevents unauthorized writes.

---

## Not Proven By This UAT

- R007 (self-approval / independence guard) — S02
- R008 (contradiction artifacts + advancement blocking) — S03
- R009 (dissent artifacts) — S04
- Signal-with-start (workflow not yet started when signal fires) — not implemented in S01; operational hardening deferred
- Rolling-quarter threshold metrics for independence enforcement — deferred to S02 or later

---

## Notes for Tester

- Use a unique `case_id` per test run to avoid ledger state from prior runs affecting assertions. The workflow ID convention is `permit-case/<case_id>`.
- The `idempotency_key` must be unique per test run unless intentionally testing the idempotency paths (Test Cases 2 and 3). A deterministic convention like `review/permit-case/<case_id>/<run_timestamp>` works well.
- The integration test (`tests/m003_s01_reviewer_api_boundary_test.py`) generates all IDs deterministically — no manual cleanup needed between runs.
- If you see `RuntimeError: ReviewDecisionSignal missing decision_id` in worker logs during m002 integration test runs: those tests send the old signal shape. Run them only via the updated m003 path or update them to use the HTTP API first.
- The runbook logs to `.gsd/runbook/m003_s01_worker_*.log` and `.gsd/runbook/m003_s01_api_*.log` for post-mortem inspection if it fails.
