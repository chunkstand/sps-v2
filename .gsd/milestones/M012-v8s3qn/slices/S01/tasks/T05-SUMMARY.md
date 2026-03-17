---
id: T05
parent: S01
milestone: M012-v8s3qn
provides:
  - EMERGENCY_HOLD signal contracts, activities, and workflow handlers with artifact validation
key_files:
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/activities.py
  - tests/m012_s01_emergency_hold_workflow_test.py
key_decisions:
  - Added workflow-side case_id recovery from workflow_id to allow pre-run signals.
patterns_established:
  - Emergency hold signals validate artifacts via activities and apply guarded transitions with deterministic request ids.
observability_surfaces:
  - workflow.emergency_hold_entered / workflow.emergency_hold_exited logs
  - case_transition_ledger CASE_STATE_CHANGED rows for EMERGENCY_HOLD entry/exit
  - activity.start/activity.ok logs for validate_emergency_artifact + validate_reviewer_confirmation
  - docker compose exec postgres psql -c "SELECT * FROM case_transition_ledger WHERE to_state='EMERGENCY_HOLD' OR from_state='EMERGENCY_HOLD'"
duration: 2h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T05: EMERGENCY_HOLD state transitions in workflow

**Added EMERGENCY_HOLD entry/exit signal contracts, workflow handlers, and validation activities with guarded transitions and lifecycle tests.**

## What Happened
- Added EmergencyHoldRequest/EmergencyHoldExitRequest contracts and wired EmergencyHoldEntry/EmergencyHoldExit signals into PermitCaseWorkflow.
- Added validate_emergency_artifact and validate_reviewer_confirmation activities to enforce emergency/confirmation existence and emergency expiry checks.
- Expanded apply_state_transition to allow EMERGENCY_HOLD entry/exit transitions.
- Added integration tests for emergency hold lifecycle, including success/expired/missing confirmation paths.
- Adjusted workflow signal handling to recover case_id from workflow_id when signals arrive early and added RetryPolicy(maximum_attempts=1) for validation activities.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_emergency_hold_workflow_test.py -v`
  - Failed: log assertions for workflow.emergency_hold_entered/exited not captured (2 tests failing).
  - Passed: expired emergency entry and missing confirmation exit raise failures.
- Slice-level verification not run (override guard tests/runbook pending).

## Diagnostics
- Workflow logs: workflow.emergency_hold_entered / workflow.emergency_hold_exited (not captured by tests yet)
- DB ledger inspection: `SELECT * FROM case_transition_ledger WHERE to_state='EMERGENCY_HOLD' OR from_state='EMERGENCY_HOLD'`
- Activity errors: validate_emergency_artifact (expired/missing), validate_reviewer_confirmation (missing)

## Deviations
- None.

## Known Issues
- Tests cannot capture workflow.emergency_hold_entered/exited logs; two tests failing due to missing log assertions. Need to determine correct logger/handler for Temporal workflow logs or alternative verification.

## Files Created/Modified
- `src/sps/workflows/permit_case/contracts.py` — added EmergencyHoldRequest/EmergencyHoldExitRequest contracts.
- `src/sps/workflows/permit_case/workflow.py` — added emergency hold signal handlers, activity calls, and retry policy.
- `src/sps/workflows/permit_case/activities.py` — added emergency/reviewer validation activities and EMERGENCY_HOLD transitions.
- `tests/m012_s01_emergency_hold_workflow_test.py` — added integration tests for emergency hold lifecycle.
