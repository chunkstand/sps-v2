---
id: S01
parent: M003-ozqkoh
milestone: M003-ozqkoh
provides:
  - POST /api/v1/reviews/decisions — authoritative ReviewDecision writer with idempotency + Temporal signal delivery
  - GET /api/v1/reviews/decisions/{decision_id} — read-only inspection endpoint
  - require_reviewer_api_key FastAPI dependency (401 on missing/wrong X-Reviewer-Api-Key header)
  - SPS_REVIEWER_API_KEY config field (default dev-reviewer-key; never logged)
  - PermitCaseWorkflow no longer calls persist_review_decision; consumes decision_id from ReviewDecisionSignal
  - ReviewDecisionSignal.decision_id optional field (backward-compatible None default)
  - tests/m003_s01_reviewer_api_boundary_test.py — integration test (happy path + 409 conflict)
  - scripts/verify_m003_s01.sh — operator runbook proving HTTP reviewer API → workflow unblock against docker-compose
requires: []
affects:
  - S02
  - S03
  - S04
key_files:
  - src/sps/config.py
  - src/sps/api/routes/reviews.py
  - src/sps/api/main.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/workflow.py
  - tests/m003_s01_reviewer_api_boundary_test.py
  - scripts/verify_m003_s01.sh
key_decisions:
  - POST endpoint async def; Temporal signal dispatched via asyncio.wait_for(10s) after Postgres commit; signal failure logged but does NOT change HTTP response status (DECISIONS #28)
  - ReviewDecisionSignal.decision_id is optional (None default) for backward compat; workflow raises RuntimeError if None — fails loudly on legacy signals (DECISIONS #29)
  - httpx.ASGITransport(app=app) + AsyncClient(transport=...) for in-process ASGI tests (DECISIONS #30)
  - Idempotency: same key + same decision_id → 200; same key + different decision_id → 409 IDEMPOTENCY_CONFLICT
  - reviewer_independence_status hardcoded to PASS; schema_version hardcoded to 1.0 (S02 extends these)
patterns_established:
  - Async FastAPI endpoint + sync DB Session dependency (same Session pattern as evidence.py) — endpoint async for Temporal I/O
  - Signal delivery in _send_review_signal() local helper: asyncio.wait_for, exception swallowed and logged, never raises to caller
  - httpx.ASGITransport(app=app) + AsyncClient(transport=...) for in-process FastAPI ASGI tests
  - Worker in integration test registers only [ensure_permit_case_exists, apply_state_transition] — persist_review_decision intentionally excluded to enforce API-authority-boundary contract
observability_surfaces:
  - reviewer_api.decision_received / decision_persisted / signal_sent / signal_failed — logged by POST endpoint
  - GET /api/v1/reviews/decisions/{decision_id} — read-only inspection
  - docker compose logs api | grep reviewer_api — full decision lifecycle event sequence
  - SELECT * FROM review_decisions WHERE decision_id = '...'; — Postgres assertion
  - SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s — integration test with log output
  - bash scripts/verify_m003_s01.sh — operator-style runbook, exits 0 on success
drill_down_paths:
  - .gsd/milestones/M003-ozqkoh/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M003-ozqkoh/slices/S01/tasks/T03-SUMMARY.md
duration: ~1h40m (T01: 25m, T02: 45m, T03: 30m)
verification_result: passed
completed_at: 2026-03-15
---

# S01: Reviewer API authority boundary

**HTTP reviewer API is the sole writer of ReviewDecision records; PermitCaseWorkflow now waits for the signal carrying decision_id issued by the API, not from its own activity.**

## What Happened

Three tasks executed sequentially, each building on the prior.

**T01 (infrastructure):** Added `SPS_REVIEWER_API_KEY` to `sps.config.Settings` with a safe local default and explicit redaction warning. Created `src/sps/api/routes/reviews.py` with Pydantic request/response models (`CreateReviewDecisionRequest`, `ReviewDecisionResponse`), the `require_reviewer_api_key` dependency (401 on missing/wrong `X-Reviewer-Api-Key` header), and stub endpoints (501). Registered the router under `/api/v1/reviews` in `sps.api.main`. Extended `ReviewDecisionSignal` with `decision_id: str | None = None` — backward-compatible addition that lets existing callers (omitting `decision_id`) deserialize without breaking.

**T02 (implementation):** Replaced the 501 stubs with a full `POST /api/v1/reviews/decisions` implementation: idempotency check against `review_decisions.idempotency_key` (same key + same `decision_id` → 200; same key + different `decision_id` → 409 `IDEMPOTENCY_CONFLICT`); INSERT `ReviewDecision` row in a transaction; post-commit Temporal signal delivery via `_send_review_signal()` with 10s timeout (signal failure is logged but does NOT roll back the Postgres commit or change HTTP status). Added `GET /api/v1/reviews/decisions/{decision_id}` for read-only inspection. Stripped `persist_review_decision` from `PermitCaseWorkflow.run` — workflow now uses `review_signal.decision_id` directly as `required_review_id`, and raises `RuntimeError` loudly if the signal arrives without it. Four structured log events instrument the full decision lifecycle.

**T03 (verification):** Wrote `tests/m003_s01_reviewer_api_boundary_test.py` with two integration tests (guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`): the happy path (HTTP POST → Postgres row → Temporal signal → workflow resumes → `APPROVED_FOR_SUBMISSION` in ledger) and the 409 conflict case. Wrote `scripts/verify_m003_s01.sh` following the m002_s03 runbook pattern — brings up docker-compose, applies migrations, starts worker + uvicorn in background, drives the full scenario with `curl`, and asserts Postgres outcomes and HTTP status codes including the 401 and 409 paths.

One implementation fix in T03: `httpx.AsyncClient(app=app, ...)` was removed in httpx 0.20; replaced with `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)`.

## Verification

All verification checks passed:

- `python -c "from sps.api.main import app; print('ok')"` → ok
- `python -c "from sps.api.routes.reviews import router, ..."` → ok
- `get_settings().reviewer_api_key` → `dev-reviewer-key`
- `ReviewDecisionSignal(decision_outcome='ACCEPT', reviewer_id='r1').decision_id is None` → ok
- `pytest tests/ -k "not (integration or temporal)" -x -q` → 9 passed, 6 skipped
- Auth smoke: missing key → 401 `{error: missing_api_key}`; wrong key → 401 `{error: invalid_api_key}`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s` → 2 passed
- `bash scripts/verify_m003_s01.sh` → exits 0; all Postgres assertions passed; 201/401/409 paths confirmed

## Requirements Advanced

- R006 — ReviewDecision authority boundary flipped from workflow activity to HTTP reviewer API; idempotency enforcement and Temporal signal delivery implemented and proven

## Requirements Validated

- R006 — Proved by integration test (`tests/m003_s01_reviewer_api_boundary_test.py`) + operator runbook (`scripts/verify_m003_s01.sh`): HTTP POST → Postgres `review_decisions` row → Temporal signal → workflow resumes → `APPROVED_FOR_SUBMISSION` in `case_transition_ledger`; 409 on idempotency-key conflict; 401 on missing/wrong key

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- `httpx.AsyncClient(app=app, ...)` is not supported in httpx 0.28 (removed in 0.20); replaced with `httpx.ASGITransport(app=app)` + `AsyncClient(transport=...)`. This was noted in the T03 plan as the expected pattern; the fix was straightforward.
- `reviewer_independence_status` hardcoded to `"PASS"` in DB INSERT because `CreateReviewDecisionRequest` does not expose it — structural placeholder; S02 extends this.
- `schema_version` hardcoded to `"1.0"` — no existing version registry; consistent with how `persist_review_decision` handled it previously.

## Known Limitations

- Existing m002 integration tests (`m002_s01_temporal_permit_case_workflow_test.py`) send `ReviewDecisionSignal` without `decision_id` — these will hit the `RuntimeError` guard in the workflow when run against the new code. They are guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1` and must be updated to use the new HTTP API pattern before the next m002 integration run.
- `reviewer_independence_status` is always `PASS` — independence enforcement lands in S02.
- No retry / dead-letter for failed signal delivery — operator re-signals manually using `temporal workflow signal --workflow-id permit-case/<case_id>`.

## Follow-ups

- Update `m002_s01_temporal_permit_case_workflow_test.py` to use the HTTP reviewer API pattern (avoids `RuntimeError` on `ReviewDecisionSignal.decision_id is None`).
- S02: expose `reviewer_independence_status` and `subject_author_id` in `CreateReviewDecisionRequest`; implement self-approval denial.
- Operational hardening: signal-with-start as alternative delivery mode for cases where the workflow may not be running yet.

## Files Created/Modified

- `src/sps/config.py` — added `reviewer_api_key` field with `SPS_REVIEWER_API_KEY` alias and redaction warning
- `src/sps/api/routes/reviews.py` (new) — Pydantic models, auth dependency, full POST + GET implementation
- `src/sps/api/main.py` — registered reviews_router under `/api/v1/reviews`
- `src/sps/workflows/permit_case/contracts.py` — added `decision_id: str | None = None` to `ReviewDecisionSignal`
- `src/sps/workflows/permit_case/workflow.py` — removed `persist_review_decision`; uses `review_signal.decision_id` as `required_review_id`
- `tests/m003_s01_reviewer_api_boundary_test.py` (new) — integration test (happy path + 409 conflict)
- `scripts/verify_m003_s01.sh` (new) — operator runbook

## Forward Intelligence

### What the next slice should know

- The `CreateReviewDecisionRequest` currently has no `subject_author_id` field — S02 needs to add it and wire the independence check before the Postgres INSERT.
- `reviewer_independence_status` is a column in `review_decisions`; its value is currently hardcoded to `PASS`; S02 should update it based on the actual independence check result before committing.
- Workflow ID convention is `permit-case/<case_id>` — the signal is sent to this ID. S02 doesn't change this convention.
- The `_send_review_signal()` helper is the sole signal dispatch point — S02 independence denial should happen *before* calling it (or before the Postgres commit) so a denied review never reaches Temporal.
- Auth middleware is on the router level (`dependencies=[Depends(require_reviewer_api_key)]`) — S02 adds policy logic inside the endpoint, not the auth layer.

### What's fragile

- m002 integration tests — will hit `RuntimeError` if run against current workflow code without the HTTP reviewer API being used. Update before running `SPS_RUN_TEMPORAL_INTEGRATION=1` on m002 test files.
- Signal delivery has no retry loop — if Temporal is briefly unreachable after a Postgres commit, the review is durable but the workflow stays paused. The operator re-signals manually via the convention in diagnostics.

### Authoritative diagnostics

- `docker compose logs api | grep reviewer_api` — surfaces the four decision lifecycle events in order; `signal_failed` indicates the workflow stayed paused and needs operator re-signal
- `SELECT decision_id, idempotency_key, reviewer_independence_status FROM review_decisions ORDER BY created_at DESC LIMIT 5;` — authoritative Postgres assertion; the row persists even on signal failure
- `SELECT event_type, to_state FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY created_at;` — confirms `APPROVED_FOR_SUBMISSION` transition applied

### What assumptions changed

- Assumed httpx `app=` kwarg was still supported — it was removed in httpx 0.20. `ASGITransport` is the stable replacement and works without modification to the endpoint code.
