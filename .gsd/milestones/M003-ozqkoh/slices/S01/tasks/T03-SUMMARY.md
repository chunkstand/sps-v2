---
id: T03
parent: S01
milestone: M003-ozqkoh
provides:
  - tests/m003_s01_reviewer_api_boundary_test.py — integration test with happy path + 409 conflict
  - scripts/verify_m003_s01.sh — runbook proving HTTP reviewer API → workflow unblock against real docker-compose
key_files:
  - tests/m003_s01_reviewer_api_boundary_test.py
  - scripts/verify_m003_s01.sh
key_decisions:
  - httpx.ASGITransport used for in-process ASGI testing (httpx 0.20+ removed the app= kwarg from AsyncClient); pattern is httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
  - Worker in integration test registers only [ensure_permit_case_exists, apply_state_transition] — persist_review_decision intentionally excluded to prove the API-authority-boundary contract (any registration of that activity would let the old path work silently)
  - Runbook starts uvicorn as a subprocess (python -m uvicorn sps.api.main:app) rather than docker-compose api service, keeping runbook self-contained without requiring a separately built image
  - Structured log lines (reviewer_api.*) land in uvicorn stderr under the sps.api.routes.reviews logger; grep on docker compose logs api | grep reviewer_api in containerized deployments
patterns_established:
  - httpx.ASGITransport(app=app) + AsyncClient(transport=...) for in-process FastAPI ASGI tests (replaces deprecated app= kwarg)
  - Runbook proves the HTTP authority boundary end-to-end: worker + API server + Temporal running concurrently, driven by curl, assertions via docker compose exec postgres psql
observability_surfaces:
  - "SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s — full integration run with log output"
  - "bash scripts/verify_m003_s01.sh — operator-style runbook, exits 0 on success"
  - "docker compose logs api | grep reviewer_api — surfaces decision lifecycle events (decision_received → decision_persisted → signal_sent or signal_failed)"
  - "Runbook logs to .gsd/runbook/m003_s01_worker_*.log and .gsd/runbook/m003_s01_api_*.log for post-mortem inspection"
duration: ~30min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Integration test and runbook

**Both integration tests pass and the runbook exits 0 against the live docker-compose stack.**

## What Happened

Wrote `tests/m003_s01_reviewer_api_boundary_test.py` following the m002_s02 pattern (real Temporal worker + real Postgres, guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`):

- `test_reviewer_api_unblocks_workflow`: starts `PermitCaseWorkflow`, waits for `APPROVAL_GATE_DENIED` (workflow paused in REVIEW_PENDING), then calls `POST /api/v1/reviews/decisions` via `httpx.ASGITransport`, asserts HTTP 201, asserts `review_decisions` row in Postgres, waits for workflow result, asserts `final_result.result == "applied"` and `CASE_STATE_CHANGED/APPROVED_FOR_SUBMISSION` in ledger.
- `test_reviewer_api_idempotency_conflict_409`: first POST succeeds (201), second POST with same `idempotency_key` but different `decision_id` returns 409 with `error=IDEMPOTENCY_CONFLICT`, `existing_decision_id`, and `idempotency_key` in the body.

Wrote `scripts/verify_m003_s01.sh` following the m002_s03 runbook pattern:
- Brings up docker-compose stack, applies migrations, starts worker + uvicorn API in background
- Waits for workflow to enter REVIEW_PENDING (polls `case_transition_ledger` for `APPROVAL_GATE_DENIED`)
- POSTs to `POST /api/v1/reviews/decisions` via `curl` with `X-Reviewer-Api-Key` header, asserts HTTP 201
- Asserts `review_decisions` row via `docker compose exec postgres psql`
- Polls for `CASE_STATE_CHANGED/APPROVED_FOR_SUBMISSION` in ledger
- Proves 409 with second POST on same `idempotency_key`
- Verifies 401 on missing key and wrong key

One implementation fix needed: `httpx.AsyncClient(app=app, ...)` was removed in httpx 0.20+. Fixed by switching to `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)`.

## Verification

```
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s
# Result: 2 passed

bash scripts/verify_m003_s01.sh
# Result: exits 0; all Postgres assertions pass; 401, 409, and 201 paths verified
```

Slice-level verification checks:
- ✅ `tests/m003_s01_reviewer_api_boundary_test.py` — integration test passes (guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`)
- ✅ `bash scripts/verify_m003_s01.sh` — runbook exits 0 against running docker-compose stack
- ✅ Auth failure path: 401 on missing key, 401 on wrong key — confirmed by runbook phases 11
- ✅ Signal delivery: runbook shows `reviewer_api_201_ok` → workflow completes `APPROVED_FOR_SUBMISSION`
- ✅ Structured log inspection: `docker compose logs api | grep reviewer_api` documented in runbook hint

## Diagnostics

- Integration test: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s` shows full log output
- Runbook: logs to `.gsd/runbook/m003_s01_worker_*.log` and `.gsd/runbook/m003_s01_api_*.log`
- If workflow stays paused: worker log shows `workflow.waiting_for_review` without `workflow.review_received` → signal not delivered; check `reviewer_api.signal_failed` in API logs
- Signal delivery failure: `review_decisions` row is durable; re-signal with `temporal workflow signal --workflow-id permit-case/<case_id> --name ReviewDecision --input '{"decision_id":"<id>","decision_outcome":"ACCEPT","reviewer_id":"<id>"}'`

## Deviations

- `httpx.AsyncClient(app=app, ...)` not supported in httpx 0.28 — replaced with `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)`. The task plan referenced this pattern but it's been deprecated since httpx 0.20; the fix was straightforward.

## Known Issues

None.

## Files Created/Modified

- `tests/m003_s01_reviewer_api_boundary_test.py` — new integration test (happy path + 409 conflict)
- `scripts/verify_m003_s01.sh` — new runbook script proving HTTP reviewer API → workflow unblock
