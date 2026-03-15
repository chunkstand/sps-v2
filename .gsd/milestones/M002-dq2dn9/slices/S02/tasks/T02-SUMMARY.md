---
id: T02
parent: S02
milestone: M002-dq2dn9
provides:
  - End-to-end PermitCaseWorkflow proof path: guarded denial → deterministic wait → review signal → durable ReviewDecision persistence → guarded apply (Temporal + Postgres)
key_files:
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/cli.py
  - tests/m002_s02_temporal_guarded_transition_workflow_test.py
key_decisions:
  - Deterministic correlation/request IDs derived from workflow_id+run_id (attempt-suffixed) to make ledger/review writes idempotent and inspectable
patterns_established:
  - Denial-driven workflow orchestration: attempt guarded transition → wait for signal → persist review decision via idempotent activity → re-attempt guarded transition
observability_surfaces:
  - workflow logs: workflow.transition_attempt|workflow.transition_denied|workflow.waiting_for_review|workflow.review_received|workflow.transition_applied
  - activity logs: activity.start|activity.ok|activity.denied|activity.error (with workflow_id/run_id/case_id/request_id)
duration: 2h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Wire PermitCaseWorkflow denial→signal unblock→apply path + Temporal/Postgres integration proof

**Shipped the canonical guarded-transition workflow path (deny → wait → signal → persist → apply) with a real Temporal+Postgres integration test proving durable denial and successful unblock.**

## What Happened

- Updated `ensure_permit_case_exists()` seeding to be contract-valid for the proof path (starts in `REVIEW_PENDING`, `submission_mode=AUTOMATED`, `portal_support_level=FULLY_SUPPORTED`).
- Aligned `ReviewDecision` signaling with canonical contract enums (`ACCEPT|ACCEPT_WITH_DISSENT|BLOCK`) and expanded the signal model with required persistence fields (with safe defaults).
- Added `persist_review_decision(...)` Temporal activity that writes `review_decisions` idempotently via the table’s `idempotency_key` unique constraint.
- Extended `PermitCaseWorkflow`:
  - attempt guarded transition via `apply_state_transition`
  - on `APPROVAL_GATE_DENIED` wait deterministically for the `ReviewDecision` signal
  - persist the review decision, then re-attempt transition with `required_review_id`
  - complete only when the transition applies
- Added `tests/m002_s02_temporal_guarded_transition_workflow_test.py` proving the full denial→unblock→apply path and validating Postgres state + ledger rows.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`
- Slice-level spot-check (ran while implementing):
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py tests/m002_s01_temporal_permit_case_workflow_test.py tests/m002_s02_temporal_guarded_transition_workflow_test.py`

## Diagnostics

- Deterministic IDs used by the workflow:
  - `correlation_id = "{workflow_id}:{run_id}"`
  - transition `request_id = "{workflow_id}/{run_id}/review_pending_to_approved_for_submission/attempt-{n}"`
  - review `decision_id`/`idempotency_key = "review/{workflow_id}/{run_id}"`
- Postgres inspection:
  - Ledger by request_id:
    - `SELECT event_type, payload FROM case_transition_ledger WHERE transition_id = '<request_id>';`
  - Ledger by correlation_id:
    - `SELECT transition_id, event_type FROM case_transition_ledger WHERE correlation_id = '<correlation_id>' ORDER BY occurred_at;`
  - Review decision by idempotency key:
    - `SELECT decision_id, decision_outcome FROM review_decisions WHERE idempotency_key = 'review/<workflow_id>/<run_id>';`

## Deviations

- None.

## Known Issues

- None observed in verification.

## Files Created/Modified

- `src/sps/workflows/permit_case/contracts.py` — canonical review decision enums + persistence/request/result models.
- `src/sps/workflows/permit_case/activities.py` — contract-valid seeding + new `persist_review_decision` activity.
- `src/sps/workflows/permit_case/workflow.py` — denial→wait→signal→persist→re-attempt guarded transition path with structured workflow logs.
- `src/sps/workflows/worker.py` — registers the new activity.
- `src/sps/workflows/cli.py` — CLI accepts canonical decision outcomes.
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — updated to reflect canonical outcomes + new workflow completion payload.
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — Temporal+Postgres integration proof for S02.
