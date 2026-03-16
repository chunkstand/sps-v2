---
id: T02
parent: S01
milestone: M004-lp1flz
provides:
  - INTAKE_PENDING → INTAKE_COMPLETE guarded transition + workflow branch
key_files:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/contracts.py
key_decisions:
  - none
patterns_established:
  - workflow reads PermitCase state via activity before branching transitions
observability_surfaces:
  - case_transition_ledger rows + workflow.transition_attempt/transition_applied logs
  - activity.start logs for apply_state_transition/fetch_permit_case_state
  - denial_reason/event_type in ledger payloads
duration: 2h
verification_result: partial
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Wire INTAKE_PENDING → INTAKE_COMPLETE workflow transition

**Added an intake-branching workflow step with a guarded INTAKE_PENDING → INTAKE_COMPLETE transition and ledger persistence.**

## What Happened
- Added `fetch_permit_case_state` activity and PermitCase state snapshot contract to branch workflow execution.
- Extended `apply_state_transition` with the INTAKE_PENDING → INTAKE_COMPLETE guard that checks Project existence and records ledger entries.
- Updated `PermitCaseWorkflow` to run intake transition when case_state is INTAKE_PENDING and preserved the REVIEW_PENDING path otherwise; expanded workflow result with optional intake transition fields.
- Updated Temporal worker/test activity registrations and added a workflow_transition test that validates ledger + state update.

## Verification
- `.venv/bin/python -m pytest tests/m004_s01_intake_api_workflow_test.py -k workflow_transition`
- `.venv/bin/python -m pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation`
- `.venv/bin/python -m pytest tests/m004_s01_intake_api_workflow_test.py`
- `.venv/bin/python -m pytest tests/m002_s01_temporal_permit_case_workflow_test.py` (skipped: SPS_RUN_TEMPORAL_INTEGRATION not set; pytest exit code 5)
- `bash scripts/verify_m004_s01.sh` (failed: script missing)

## Diagnostics
- Inspect `case_transition_ledger` for `case_id` + `to_state=INTAKE_COMPLETE` and denial_reason/event_type on failures.
- Check workflow logs for `workflow.transition_attempt` and `workflow.transition_applied` with INTAKE_COMPLETE.
- Activity logs include `activity.start name=fetch_permit_case_state` and `activity.start name=apply_state_transition`.

## Deviations
- None.

## Known Issues
- `scripts/verify_m004_s01.sh` does not exist, so the slice runbook verification step cannot run.
- Temporal integration test skipped without `SPS_RUN_TEMPORAL_INTEGRATION=1`.

## Files Created/Modified
- `src/sps/workflows/permit_case/activities.py` — added state snapshot activity and intake transition guard.
- `src/sps/workflows/permit_case/workflow.py` — branched intake transition and added intake result metadata.
- `src/sps/workflows/permit_case/contracts.py` — added PermitCase state snapshot + optional intake fields in workflow result.
- `src/sps/workflows/worker.py` — registered new activity.
- `tests/m004_s01_intake_api_workflow_test.py` — added workflow_transition coverage + async contract validation test.
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — registered new activity.
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — registered new activity.
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py` — registered new activity.
- `tests/m002_s03_temporal_replay_determinism_test.py` — registered new activity.
- `tests/m003_s01_reviewer_api_boundary_test.py` — registered new activity.
- `.gsd/milestones/M004-lp1flz/slices/S01/S01-PLAN.md` — marked T02 complete.
- `.gsd/STATE.md` — advanced next action to T03.
