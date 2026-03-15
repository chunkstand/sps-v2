---
estimated_steps: 9
estimated_files: 6
---

# T02: Wire PermitCaseWorkflow denial→signal unblock→apply path + Temporal/Postgres integration proof

**Slice:** S02 — Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock
**Milestone:** M002-dq2dn9

## Description

Extend the minimal S01 workflow into the canonical guarded-transition proof path:

- Bootstrap a contract-valid case (starts in `REVIEW_PENDING`).
- Attempt the protected transition `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` via the guarded transition activity.
- On denial (`APPROVAL_GATE_DENIED`), enter a deterministic waiting state.
- Accept a `ReviewDecision` via Temporal signal, persist it idempotently, then re-attempt the same transition and complete on success.

This task also aligns the signal/CLI vocabulary with the canonical contracts (`ReviewDecision.decision_outcome` enum), so the end-to-end proof isn’t built on “garbage enums”.

## Steps

1. Update `ensure_permit_case_exists()` seeding to use contract-valid enums:
   - `case_state=REVIEW_PENDING`
   - `submission_mode=AUTOMATED|MANUAL` (pick one stable default)
   - `portal_support_level` to a valid enum value
2. Update workflow signal payload model (and CLI args) to use canonical `decision_outcome` values (`ACCEPT|ACCEPT_WITH_DISSENT|BLOCK`) and add any required fields needed for DB persistence.
3. Add an activity `persist_review_decision(...)` that writes `review_decisions` using the table’s `idempotency_key` unique constraint (derive a deterministic idempotency key in the workflow).
4. In `PermitCaseWorkflow.run()`:
   - derive a stable deterministic transition `request_id` (based on `workflow_id`/`run_id` + transition name)
   - call `apply_state_transition` (T01)
   - if denied with `APPROVAL_GATE_DENIED`, wait on `workflow.wait_condition(...)` for a review signal
   - on signal, call `persist_review_decision`, then re-call `apply_state_transition` with `required_review_id` set
   - complete only when transition is applied
5. Add a Temporal+Postgres integration test that:
   - starts the workflow and asserts it remains running after the initial denial
   - asserts Postgres contains a denial ledger row for the request
   - signals an ACCEPT decision, waits for completion
   - asserts `permit_cases.case_state=APPROVED_FOR_SUBMISSION`
   - asserts ledger has exactly one denial + one applied row for the run/correlation id.

## Must-Haves

- [ ] Workflow denies protected transition without a persisted valid `ReviewDecision`, then waits deterministically.
- [ ] Signal causes ReviewDecision persistence, then unblocks and applies the guarded transition.
- [ ] Operator CLI can start the workflow and send the canonical ReviewDecision signal values.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`

## Observability Impact

- Signals added/changed: workflow logs for `workflow.transition_attempt`, `workflow.transition_denied`, `workflow.waiting_for_review`, `workflow.review_received`, `workflow.transition_applied`.
- How a future agent inspects this: Temporal UI history (signal + activities) and Postgres `case_transition_ledger` rows keyed by `request_id`.
- Failure state exposed: deterministic denied result returned to workflow and persisted as ledger/audit event.

## Inputs

- `src/sps/workflows/permit_case/workflow.py` — existing deterministic wait→signal→resume pattern.
- `src/sps/workflows/cli.py` — operator start + signal surfaces.
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — established Temporal integration harness pattern.

## Expected Output

- `src/sps/workflows/permit_case/contracts.py` — updated signal contract (canonical enums) and any new persisted-decision payload model.
- `src/sps/workflows/permit_case/activities.py` — updated bootstrap seeding + new `persist_review_decision` activity.
- `src/sps/workflows/permit_case/workflow.py` — denial→wait→signal→persist→re-attempt path.
- `src/sps/workflows/cli.py` — signal command accepts canonical decision outcomes.
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — end-to-end Temporal+Postgres proof.
