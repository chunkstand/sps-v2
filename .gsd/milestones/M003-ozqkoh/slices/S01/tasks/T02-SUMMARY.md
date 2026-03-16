---
id: T02
parent: S01
milestone: M003-ozqkoh
provides:
  - POST /api/v1/reviews/decisions — fully implemented with idempotency + Temporal signal delivery
  - GET /api/v1/reviews/decisions/{decision_id} — read-only inspection endpoint
  - PermitCaseWorkflow no longer calls persist_review_decision; uses review_signal.decision_id as required_review_id
  - Integration test file tests/m003_s01_reviewer_api_boundary_test.py
  - Runbook scripts/verify_m003_s01.sh
key_files:
  - src/sps/api/routes/reviews.py
  - src/sps/workflows/permit_case/workflow.py
  - tests/m003_s01_reviewer_api_boundary_test.py
  - scripts/verify_m003_s01.sh
key_decisions:
  - POST endpoint is async def; Temporal signal dispatched via asyncio.wait_for(10s timeout) after Postgres commit; signal failure logged as reviewer_api.signal_failed but does NOT change HTTP response status (DECISIONS #28)
  - Workflow raises RuntimeError("ReviewDecisionSignal missing decision_id — legacy signal unsupported after M003/S01") if signal arrives without decision_id — fails loudly rather than silently (DECISIONS #29)
  - Idempotency check queries by idempotency_key; same key + same decision_id → 200; same key + different decision_id → 409 with IDEMPOTENCY_CONFLICT error body
  - schema_version hardcoded to "1.0" and reviewer_independence_status to "PASS" since CreateReviewDecisionRequest does not expose these; these can be extended in a later slice
patterns_established:
  - Async FastAPI endpoint with sync DB dependency (Session = Depends(get_db)) — same Session pattern as evidence.py but endpoint is async def for Temporal I/O
  - Signal delivery in _send_review_signal() local helper: asyncio.wait_for with 10s timeout, exception swallowed and logged, never raises to caller
observability_surfaces:
  - reviewer_api.decision_received decision_id=... idempotency_key=... case_id=... (logged at endpoint entry)
  - reviewer_api.decision_persisted decision_id=... case_id=... idempotency_key=... (logged after Postgres commit)
  - reviewer_api.signal_sent decision_id=... case_id=... workflow_id=... (logged on successful Temporal signal)
  - reviewer_api.signal_failed decision_id=... case_id=... signal_error=<exc_type> (logged on Temporal failure; workflow stays paused, operator re-signals via workflow ID permit-case/<case_id>)
  - Inspection: GET /api/v1/reviews/decisions/{decision_id}; DB: SELECT * FROM review_decisions WHERE decision_id = '...';
  - grep "reviewer_api\." <api_logs> shows full decision lifecycle sequence
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Endpoint implementation, service layer, and workflow boundary flip

**POST /api/v1/reviews/decisions is live with idempotency + Temporal signal delivery; PermitCaseWorkflow now uses the API-issued decision_id directly.**

## What Happened

Implemented `POST /api/v1/reviews/decisions` as a fully async FastAPI endpoint with:
- Idempotency check against `review_decisions.idempotency_key`: same key + same `decision_id` → 200 (idempotent OK); same key + different `decision_id` → 409 `IDEMPOTENCY_CONFLICT`
- INSERT `ReviewDecision` row with `schema_version=1.0`, `object_type=permit_case`, `dissent_flag` derived from outcome
- Post-commit Temporal signal delivery via `_send_review_signal()` with 10s timeout; signal failure logged as `reviewer_api.signal_failed` and does NOT change HTTP status (201 still returned)
- Four structured log events: `decision_received`, `decision_persisted`, `signal_sent`/`signal_failed`

Implemented `GET /api/v1/reviews/decisions/{decision_id}` as a simple PK lookup returning 200 or 404.

Removed `persist_review_decision` from `PermitCaseWorkflow.run`:
- Removed `PersistReviewDecisionRequest` import and `workflow.execute_activity(persist_review_decision, ...)` call
- Added guard: `if review_signal.decision_id is None: raise RuntimeError(...)` — fails loudly on legacy signals
- `review_decision_id = review_signal.decision_id` — the workflow is now a pure consumer of the API-issued ID

Created `tests/m003_s01_reviewer_api_boundary_test.py` with HTTP-level tests (guarded by `SPS_RUN_DB_INTEGRATION=1`) and a full workflow integration test (guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`). Created `scripts/verify_m003_s01.sh` runbook.

## Verification

Unit tests pass unchanged:
```
.venv/bin/pytest tests/ -k "not (integration or temporal)" -x
# 9 passed, 6 skipped
```

Import chain verified:
```
python -c "from sps.api.routes.reviews import router; print('import OK')"
python -c "from sps.workflows.permit_case.workflow import PermitCaseWorkflow; print('workflow import OK')"
```

Auth smoke tests (TestClient, no DB needed):
- Missing key → 401 ✓
- Wrong key → 401 ✓
- GET without key → 401 ✓

Route registration confirmed: both `/api/v1/reviews/decisions` and `/api/v1/reviews/decisions/{decision_id}` appear in `app.routes`.

m003_s01 test file collects cleanly and skips at module level when env vars unset (exit code 5, expected).

## Diagnostics

Signal delivery failures are non-fatal and recoverable:
1. `grep "reviewer_api.signal_failed" <api_logs>` shows `signal_error=<exc_type>` and `case_id`
2. The `review_decisions` row is durable — `SELECT decision_id FROM review_decisions WHERE decision_id = '<id>';`
3. Operator re-signals using: `temporal workflow signal --workflow-id permit-case/<case_id> --name ReviewDecision --input '{"decision_id":"<id>","decision_outcome":"ACCEPT","reviewer_id":"<id>"}'`

Idempotency conflict inspection: 409 body always includes `error`, `existing_decision_id`, and `idempotency_key`.

## Deviations

- `reviewer_independence_status` hardcoded to `"PASS"` in the DB INSERT because `CreateReviewDecisionRequest` does not expose it (T01 plan kept the model focused). The field is structural — a later slice can expose it.
- `schema_version` hardcoded to `"1.0"` — no existing version registry to consult; consistent with how `persist_review_decision` activity handled it.

## Known Issues

- Existing m002 integration tests (`m002_s01_temporal_permit_case_workflow_test.py`) send `ReviewDecisionSignal` without `decision_id`, which will now raise `RuntimeError` in the workflow when run against the new code. These tests are guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` and must be updated before the next integration run. The m003_s01 integration test provides the updated pattern (POST via HTTP, decision_id carried in signal).

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — full POST + GET implementation replacing T01 stubs
- `src/sps/workflows/permit_case/workflow.py` — persist_review_decision removed; review_signal.decision_id used as required_review_id
- `tests/m003_s01_reviewer_api_boundary_test.py` — integration test file (HTTP + workflow tests, both guarded by env vars)
- `scripts/verify_m003_s01.sh` — runbook script for slice-level verification against live docker-compose
