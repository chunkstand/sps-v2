---
id: T01
parent: S01
milestone: M011-kg7s2p
provides:
  - Post-submission artifact models, migrations, and case list endpoints for correction/resubmission/approval/inspection.
key_files:
  - src/sps/db/models.py
  - alembic/versions/b1c2d3e4f5a6_post_submission_artifacts.py
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m011_s01_post_submission_artifacts_api_test.py
key_decisions:
  - none
patterns_established:
  - Case list endpoints return 409 when artifacts are absent and order by created_at desc.
observability_surfaces:
  - Case read endpoints for correction/resubmission/approval/inspection artifacts; new Postgres tables for durable audit.
duration: 1.5h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add post-submission artifact models + read APIs

**Added correction/resubmission/approval/inspection artifact schemas and case list endpoints with integration coverage.**

## What Happened
- Added ORM models and Alembic migration for correction_tasks, resubmission_packages, approval_records, and inspection_milestones with FK links to cases and submission attempts.
- Defined Pydantic response/list contracts and added case routes for listing each artifact type with consistent ordering and error handling.
- Created integration test that seeds each artifact type and validates list endpoints.

## Verification
- `python3 -m pytest tests/m011_s01_post_submission_artifacts_api_test.py -v` (failed: pytest module not installed)
- `python3 -m pytest tests/m011_s01_status_event_artifacts_test.py -v` (failed: pytest module not installed)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 python3 -m pytest tests/m011_s01_resubmission_workflow_test.py -v -s` (failed: pytest module not installed)

## Diagnostics
- Query new tables: `correction_tasks`, `resubmission_packages`, `approval_records`, `inspection_milestones`.
- API surfaces: `/api/v1/cases/{case_id}/correction-tasks`, `/resubmission-packages`, `/approval-records`, `/inspection-milestones`.

## Deviations
- None.

## Known Issues
- pytest is not installed in the environment, so verification could not run.

## Files Created/Modified
- `src/sps/db/models.py` — added post-submission artifact ORM models.
- `alembic/versions/b1c2d3e4f5a6_post_submission_artifacts.py` — migration for new artifact tables.
- `src/sps/api/contracts/cases.py` — added response/list contracts for new artifacts.
- `src/sps/api/routes/cases.py` — added list endpoints and response mappers.
- `tests/m011_s01_post_submission_artifacts_api_test.py` — integration coverage for artifact list APIs.
