# S01: Post-submission artifacts + workflow wiring

**Goal:** Persist correction/resubmission/approval/inspection artifacts from status ingestion and wire the resubmission loop through the PermitCaseWorkflow with guarded transitions.
**Demo:** Integration tests show COMMENT_ISSUED → CORRECTION_PENDING → RESUBMISSION_PENDING → SUBMITTED loop with durable artifacts, and approval/inspection events persisted + queryable via API read surfaces.

## Must-Haves
- Persist CorrectionTask and ResubmissionPackage artifacts tied to case + submission attempt when comment/resubmission statuses arrive (R032).
- Persist ApprovalRecord and InspectionMilestone artifacts from normalized status events and expose them via case read APIs (R033).
- PermitCaseWorkflow advances through comment/resubmission states and back to SUBMITTED using guarded transitions (R032).
- Status mapping fixtures cover comment/resubmission/approval/inspection statuses with fail-closed normalization.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m011_s01_post_submission_artifacts_api_test.py -v`
- `pytest tests/m011_s01_status_event_artifacts_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s`

## Observability / Diagnostics
- Runtime signals: activity logs for artifact persistence, transition ledger entries
- Inspection surfaces: Postgres tables (correction_tasks, resubmission_packages, approval_records, inspection_milestones), case read endpoints
- Failure visibility: activity error logs with request_id + case_id, transition ledger denial rows
- Redaction constraints: none

## Integration Closure
- Upstream surfaces consumed: `persist_external_status_event`, status map fixtures, `apply_state_transition`, `SubmissionAttempt` linkage
- New wiring introduced in this slice: artifact persistence activities, workflow comment/resubmission/approval branches, API read endpoints
- What remains before the milestone is truly usable end-to-end: S02 docker-compose runbook

## Tasks
- [x] **T01: Add post-submission artifact models + read APIs** `est:2h`
  - Why: expose durable correction/resubmission/approval/inspection records for R032/R033.
  - Files: `src/sps/db/models.py`, `alembic/versions/*.py`, `src/sps/api/contracts/cases.py`, `src/sps/api/routes/cases.py`
  - Do: add ORM models + FK constraints + migration; add response/list models and case endpoints to query new artifacts; align IDs with existing stable-id conventions.
  - Verify: `pytest tests/m011_s01_post_submission_artifacts_api_test.py -v`
  - Done when: new artifact tables migrate cleanly and API list endpoints return persisted rows for a case.
- [x] **T02: Persist artifacts from status events + extend status maps** `est:2h`
  - Why: ensure normalized comment/resubmission/approval/inspection statuses create durable artifacts with idempotency.
  - Files: `specs/sps/build-approved/fixtures/phase7/status-maps.json`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/contracts.py`, `tests/m011_s01_status_event_artifacts_test.py`
  - Do: extend status map fixtures for comment/resubmission/approval/inspection; add activity helpers to persist CorrectionTask/ResubmissionPackage/ApprovalRecord/InspectionMilestone with idempotent guards and case/submission validation; add tests covering artifact creation and duplicate protection.
  - Verify: `pytest tests/m011_s01_status_event_artifacts_test.py -v`
  - Done when: status normalization writes the new artifacts and idempotent replays return existing rows without error.
- [x] **T03: Wire resubmission loop + approval/inspection workflow branches** `est:2h`
  - Why: prove the workflow transitions through post-submission states and records approvals/inspections.
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`, `tests/m011_s01_resubmission_workflow_test.py`
  - Do: wire COMMENT_ISSUED/RESUBMISSION_REQUESTED/APPROVAL_* /INSPECTION_* handlers to `apply_state_transition`; ensure latest submission attempt tracking is respected; add Temporal integration tests for comment→resubmission→submitted loop and approval/inspection persistence.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s`
  - Done when: workflow tests show the loop and approval/inspection artifacts in Postgres.

## Files Likely Touched
- `src/sps/db/models.py`
- `alembic/versions/*.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `specs/sps/build-approved/fixtures/phase7/status-maps.json`
- `tests/m011_s01_post_submission_artifacts_api_test.py`
- `tests/m011_s01_status_event_artifacts_test.py`
- `tests/m011_s01_resubmission_workflow_test.py`
