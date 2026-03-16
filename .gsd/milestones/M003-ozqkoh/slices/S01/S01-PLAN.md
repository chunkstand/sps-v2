# S01: Reviewer API authority boundary

**Goal:** Replace workflow-internal `persist_review_decision` activity with a governed HTTP endpoint that writes the `ReviewDecision` row, then signals Temporal — making `POST /api/v1/reviews/decisions` the sole writer of `review_decisions`.

**Demo:** A PermitCaseWorkflow in `REVIEW_PENDING` is unblocked by `POST /api/v1/reviews/decisions` (authenticated with dev API key) against a live docker-compose run. The workflow resumes and transitions to `APPROVED_FOR_SUBMISSION`. A second POST with the same `idempotency_key` but conflicting fields returns 409. Both outcomes are proven by an integration test and a runbook script.

## Must-Haves

- `POST /api/v1/reviews/decisions` writes a `ReviewDecision` row, then signals the waiting Temporal workflow via `workflow_id` convention
- Dev API key middleware (`SPS_REVIEWER_API_KEY` header) gates the endpoint; missing/wrong key returns 401
- Duplicate `idempotency_key` with a conflicting payload returns 409 with a stable error shape; duplicate with identical payload returns 200 (idempotent OK)
- Workflow no longer calls `persist_review_decision` activity; it waits for the signal, reads `decision_id` from signal payload, and proceeds with `apply_state_transition` using `required_review_id=decision_id`
- Signal payload extended to carry `decision_id` (client-provided, already written to Postgres before signal fires)
- Integration test proves: HTTP POST → Postgres `review_decisions` row → Temporal signal → workflow resumes → `APPROVED_FOR_SUBMISSION` in `case_transition_ledger`
- `scripts/verify_m003_s01.sh` runbook drives the full scenario end-to-end against real docker-compose

## Proof Level

- This slice proves: integration (HTTP authority boundary + Temporal signal delivery + workflow resume)
- Real runtime required: yes (docker-compose Postgres + Temporal)
- Human/UAT required: no

## Verification

- `tests/m003_s01_reviewer_api_boundary_test.py` — integration test against real docker-compose (guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`)
- `bash scripts/verify_m003_s01.sh` — runbook: brings up stack, runs HTTP POST, asserts DB outcomes
- **Failure path — missing/wrong API key:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/reviews/decisions` returns `401`; with wrong key header also returns `401` — confirms auth middleware is live
- **Failure path — signal delivery failure:** When Temporal is unreachable after a successful Postgres commit, `reviewer_api.signal_failed` is emitted with `signal_error=...`; the `review_decisions` row persists in Postgres (visible via `docker compose exec postgres psql -c "SELECT decision_id, idempotency_key FROM review_decisions ORDER BY created_at DESC LIMIT 1;"`); operator re-signals using `permit-case/<case_id>` workflow ID convention
- **Structured log inspection:** `docker compose logs api | grep reviewer_api` surfaces the decision lifecycle event sequence (`decision_received` → `decision_persisted` → `signal_sent` or `signal_failed`)

## Observability / Diagnostics

- Runtime signals: structured log lines in reviewer endpoint (`reviewer_api.decision_received`, `reviewer_api.decision_persisted`, `reviewer_api.signal_sent`, `reviewer_api.signal_failed`) and existing workflow log lines (`workflow.review_received`, `workflow.transition_applied`)
- Inspection surfaces: `GET /api/v1/reviews/decisions/{decision_id}` (read-only), `case_transition_ledger` table, Temporal UI workflow execution timeline
- Failure visibility: if signal delivery fails after Postgres commit, the structured log `reviewer_api.signal_failed signal_error=...` is the recovery trigger; `review_decisions` row is durable — operator can re-signal manually using workflow ID convention `permit-case/<case_id>`
- Redaction constraints: `SPS_REVIEWER_API_KEY` must never appear in logs; `decision_id` and `idempotency_key` are safe to log

## Integration Closure

- Upstream surfaces consumed: `sps.db.models.ReviewDecision`, `sps.db.session`, `sps.workflows.temporal.connect_client()`, `sps.workflows.permit_case.ids.permit_case_workflow_id`, existing `ReviewDecisionSignal` contract (extended)
- New wiring introduced: `sps.api.routes.reviews` router registered in `sps.api.main`; `SPS_REVIEWER_API_KEY` in `sps.config.Settings`; `ReviewDecisionSignal.decision_id` field (backward-compatible addition)
- What remains before milestone is truly usable end-to-end: S02 (independence guard), S03 (contradiction blocking), S04 (dissent artifacts) — all build on the working API from this slice

## Tasks

- [x] **T01: API infrastructure — settings, models, key middleware, router skeleton** `est:45m`
  - Why: Establishes all structural prerequisites (config, Pydantic request/response shapes, auth dependency, router registration) so T02 has a clean surface to implement behavior on
  - Files: `src/sps/config.py`, `src/sps/api/routes/reviews.py` (new), `src/sps/api/main.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: Add `SPS_REVIEWER_API_KEY` to Settings with a safe local default; add `reviewer_api_key` property; create `src/sps/api/routes/reviews.py` with Pydantic request model (`CreateReviewDecisionRequest`), response model (`ReviewDecisionResponse`), and a 501 stub endpoint; implement `require_reviewer_api_key` FastAPI dependency that reads the `X-Reviewer-Api-Key` header and returns 401 on mismatch; extend `ReviewDecisionSignal` in contracts.py with `decision_id: str` field (optional with default None for backward compatibility with existing tests); register reviews router in `sps.api.main`
  - Verify: `python -c "from sps.api.routes.reviews import router; print('ok')"` succeeds; `python -c "from sps.config import get_settings; s = get_settings(); print(s.reviewer_api_key)"` prints the default key
  - Done when: All imports resolve, router is registered in main, `SPS_REVIEWER_API_KEY` is in Settings, request/response models are importable with correct field shapes

- [x] **T02: Endpoint implementation, service layer, and workflow boundary flip** `est:1.5h`
  - Why: Core of the slice — implements the write path, 409 idempotency enforcement, Temporal signal delivery, and removes `persist_review_decision` from the workflow
  - Files: `src/sps/api/routes/reviews.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: Implement `POST /api/v1/reviews/decisions` — validate request, open a DB transaction, check idempotency: if `idempotency_key` exists with identical `decision_id` return 200; if exists with conflicting `decision_id` return 409 with `{"error":"IDEMPOTENCY_CONFLICT","existing_decision_id":"...","idempotency_key":"..."}`; otherwise INSERT `ReviewDecision` row and commit; after commit, connect Temporal client and signal the workflow at `permit-case/<case_id>` with `ReviewDecisionSignal` carrying `decision_id`; log `reviewer_api.signal_sent` or `reviewer_api.signal_failed` (signal failure must NOT roll back the Postgres commit — row is durable, caller must re-signal); patch `PermitCaseWorkflow.run` to remove `persist_review_decision` activity call — the review signal now carries `decision_id` so the workflow uses that directly as `required_review_id` in the second `apply_state_transition` call; add `GET /api/v1/reviews/decisions/{decision_id}` read-only endpoint for inspection
  - Verify: Unit-level: `pytest tests/ -k "not integration" -x` passes; import check `python -c "from sps.api.main import app; print('ok')"` succeeds; workflow module imports without error
  - Done when: Endpoint handles all three idempotency cases correctly, workflow no longer calls `persist_review_decision`, signal carrying `decision_id` is the sole mechanism to deliver the review to the workflow

- [x] **T03: Integration test and runbook** `est:1.5h`
  - Why: Closes R006 — proves the full HTTP → Postgres → Temporal signal → workflow resume path against a real docker-compose stack; the runbook makes the scenario reproducible by operators
  - Files: `tests/m003_s01_reviewer_api_boundary_test.py` (new), `scripts/verify_m003_s01.sh` (new)
  - Do: Write `tests/m003_s01_reviewer_api_boundary_test.py` following the m002_s02 test pattern (guarded by `SPS_RUN_TEMPORAL_INTEGRATION=1`): start the workflow, call `POST /api/v1/reviews/decisions` via `httpx.AsyncClient` (with correct API key), assert `review_decisions` row in Postgres, wait for workflow to complete, assert `APPROVED_FOR_SUBMISSION` ledger event in `case_transition_ledger`; add a second test asserting 409 on idempotency-key conflict with differing decision_id; write `scripts/verify_m003_s01.sh` following the m002_s03 runbook pattern: bring up docker-compose, apply migrations, start worker, POST to reviewer API with `curl`, assert Postgres outcomes via `docker compose exec postgres psql`
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v` passes against running docker-compose stack; `bash scripts/verify_m003_s01.sh` exits 0
  - Done when: Both integration test assertions pass (happy path + 409), runbook exits 0, `review_decisions` and `case_transition_ledger` rows confirmed by Postgres assertions

## Files Likely Touched

- `src/sps/config.py`
- `src/sps/api/main.py`
- `src/sps/api/routes/reviews.py` (new)
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/workflow.py`
- `tests/m003_s01_reviewer_api_boundary_test.py` (new)
- `scripts/verify_m003_s01.sh` (new)
