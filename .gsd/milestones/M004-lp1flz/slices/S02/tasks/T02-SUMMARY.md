---
id: T02
parent: S02
milestone: M004-lp1flz
provides:
  - Jurisdiction/requirements persistence activities, guarded transitions, and workflow wiring to reach RESEARCH_COMPLETE
key_files:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/worker.py
  - tests/m004_s02_jurisdiction_requirements_workflow_test.py
key_decisions:
  - none
patterns_established:
  - Idempotent fixture persistence activities with structured persisted logs and deterministic request IDs
observability_surfaces:
  - jurisdiction_activity.persisted and requirements_activity.persisted logs, workflow.transition_* logs, case_transition_ledger rows
  - jurisdiction_resolutions and requirement_sets tables for persisted artifacts
  - guard denial rows with denial_reason and guard_assertion_id
duration: 1h 10m
verification_result: failed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Wire activities + workflow transitions for jurisdiction/research

**Added fixture persistence activities and workflow wiring to drive INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE with guarded transitions.**

## What Happened
- Added jurisdiction/requirements persistence activities that load phase4 fixtures, insert rows idempotently, and emit structured persisted logs with case_id/request_id.
- Extended apply_state_transition to allow INTAKE_COMPLETE → JURISDICTION_COMPLETE and JURISDICTION_COMPLETE → RESEARCH_COMPLETE with jurisdiction presence and requirement freshness guards.
- Updated PermitCaseWorkflow to run fixture persistence activities and guarded transitions with deterministic request IDs, returning results for the new path.
- Registered new activities in the Temporal worker and added workflow progression integration coverage with log assertions.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py -k workflow_progression` (skipped; SPS_RUN_TEMPORAL_INTEGRATION not set).
- `bash scripts/verify_m004_s02.sh` (failed: script not found).

## Diagnostics
- Inspect `case_transition_ledger` for CASE_STATE_CHANGED rows to JURISDICTION_COMPLETE/RESEARCH_COMPLETE or guard denials.
- Check `jurisdiction_resolutions` and `requirement_sets` tables for persisted artifacts.
- Review logs containing `jurisdiction_activity.persisted`, `requirements_activity.persisted`, and `workflow.transition_*` for activity/transition traces.

## Deviations
- None.

## Known Issues
- `scripts/verify_m004_s02.sh` is missing; slice verification script could not be run.
- Temporal workflow progression test requires SPS_RUN_TEMPORAL_INTEGRATION=1 to execute.

## Files Created/Modified
- `src/sps/workflows/permit_case/activities.py` — added fixture persistence activities and new guarded transition checks.
- `src/sps/workflows/permit_case/contracts.py` — added persistence request models for new activities.
- `src/sps/workflows/permit_case/workflow.py` — wired jurisdiction/requirements activities and transitions for INTAKE_COMPLETE path.
- `src/sps/workflows/worker.py` — registered new activities in the Temporal worker.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — added workflow progression integration test and log assertions.
