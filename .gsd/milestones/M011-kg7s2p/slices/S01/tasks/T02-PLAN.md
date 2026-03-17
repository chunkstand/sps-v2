---
estimated_steps: 5
estimated_files: 4
---

# T02: Persist artifacts from status events + extend status maps

**Slice:** S01 — Post-submission artifacts + workflow wiring
**Milestone:** M011-kg7s2p

## Description
Extend status mapping fixtures for comment/resubmission/approval/inspection events and add persistence activities that translate normalized statuses into durable artifacts with idempotent behavior.

## Steps
1. Extend Phase 7 status-map fixtures with COMMENT_ISSUED, RESUBMISSION_REQUESTED, APPROVAL_*, INSPECTION_* mappings.
2. Add activity helpers to persist CorrectionTask/ResubmissionPackage/ApprovalRecord/InspectionMilestone rows with idempotency guards.
3. Validate case/submission_attempt linkage inside persistence activities.
4. Wire persistence from status normalization results where appropriate.
5. Add integration tests asserting artifact creation + idempotent replay.

## Must-Haves
- [ ] Status map fixtures cover comment/resubmission/approval/inspection statuses with fail-closed normalization.
- [ ] Artifact persistence activities are idempotent and enforce case/submission consistency.

## Verification
- `pytest tests/m011_s01_status_event_artifacts_test.py -v`

## Observability Impact
- Signals added/changed: activity logs for artifact persistence outcomes and idempotent replays
- How a future agent inspects this: query artifact tables + external_status_events rows for case_id
- Failure state exposed: logged activity errors with request_id and case_id

## Inputs
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — existing status mapping structure
- `src/sps/workflows/permit_case/activities.py` — external status normalization activity pattern

## Expected Output
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — new mappings for post-submission statuses
- `src/sps/workflows/permit_case/activities.py` — persistence helpers for new artifacts
- `tests/m011_s01_status_event_artifacts_test.py` — activity-level artifact persistence coverage
