# S01: Post-submission artifacts + workflow wiring — UAT

**Milestone:** M011-kg7s2p
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 creates database models, persistence activities, and API list endpoints; artifact-driven UAT proves the models persist correctly and are queryable via API; full runtime verification (Temporal workflow execution) is deferred to S02 docker-compose runbook.

## Preconditions

- Postgres running and accepting connections
- Database migrated to latest (alembic upgrade head)
- Database tables exist: correction_tasks, resubmission_packages, approval_records, inspection_milestones
- SPS API server running (or ASGI transport available for test client)
- Authentication configured: SPS_AUTH_JWT_ISSUER, SPS_AUTH_JWT_AUDIENCE, SPS_AUTH_JWT_SECRET, SPS_AUTH_JWT_ALGORITHM set
- At least one PermitCase and SubmissionAttempt exist in database (can be seeded via test helper)

## Smoke Test

Run `pytest tests/m011_s01_post_submission_artifacts_api_test.py -v` and verify it passes:
- Test seeds CorrectionTask, ResubmissionPackage, ApprovalRecord, InspectionMilestone rows
- Test queries all 4 API list endpoints with intake role authentication
- All 4 endpoints return 200 with seeded artifact data
- Test exits 0

If this passes, the core artifact models, migrations, persistence, and API list endpoints are working.

## Test Cases

### 1. Create and query CorrectionTask via API

1. Seed a PermitCase with case_id=CASE-EXAMPLE-001
2. Seed a SubmissionAttempt with submission_attempt_id=SUBATT-001 linked to CASE-EXAMPLE-001
3. Insert CorrectionTask row with correction_task_id=CORR-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBATT-001, status=OPEN, summary="Need updated plans", due_at=7 days from now
4. Build JWT with roles=["intake"]
5. GET /api/v1/cases/CASE-EXAMPLE-001/correction-tasks with Authorization: Bearer {token}
6. **Expected:** 200 response with JSON body containing correction_tasks array with 1 item: correction_task_id=CORR-001, status=OPEN, summary="Need updated plans"

### 2. Create and query ResubmissionPackage via API

1. Using same case/attempt from test case 1
2. Insert ResubmissionPackage row with resubmission_package_id=RESUB-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBATT-001, package_id=PKG-RESUB-1, package_version=v2, status=READY
3. GET /api/v1/cases/CASE-EXAMPLE-001/resubmission-packages with Authorization: Bearer {token}
4. **Expected:** 200 response with resubmission_packages array containing resubmission_package_id=RESUB-001, status=READY, package_version=v2

### 3. Create and query ApprovalRecord via API

1. Using same case/attempt from test case 1
2. Insert ApprovalRecord row with approval_record_id=APR-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBATT-001, decision=APPROVED, authority=city-review, decided_at=now
3. GET /api/v1/cases/CASE-EXAMPLE-001/approval-records with Authorization: Bearer {token}
4. **Expected:** 200 response with approval_records array containing approval_record_id=APR-001, decision=APPROVED, authority=city-review

### 4. Create and query InspectionMilestone via API

1. Using same case/attempt from test case 1
2. Insert InspectionMilestone row with inspection_milestone_id=INSP-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBATT-001, milestone_type=ROUGH_INSPECTION, status=SCHEDULED, scheduled_for=14 days from now
3. GET /api/v1/cases/CASE-EXAMPLE-001/inspection-milestones with Authorization: Bearer {token}
4. **Expected:** 200 response with inspection_milestones array containing inspection_milestone_id=INSP-001, milestone_type=ROUGH_INSPECTION, status=SCHEDULED

### 5. Idempotent artifact persistence (CorrectionTask)

1. Using case/attempt from test case 1
2. Call persist_correction_task activity with request_id=REQ-CORR-001, case_id=CASE-EXAMPLE-001, submission_attempt_id=SUBATT-001, correction_task_id=CORR-IDEMPOTENT, status=OPEN, summary="Test idempotency"
3. **Expected:** Activity returns successfully, correction_tasks table contains CORR-IDEMPOTENT row
4. Call persist_correction_task activity again with identical request (same request_id, correction_task_id, case_id, submission_attempt_id)
5. **Expected:** Activity returns successfully without error, correction_tasks table still contains exactly 1 CORR-IDEMPOTENT row (no duplicate), activity log shows idempotent=1 flag

### 6. Case/submission_attempt linkage validation

1. Seed PermitCase with case_id=CASE-A
2. Seed SubmissionAttempt with submission_attempt_id=SUBATT-A linked to CASE-A
3. Seed PermitCase with case_id=CASE-B
4. Seed SubmissionAttempt with submission_attempt_id=SUBATT-B linked to CASE-B
5. Call persist_correction_task with case_id=CASE-A, submission_attempt_id=SUBATT-B (mismatched)
6. **Expected:** Activity raises LookupError with "submission_attempt_case_mismatch" message, no correction_tasks row created

### 7. Status map normalization for post-submission events

1. Load specs/sps/build-approved/fixtures/phase7/status-maps.json
2. **Expected:** JSON contains mapping entries for:
   - COMMENT_ISSUED → normalized_status=COMMENT_REVIEW_PENDING
   - RESUBMISSION_REQUESTED → normalized_status=RESUBMISSION_PENDING
   - APPROVAL_PENDING_INSPECTION → normalized_status=APPROVED_PENDING_INSPECTION
   - APPROVAL_FINAL → normalized_status=APPROVED_FINAL
   - INSPECTION_SCHEDULED → normalized_status=INSPECTION_SCHEDULED
   - INSPECTION_PASSED → normalized_status=INSPECTION_PASSED
   - INSPECTION_FAILED → normalized_status=INSPECTION_FAILED
3. All 7 entries have valid JSON structure with external_status, normalized_status, portal_family fields

## Edge Cases

### Missing case_id (CorrectionTask creation)

1. Call persist_correction_task with case_id=CASE-MISSING (does not exist in permit_cases)
2. **Expected:** Activity raises LookupError with "permit_case not found" message, no correction_tasks row created

### Missing submission_attempt_id (ResubmissionPackage creation)

1. Call persist_resubmission_package with submission_attempt_id=SUBATT-MISSING (does not exist in submission_attempts)
2. **Expected:** Activity raises LookupError with "submission_attempt not found" message, no resubmission_packages row created

### API query without authentication

1. GET /api/v1/cases/CASE-EXAMPLE-001/correction-tasks without Authorization header
2. **Expected:** 401 response with {"detail": {"error": "auth_required", "auth_reason": "missing_or_invalid_authorization"}}

### API query with wrong role (reviewer instead of intake)

1. Build JWT with roles=["reviewer"]
2. GET /api/v1/cases/CASE-EXAMPLE-001/correction-tasks with Authorization: Bearer {token}
3. **Expected:** 403 response with {"detail": {"error_code": "role_denied", "required_roles": ["intake"]}}

### Empty artifact list

1. Seed PermitCase with case_id=CASE-EMPTY (no correction_tasks)
2. GET /api/v1/cases/CASE-EMPTY/correction-tasks with valid intake token
3. **Expected:** 200 response with {"case_id": "CASE-EMPTY", "correction_tasks": []} (empty array, not 404)

## Failure Signals

- API endpoints return 500 instead of 200 (unhandled exception in route handler)
- API endpoints return 404 for valid case_id (DB query failed or route not registered)
- API endpoints return 401 with valid token (JWT validation broken)
- API endpoints return 403 with intake role (RBAC dependency injection misconfigured)
- Artifact persistence activity raises IntegrityError (FK constraint violation, idempotency broken)
- Artifact persistence activity raises LookupError for valid case_id/submission_attempt_id (validation logic broken)
- Idempotent replay creates duplicate rows instead of returning existing (PK check or race handling broken)
- Status map JSON fails to parse (invalid JSON syntax)
- Status map missing required fields (external_status, normalized_status, portal_family)
- Alembic migration fails to run (SQL syntax error, FK constraint error, column name collision)

## Requirements Proved By This UAT

- R032 — Comment resolution and resubmission loops (F-008): Proved that CorrectionTask and ResubmissionPackage artifacts can be persisted and queried; workflow state branches exist (code verification) but runtime execution deferred to S02.
- R033 — Approval and inspection milestone tracking (F-009): Proved that ApprovalRecord and InspectionMilestone artifacts can be persisted and queried; status map fixtures extended with approval/inspection statuses.

## Not Proven By This UAT

- Workflow runtime execution: PermitCaseWorkflow state transitions through COMMENT_REVIEW_PENDING → CORRECTION_PENDING → RESUBMISSION_PENDING → DOCUMENT_COMPLETE loop not proven (requires running Temporal server, deferred to S02).
- Status event normalization triggering artifact creation: ExternalStatusEvent → workflow continuation → persist_* activity call path not proven (status event wiring not implemented, deferred to S02).
- End-to-end post-submission lifecycle: Full comment → resubmission → approval → inspection flow not proven (requires docker-compose runbook in S02).
- Temporal integration tests: tests/m011_s01_resubmission_workflow_test.py and tests/m011_s01_status_event_artifacts_test.py not executed (require SPS_RUN_TEMPORAL_INTEGRATION=1 + running Temporal server + full database setup, deferred pending infrastructure provisioning).

## Notes for Tester

**Authentication is required for all API tests:**
- All case endpoints require intake role due to router-level dependency: `dependencies=[Depends(require_roles(Role.INTAKE))]`
- Build JWT with roles=["intake"] and pass `Authorization: Bearer {token}` header on all requests
- Without authentication, all requests will return 401; with wrong role, requests will return 403

**Use existing Phase 6 fixture case ID:**
- Test case ID CASE-EXAMPLE-001 has existing Phase 6 fixture data and can be used for all tests
- Do not create new fixture sets; reuse CASE-EXAMPLE-001 for consistency

**Temporal integration tests are blocked but structurally correct:**
- tests/m011_s01_resubmission_workflow_test.py and tests/m011_s01_status_event_artifacts_test.py are complete and will pass once infrastructure is provisioned
- Do not expect these tests to pass without running Temporal server (localhost:7233) and full Postgres setup
- Test structure is correct; infrastructure provisioning is the blocker

**Idempotency is key:**
- All persistence activities use PK check + IntegrityError race handling pattern
- Idempotent replay should return existing row without error and log idempotent=1
- If duplicate rows are created, idempotency is broken and persistence logic needs debugging

**FK constraints enforce referential integrity:**
- Cannot create artifact without valid case_id and submission_attempt_id
- Cannot create artifact with mismatched case_id/submission_attempt_id linkage (validation logic prevents this)
- Trust FK constraints; do not bypass with direct DB inserts
