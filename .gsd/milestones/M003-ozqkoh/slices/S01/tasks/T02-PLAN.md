---
estimated_steps: 7
estimated_files: 3
---

# T02: Endpoint implementation, service layer, and workflow boundary flip

**Slice:** S01 — Reviewer API authority boundary
**Milestone:** M003-ozqkoh

## Description

Implements the `POST /api/v1/reviews/decisions` endpoint with full idempotency semantics, Temporal signal delivery, and the `GET /api/v1/reviews/decisions/{decision_id}` read endpoint. Simultaneously removes `persist_review_decision` from `PermitCaseWorkflow` — after this task, the workflow is a pure consumer: it waits for a signal that carries `decision_id`, uses that ID as `required_review_id`, and re-attempts the guarded transition.

This is the authority boundary flip that D20 establishes as the core Phase 3 architectural decision.

## Steps

1. In `src/sps/api/routes/reviews.py`, implement `POST /decisions` fully:
   - Parse request body as `CreateReviewDecisionRequest`
   - Open a synchronous DB session (use `get_db` dependency)
   - Check idempotency: query `ReviewDecision` by `idempotency_key`
     - If found with same `decision_id`: return 200 `ReviewDecisionResponse` (idempotent OK)
     - If found with different `decision_id`: return 409 `{"error":"IDEMPOTENCY_CONFLICT","existing_decision_id":"<existing>","idempotency_key":"<key>"}`
     - If not found: INSERT the `ReviewDecision` row and commit
   - After commit, in a separate `asyncio` step: connect Temporal client and send signal `ReviewDecision` to workflow `permit-case/<case_id>` with `ReviewDecisionSignal(decision_id=decision_id, decision_outcome=outcome, reviewer_id=reviewer_id, ...)`
   - Log `reviewer_api.signal_sent` on success, `reviewer_api.signal_failed signal_error=...` on failure — signal failure must NOT raise 5xx back to the caller (the Postgres write succeeded; the row is durable)
   - Return 201 `ReviewDecisionResponse` on successful create

2. Implement `GET /decisions/{decision_id}` in `src/sps/api/routes/reviews.py`:
   - Load `ReviewDecision` from DB by primary key
   - Return 404 if not found, else 200 `ReviewDecisionResponse`

3. In `src/sps/workflows/permit_case/workflow.py`, remove the `persist_review_decision` activity call:
   - Remove the `PersistReviewDecisionRequest` construction and `workflow.execute_activity(persist_review_decision, ...)` block
   - Remove the `persist_review_decision` import (if no longer used anywhere in the workflow module)
   - After `await workflow.wait_condition(...)`, validate `review_signal` as before; use `review_signal.decision_id` directly as `review_decision_id` for `required_review_id` in the second `apply_state_transition` call
   - Add a guard: if `review_signal.decision_id is None`, raise `RuntimeError("ReviewDecisionSignal missing decision_id — legacy signal unsupported after M003/S01")` to fail loudly rather than silently passing a None review ID

4. Update `PermitCaseWorkflowResult` in contracts.py: `review_decision_id` is now always populated from `review_signal.decision_id` (not derived in workflow); verify this field's type is still `str | None` (it is — no change needed, just confirm the source).

5. Wire async Temporal client call: the endpoint is a FastAPI sync route using `get_db` — Temporal signal must be dispatched via `asyncio.run(...)` or by making the endpoint async. Make the `POST /decisions` endpoint `async def` and use `await connect_client()` + `await handle.signal(...)`. Use `asyncio.wait_for` with a 10-second timeout to avoid hanging on Temporal unavailability; log signal failure but return 201 regardless.

6. Add structured log lines at the start and end of the endpoint (matching the `activity.start`/`activity.ok` pattern): `reviewer_api.decision_received`, `reviewer_api.decision_persisted`, `reviewer_api.signal_sent`/`reviewer_api.signal_failed`.

7. Verify unit-level correctness: `pytest tests/ -k "not (integration or temporal)" -x` must still pass (existing m002 tests should not break since `ReviewDecisionSignal.decision_id` is optional).

## Must-Haves

- [ ] `POST /api/v1/reviews/decisions` with valid key writes `ReviewDecision` to Postgres and returns 201
- [ ] 409 returned when `idempotency_key` exists with a different `decision_id`; response body includes `error`, `existing_decision_id`, `idempotency_key`
- [ ] 200 (idempotent OK) returned when `idempotency_key` exists with the same `decision_id`
- [ ] Temporal signal sent after Postgres commit; signal failure logged but does not change HTTP response status
- [ ] `PermitCaseWorkflow.run` no longer calls `persist_review_decision` activity
- [ ] Workflow uses `review_signal.decision_id` as `required_review_id`; raises loudly if `decision_id is None`
- [ ] `GET /api/v1/reviews/decisions/{decision_id}` returns 200 or 404

## Observability Impact

- Signals added: `reviewer_api.decision_received`, `reviewer_api.decision_persisted`, `reviewer_api.signal_sent`, `reviewer_api.signal_failed signal_error=<exc_type>`
- How a future agent inspects this: `grep "reviewer_api\." <log>` finds the write/signal sequence; `review_decisions` table shows the durable record; if signal failed, the `permit-case/<case_id>` workflow remains paused in Temporal UI — operator re-signals manually
- Failure state exposed: signal timeout/failure logged with `signal_error=` tag; workflow stays paused (not failed) — recovery is a manual re-signal using the workflow ID from the log

## Inputs

- `src/sps/api/routes/reviews.py` — stubs from T01; add full implementation
- `src/sps/workflows/permit_case/workflow.py` — remove `persist_review_decision` call; use `review_signal.decision_id`
- `src/sps/workflows/permit_case/contracts.py` — `ReviewDecisionSignal.decision_id` field (added in T01)
- `src/sps/db/models.py` — `ReviewDecision` model (pre-existing)
- `src/sps/workflows/temporal.py` — `connect_client()` for signal delivery

## Expected Output

- `src/sps/api/routes/reviews.py` — fully implemented POST + GET endpoints with idempotency + signal delivery
- `src/sps/workflows/permit_case/workflow.py` — `persist_review_decision` removed; `review_signal.decision_id` used as `required_review_id`
