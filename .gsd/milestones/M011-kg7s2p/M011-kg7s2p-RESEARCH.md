# M011-kg7s2p — Research
**Date:** 2026-03-16

## Summary
The codebase already has the post-submission primitives needed to anchor comment resolution and approval tracking: ExternalStatusEvent normalization/persistence, SubmissionAttempt linkage, and a deterministic PermitCaseWorkflow that only mutates state through `apply_state_transition`. However, there are no DB models, migrations, activities, or workflow branches for ReviewComment, CorrectionTask, ResubmissionPackage, ApprovalRecord, or InspectionMilestone; even the status mapping fixtures only cover approval/rejection statuses. The fastest path is to extend the data model/migrations and build activity-layer persistence modeled after `persist_external_status_event`, then wire minimal transitions and workflow branches that consume ExternalStatusEvent + SubmissionAttempt and emit durable artifacts.

Primary recommendation: prove the new artifacts and guard flow at the activity + integration-test layer before expanding workflow transitions. Use the existing status normalization activity and mappings as the entry point, then add deterministic, idempotent persistence for correction/resubmission/approval artifacts with explicit linkage to `case_id` and `submission_attempt_id`. Only after those tables and activities are proven should we introduce additional case-state transitions (COMMENT_REVIEW_PENDING → CORRECTION_PENDING → RESUBMISSION_PENDING → SUBMITTED/APPROVED) and runbook coverage.

## Recommendation
Follow the established Temporal + Postgres pattern: introduce new ORM models and migrations for ReviewComment, CorrectionTask, ResubmissionPackage, ApprovalRecord, and InspectionMilestone; add activities with idempotency checks and detailed structured logs; and reuse ExternalStatusEvent as the driver for comment/approval flows. Keep the workflow deterministic: all I/O stays in activities, and state transitions go through `apply_state_transition` with new guard cases. Start with integration tests that call activities directly (as in M007) to validate artifact persistence and fail-closed behavior before wiring full workflow/runbook paths.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| State transitions & governance denials | `apply_state_transition` in `permit_case/activities.py` | Ensures deterministic guard behavior, idempotent ledger writes, and stable denial identifiers; avoids silent state drift. |
| Status normalization & mapping selection | `persist_external_status_event` + `select_status_mapping_for_case` | Provides fail-closed status handling, case/submission linkage, and fixture-backed mapping versioning. |
| Evidence artifact storage | Evidence registry (Phase 1) | Keeps approval/inspection evidence stable, audited, and aligned with existing retention/legal-hold enforcement. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/contracts.py` — case-state enums already include COMMENT_REVIEW_PENDING/CORRECTION_PENDING/RESUBMISSION_PENDING/APPROVED, and ExternalStatusClass includes COMMENT_ISSUED/RESUBMISSION_REQUESTED/APPROVAL_*; reuse for new guards and activities.
- `src/sps/workflows/permit_case/activities.py` — `persist_external_status_event` shows idempotent, fail-closed persistence with session-scoped transactions and structured logs; mirror this pattern for correction/approval artifacts.
- `src/sps/workflows/permit_case/workflow.py` — workflow is deterministic and only calls activities; new branches must follow the same pattern (no direct DB I/O).
- `src/sps/db/models.py` — no ORM models yet for ReviewComment/CorrectionTask/ApprovalRecord/InspectionMilestone/ResubmissionPackage; will need to extend alongside migrations.
- `tests/m007_s02_external_status_events_test.py` — integration test style for activity-level Postgres proofs and fixture overrides; replicate for M011 artifacts.
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — current status mappings only cover approval/rejection; comment/resubmission statuses are missing and must be added or fixture-extended.

## Constraints
- Workflow determinism: all I/O must remain in activities; workflow changes must be pure orchestration (`workflow.execute_activity`).
- Guarded state mutation only via `apply_state_transition`; direct case_state updates are forbidden.
- ExternalStatusEvent is append-only with strict case/submission_attempt validation; new artifacts must link to valid attempts.
- Fixture-driven status mapping is the only normalization source; adding new statuses requires fixture updates.

## Common Pitfalls
- **Missing idempotency on new artifacts** — follow the existing pattern (unique IDs + lookup on IntegrityError) to avoid duplicate rows under retries.
- **Case/submission mismatch** — ensure new activities validate `submission_attempt.case_id` (same as `persist_external_status_event`).
- **Incomplete fixture mappings** — comment/resubmission statuses won’t normalize without fixture updates, causing fail-closed errors.

## Open Risks
- ResubmissionPackage is not defined in `model/sps/model.yaml` or ORM/migrations; scope alignment needs a decision before implementation.
- Transition guard expansion could become complex; start with minimal allowed paths to avoid unbounded state growth.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |
| Pydantic | bobmatnyc/claude-mpm-skills@pydantic | available (not installed) |

## Sources
- Workflow determinism + activity-only I/O pattern (source: `src/sps/workflows/permit_case/workflow.py`)
- Status normalization and idempotent persistence pattern (source: `src/sps/workflows/permit_case/activities.py`)
- Case state + status enums (source: `src/sps/workflows/permit_case/contracts.py`)
- Existing ExternalStatusEvent fixtures (source: `specs/sps/build-approved/fixtures/phase7/status-maps.json`)
- Integration test patterns for activity persistence (source: `tests/m007_s02_external_status_events_test.py`)
- Model definitions for CorrectionTask/ApprovalRecord/InspectionMilestone (source: `model/sps/model.yaml`)
