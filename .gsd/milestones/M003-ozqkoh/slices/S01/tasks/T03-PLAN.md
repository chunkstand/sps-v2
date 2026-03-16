---
estimated_steps: 6
estimated_files: 2
---

# T03: Integration test and runbook

**Slice:** S01 — Reviewer API authority boundary
**Milestone:** M003-ozqkoh

## Description

Proves R006 against a real docker-compose stack: HTTP `POST /api/v1/reviews/decisions` → Postgres `review_decisions` row → Temporal signal → workflow resumes → `APPROVED_FOR_SUBMISSION` in `case_transition_ledger`. Also proves the 409 idempotency-conflict path.

The integration test follows the established m002_s02 pattern (real Temporal worker + real Postgres, guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`). The runbook follows the m002_s03 pattern (curl + psql assertions inside the container).

## Steps

1. Write `tests/m003_s01_reviewer_api_boundary_test.py`:
   - Module-level guard: `pytest.skip` unless `SPS_RUN_TEMPORAL_INTEGRATION=1`
   - Session-scoped fixtures: wait for Postgres, run Alembic migrations, reset DB (`TRUNCATE case_transition_ledger, review_decisions, permit_cases CASCADE`)
   - `test_reviewer_api_unblocks_workflow`: start `PermitCaseWorkflow` via Temporal client (worker in thread pool), call `POST /api/v1/reviews/decisions` via `httpx.AsyncClient` with correct `X-Reviewer-Api-Key`, assert HTTP 201, assert `review_decisions` row in Postgres, wait for workflow result, assert `final_result.result == "applied"`, assert `case_transition_ledger` has `CASE_STATE_CHANGED` with `to_state=APPROVED_FOR_SUBMISSION`
   - `test_reviewer_api_idempotency_conflict_409`: POST once, then POST again with same `idempotency_key` but different `decision_id`; assert 409 with `error=IDEMPOTENCY_CONFLICT`
   - Use `httpx.AsyncClient(app=app, base_url="http://test")` for in-process testing (no need to spin up a separate HTTP server)

2. Wire the FastAPI test client properly: the `POST /decisions` endpoint is async and makes a real Temporal signal call. In the integration test, use the real Temporal client (same as the workflow test) — the in-process `httpx` client will execute the real signal delivery.

3. Write `scripts/verify_m003_s01.sh` following the m002_s03 runbook pattern:
   - Check docker-compose services up
   - Apply Alembic migrations
   - Start worker in background (log to temp file)
   - Generate `CASE_ID` with ULID or `uuidgen`
   - Start workflow via CLI (`python -m sps.workflows.cli start ...`) or direct Temporal API
   - POST to reviewer API with `curl -X POST http://localhost:8000/api/v1/reviews/decisions -H "X-Reviewer-Api-Key: ..." -H "Content-Type: application/json" -d '{...}'`; assert HTTP 201
   - Assert `review_decisions` row via `docker compose exec postgres psql ...`
   - Wait for workflow completion (poll `case_transition_ledger` via psql)
   - Assert `CASE_STATE_CHANGED` row with `to_state=APPROVED_FOR_SUBMISSION`
   - POST again with same idempotency_key + different decision_id; assert HTTP 409

4. Ensure test correctly exercises the FastAPI API endpoint via `httpx` — not the Temporal activities directly. The point is to prove the HTTP authority boundary, not the activity in isolation.

5. Start the FastAPI app in a background thread during the integration test (or use `httpx.AsyncClient(app=app, ...)`). The app must be able to reach the running Temporal instance and Postgres — use the same env vars as the rest of the integration test suite.

6. Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v` passes; `bash scripts/verify_m003_s01.sh` exits 0.

## Must-Haves

- [ ] `test_reviewer_api_unblocks_workflow` passes: HTTP 201, `review_decisions` row in DB, workflow completes with `APPROVED_FOR_SUBMISSION`
- [ ] `test_reviewer_api_idempotency_conflict_409` passes: 409 with correct error shape on conflicting `idempotency_key`
- [ ] `scripts/verify_m003_s01.sh` exits 0 against a running docker-compose stack
- [ ] The runbook drives the HTTP API (not the CLI signal injection used in m002)
- [ ] Postgres assertions use `docker compose exec postgres psql` pattern (no host psql required)
- [ ] Test is guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` and skips cleanly otherwise

## Observability Impact

- Signals added: test output includes structured log assertions (`grep "reviewer_api.signal_sent"`, `grep "workflow.transition_applied"`)
- How a future agent inspects this: run `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s` to see full log output; or run `bash scripts/verify_m003_s01.sh` for operator-style validation
- Failure state exposed: if the workflow stays paused, the worker log shows `workflow.waiting_for_review` without a following `workflow.review_received` — indicates signal was not delivered; check `reviewer_api.signal_failed` in API logs

## Inputs

- `src/sps/api/main.py` — the FastAPI `app` object (for `httpx` in-process test client)
- `src/sps/api/routes/reviews.py` — the implemented endpoint from T02
- `src/sps/workflows/permit_case/workflow.py` — patched workflow from T02
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — reference for test structure/fixtures
- `scripts/verify_m002_s03_runbook.sh` — reference for runbook structure

## Expected Output

- `tests/m003_s01_reviewer_api_boundary_test.py` (new) — integration test with happy path + 409 test cases
- `scripts/verify_m003_s01.sh` (new) — runbook proving HTTP reviewer API → workflow unblock against real docker-compose
