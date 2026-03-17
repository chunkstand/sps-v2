---
estimated_steps: 5
estimated_files: 3
---

# T03: Wire resubmission loop + approval/inspection workflow branches

**Slice:** S01 — Post-submission artifacts + workflow wiring
**Milestone:** M011-kg7s2p

## Description
Wire PermitCaseWorkflow to consume post-submission statuses, advance through comment/resubmission states, and persist approval/inspection milestones under guarded transitions.

## Steps
1. Add workflow branches for COMMENT_ISSUED → COMMENT_REVIEW_PENDING and RESUBMISSION_REQUESTED → RESUBMISSION_PENDING transitions.
2. Ensure correction/resubmission artifacts are tied to the latest submission_attempt_id in workflow state.
3. Wire approval/inspection status handling to apply_state_transition and persistence activities.
4. Add Temporal integration tests covering comment → correction → resubmission → submitted loop.
5. Extend tests to assert approval/inspection artifacts are persisted and queryable.

## Must-Haves
- [ ] Workflow transitions through comment/resubmission loop without losing prior history.
- [ ] Approval/inspection artifacts are persisted during workflow processing.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m011_s01_resubmission_workflow_test.py -v -s`

## Observability Impact
- Signals added/changed: transition ledger entries for post-submission state changes
- How a future agent inspects this: workflow test logs + `case_transition_ledger` rows for case_id
- Failure state exposed: guard denial rows with guard_assertion_id and workflow correlation_id

## Inputs
- `src/sps/workflows/permit_case/workflow.py` — existing submission + tracking branches
- `src/sps/workflows/permit_case/activities.py` — state transition + status event activities

## Expected Output
- `src/sps/workflows/permit_case/workflow.py` — resubmission + approval/inspection branch wiring
- `tests/m011_s01_resubmission_workflow_test.py` — Temporal integration coverage for post-submission loop
