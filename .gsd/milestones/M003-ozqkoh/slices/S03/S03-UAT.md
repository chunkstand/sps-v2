# S03: Contradiction artifacts + advancement blocking — UAT

**Milestone:** M003-ozqkoh  
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S03 is DB-level governance enforcement — no Temporal worker is required. The three scenarios (blocking denial, resolve-allows-advance, non-blocking transparency) are fully verifiable via HTTP API + direct `apply_state_transition` invocation against real Postgres. The runbook covers the live-server path.

## Preconditions

- Docker-compose Postgres service is running (`docker compose up -d postgres`)
- Alembic migrations applied to head (`alembic upgrade head`)
- `SPS_REVIEWER_API_KEY` is set in environment (dev value from `.env`)
- For integration test run: `SPS_RUN_TEMPORAL_INTEGRATION=1` set in environment
- For runbook: FastAPI server is not pre-started (runbook manages it); docker-compose Postgres must be healthy

## Smoke Test

Run the integration tests:

```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m003_s03_contradiction_blocking_test.py -v -s
```

Expected: `3 passed`. If any test fails, the slice is not shippable.

## Test Cases

### 1. Blocking contradiction denies REVIEW_PENDING→APPROVED_FOR_SUBMISSION

**Purpose:** Proves INV-003 enforcement — a blocking open contradiction prevents advancement even when a valid ReviewDecision exists.

1. Ensure Postgres is clean (or use test isolation — `_reset_db()` handles this in the test).
2. Seed a PermitCase in `REVIEW_PENDING` state.
3. Seed a valid `ReviewDecision` for that case with `decision_outcome=ACCEPT` (so the review gate would pass if the contradiction guard didn't fire).
4. `POST /api/v1/contradictions/` with `blocking_effect=true`, a valid `contradiction_id`, and the seeded `case_id`.
5. **Expected:** HTTP 201. Response body includes `"resolution_status": "OPEN"`.
6. Call `apply_state_transition` with `from_state=REVIEW_PENDING`, `to_state=APPROVED_FOR_SUBMISSION`, and the seeded `required_review_id`.
7. **Expected:** Returns `DeniedStateTransitionResult` with:
   - `event_type == "CONTRADICTION_ADVANCE_DENIED"`
   - `guard_assertion_id == "INV-SPS-CONTRA-001"`
   - `normalized_business_invariants == ["INV-003"]`
8. Query `case_transition_ledger` for the case:
   ```sql
   SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY occurred_at;
   ```
9. **Expected:** One row with `event_type='CONTRADICTION_ADVANCE_DENIED'` and `payload` containing `guard_assertion_id='INV-SPS-CONTRA-001'` and `normalized_business_invariants=['INV-003']`.

### 2. Resolving a blocking contradiction allows advancement

**Purpose:** Proves that the governance lifecycle is complete — resolve unblocks what the blocking contradiction locked.

1. Start from same setup as Test 1 (case in REVIEW_PENDING, valid ReviewDecision, blocking contradiction in OPEN state, first advancement denied).
2. `POST /api/v1/contradictions/{contradiction_id}/resolve` with `resolved_by=reviewer-test`.
3. **Expected:** HTTP 200. Response body includes `"resolution_status": "RESOLVED"`, non-null `resolved_at`, `resolved_by == "reviewer-test"`.
4. Call `apply_state_transition` again with a **fresh `request_id`** (idempotency key must differ from the denied attempt) and the same `required_review_id`.
5. **Expected:** Returns `AppliedStateTransitionResult` with `event_type == "CASE_STATE_CHANGED"`.
6. Query the DB:
   ```sql
   SELECT contradiction_id, resolution_status, resolved_at, resolved_by FROM contradiction_artifacts WHERE case_id = '<id>';
   SELECT case_state FROM permit_cases WHERE case_id = '<id>';
   ```
7. **Expected:** `resolution_status='RESOLVED'`, `resolved_at` non-null, `case_state='APPROVED_FOR_SUBMISSION'`.

### 3. Non-blocking contradiction is transparent to the guard

**Purpose:** Proves that `blocking_effect=false` contradictions do not interfere with the state transition guard — only blocking ones cause denial.

1. Seed a PermitCase in `REVIEW_PENDING` state. Do **not** seed a ReviewDecision.
2. `POST /api/v1/contradictions/` with `blocking_effect=false`.
3. **Expected:** HTTP 201. Response body includes `"blocking_effect": false`.
4. Call `apply_state_transition` with no `required_review_id` (or an invalid one).
5. **Expected:** Returns `DeniedStateTransitionResult` with:
   - `event_type == "APPROVAL_GATE_DENIED"` (not `CONTRADICTION_ADVANCE_DENIED`)
   - `guard_assertion_id != "INV-SPS-CONTRA-001"`
6. **This proves** the non-blocking contradiction was invisible to the contradiction guard and the review gate fired normally.

### 4. Full runbook: HTTP API lifecycle + Postgres state verification

**Purpose:** Operator-level verification against a live FastAPI server + docker-compose Postgres.

1. Ensure docker-compose Postgres is running.
2. `bash scripts/verify_m003_s03.sh`
3. **Expected output sequence (key lines):**
   - `runbook: create_contradiction_201_ok`
   - `runbook: contradiction_artifacts_row_ok`
   - `runbook: resolve_contradiction_200_ok`
   - `runbook: contradiction_resolved_ok`
   - `runbook: advancement_unblocked_ok event_type=CASE_STATE_CHANGED`
   - `runbook: ledger_row_ok`
   - `runbook: get_contradiction_200_ok`
   - `runbook: auth_checks_ok`
   - `runbook: duplicate_contradiction_409_ok`
   - `runbook: ok`
4. **Expected exit code:** 0.

## Edge Cases

### Duplicate contradiction_id returns 409

1. `POST /api/v1/contradictions/` with a `contradiction_id` that already exists in Postgres.
2. **Expected:** HTTP 409. Body includes `"error": "CONTRADICTION_ALREADY_EXISTS"` and `"contradiction_id": "<id>"`.

### Resolve already-resolved contradiction returns 409

1. Resolve a contradiction successfully (HTTP 200).
2. Attempt to resolve the same contradiction again.
3. **Expected:** HTTP 409. Body includes `"error": "ALREADY_RESOLVED"`, `"contradiction_id": "<id>"`, `"resolution_status": "RESOLVED"`.

### GET unknown contradiction returns 404

1. `GET /api/v1/contradictions/DOES-NOT-EXIST`.
2. **Expected:** HTTP 404. Body includes `"error": "not_found"`.

### Auth enforcement: missing key returns 401

1. Call any contradiction endpoint without `X-Reviewer-Api-Key` header.
2. **Expected:** HTTP 401. All three endpoints enforce this.

### Auth enforcement: wrong key returns 401

1. Call any contradiction endpoint with an incorrect `X-Reviewer-Api-Key` value.
2. **Expected:** HTTP 401.

### Blocking contradiction + missing review — contradiction denial takes precedence

1. Seed a PermitCase in REVIEW_PENDING. Do not seed a ReviewDecision.
2. POST a blocking contradiction.
3. Call `apply_state_transition` with no `required_review_id`.
4. **Expected:** `event_type == "CONTRADICTION_ADVANCE_DENIED"` (not `APPROVAL_GATE_DENIED`).
5. **This proves** guard ordering — contradiction check fires before review gate check.

## Failure Signals

- `event_type == "APPROVAL_GATE_DENIED"` when you expected `CONTRADICTION_ADVANCE_DENIED` → contradiction guard is not firing; check that `blocking_effect=True` and `resolution_status='OPEN'` are set on the artifact row.
- `event_type == "CONTRADICTION_ADVANCE_DENIED"` after resolve → resolve did not commit; check `resolved_at` in DB.
- HTTP 404 on POST `/` or POST `/{id}/resolve` → router not registered; check `main.py` includes `contradictions_router`.
- HTTP 422 on POST → Pydantic validation failure; check request body shape against `CreateContradictionRequest` or `ResolveContradictionRequest`.
- `resolved_at=None` after 200 resolve response → `_utcnow()` returned None or resolved_at was not committed.
- `artifact is None` after session.get(ContradictionArtifact, ...) → check session is using the same engine/DB as the API; confirm TRUNCATE ran against the same Postgres instance.

## Requirements Proved By This UAT

- R008 — Blocking contradiction denies `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` with stable denial identifiers (`INV-SPS-CONTRA-001`, `INV-003`); resolving via HTTP API allows advancement to proceed.

## Not Proven By This UAT

- Temporal workflow-level integration — `apply_state_transition` is tested directly, not via a running Temporal worker. Temporal integration was proven in M002/S01 and M003/S01; S03 adds the contradiction guard layer.
- Contradiction detector — contradictions are created manually via the HTTP API. Automated detection is deferred.
- Pagination or bulk listing of contradictions — no `GET /api/v1/contradictions?case_id=...` endpoint exists yet.
- Release gating based on unresolved contradictions — enforced at the state transition level only, not at release bundle creation.

## Notes for Tester

- The `_reset_db()` truncation in the integration tests includes `contradiction_artifacts` — each test starts from a clean slate. If running tests in parallel (not recommended), data from one test could bleed into another.
- The runbook generates a unique case/contradiction ID per run using a timestamp+PID suffix, so it's safe to re-run without cleanup.
- Boolean psql output in the runbook uses `"t"` (psql `-A -t` raw mode) — if you're querying psql manually for verification, `blocking_effect = true` will display as `t`.
- `GET /api/v1/contradictions/{id}` is the primary inspection surface for cross-system correlation — it returns the full artifact including `resolved_at`, `resolved_by`, and `resolution_status` without requiring DB access.
