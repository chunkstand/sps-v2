# M011-kg7s2p: Phase 11 — comment resolution, resubmission, and approval tracking

**Vision:** After submission, SPS can record reviewer comments, generate correction tasks and resubmission packages, and persist approval/inspection milestones as status events arrive, all wired through the deterministic workflow and proven in live docker-compose execution.

## Success Criteria
- Comment and resubmission status events generate durable CorrectionTask and ResubmissionPackage artifacts linked to the correct case and submission attempt.
- Resubmission attempts are recorded and the workflow reaches RESUBMISSION_PENDING and back to SUBMITTED on a new attempt without losing prior history.
- Approval records and inspection milestones are persisted from normalized status events and are queryable via API read surfaces.
- A docker-compose runbook proves the end-to-end lifecycle: submit → comment → resubmit → approve/inspect with Postgres evidence.

## Key Risks / Unknowns
- Resubmission loop complexity could cause state explosion or inconsistent guard paths if the workflow stores too much loop history.
- Status mapping coverage for comment/resubmission/inspection may be incomplete and cause fail-closed ingestion until fixtures are expanded.

## Proof Strategy
- Resubmission loop complexity → retire in S01 by proving the workflow advances through COMMENT_REVIEW_PENDING → CORRECTION_PENDING → RESUBMISSION_PENDING → SUBMITTED using real activities + DB persistence in Temporal/Postgres integration tests.
- Status mapping coverage → retire in S01 by extending status map fixtures and proving normalized events create correction/approval artifacts with deterministic activity idempotency tests.

## Verification Classes
- Contract verification: pytest integration tests for new models, activities, and API read surfaces (Postgres-backed).
- Integration verification: Temporal workflow integration tests covering comment/resubmission loop and approval milestone persistence.
- Operational verification: docker-compose runbook that exercises API + worker + Postgres for comment/resubmission/approval tracking.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slices below are complete.
- CorrectionTask, ResubmissionPackage, ApprovalRecord, and InspectionMilestone artifacts are persisted via activities and exposed via API read surfaces.
- PermitCaseWorkflow consumes normalized status events and progresses through comment/resubmission/approval states using guarded transitions.
- The docker-compose runbook proves the real entrypoints (API + worker + Postgres + Temporal) can execute the full post-submission loop.
- Success criteria are re-checked against live runbook behavior, not just fixtures.

## Requirement Coverage
- Covers: R032, R033
- Partially covers: none
- Leaves for later: R034, R035
- Orphan risks: none

## Slices
- [x] **S01: Post-submission artifacts + workflow wiring** `risk:high` `depends:[]`
  > After this: Status ingestion and workflow runs (via tests) create correction/resubmission/approval/inspection artifacts with deterministic persistence and guarded transitions.
- [ ] **S02: Status event workflow wiring + live docker-compose runbook** `risk:medium` `depends:[S01]`
  > After this: Normalized status events trigger workflow continuations that call persist_correction_task/persist_resubmission_package/persist_approval_record/persist_inspection_milestone activities; a live API + worker + Postgres + Temporal runbook proves the end-to-end comment → resubmission → approval/inspection lifecycle with Postgres evidence; deferred S01 integration tests pass in provisioned Temporal environment.

## Boundary Map
### S01 → S02
Produces:
- New ORM models + migrations for CorrectionTask, ResubmissionPackage, ApprovalRecord, InspectionMilestone.
- Activities for persisting correction/resubmission/approval/inspection artifacts with idempotency guards and case/submission validation.
- Extended status mapping fixtures covering COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_*, INSPECTION_*.
- Workflow state branches for comment/resubmission/approval transitions (COMMENT_REVIEW_PENDING, CORRECTION_PENDING, RESUBMISSION_PENDING states exist in workflow).
- API read surfaces for new artifacts (following existing case read patterns).
- Deferred integration tests (tests/m011_s01_status_event_artifacts_test.py, tests/m011_s01_resubmission_workflow_test.py) proven structurally correct but blocked on infrastructure.

Consumes:
- ExternalStatusEvent normalization + persistence activity.
- SubmissionAttempt linkage and existing PermitCase state transition guard.

S02 must deliver:
- Wire normalized ExternalStatusEvent → workflow continuation (signal or activity invocation).
- Call persist_correction_task/persist_resubmission_package/persist_approval_record/persist_inspection_milestone from workflow when status events arrive.
- Provision Temporal development environment to execute deferred S01 integration tests.
- End-to-end docker-compose runbook proving submit → comment → resubmit → approve/inspect lifecycle with Postgres evidence.
