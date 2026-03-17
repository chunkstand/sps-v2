---
estimated_steps: 7
estimated_files: 3
---

# T05: EMERGENCY_HOLD state transitions in workflow

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Add EMERGENCY_HOLD state entry/exit transitions to PermitCaseWorkflow with signal handlers requiring valid emergency/reviewer artifacts. Enables governed emergency state management with cleanup workflow enforcement.

## Steps

1. Add EmergencyHoldRequest contract to src/sps/workflows/permit_case/contracts.py (emergency_id str, target_state=EMERGENCY_HOLD)
2. Add EmergencyHoldExitRequest contract to src/sps/workflows/permit_case/contracts.py (target_state str required, reviewer_confirmation_id str required)
3. Add @workflow.signal(name="EmergencyHoldEntry") handler in src/sps/workflows/permit_case/workflow.py that accepts EmergencyHoldRequest; validate emergency_id exists and not expired via activity call; request state transition to EMERGENCY_HOLD; emit log workflow.emergency_hold_entered (INFO, fields: workflow_id, case_id, emergency_id)
4. Add @workflow.signal(name="EmergencyHoldExit") handler in src/sps/workflows/permit_case/workflow.py that accepts EmergencyHoldExitRequest; validate reviewer_confirmation_id exists via activity call; request state transition from EMERGENCY_HOLD to target_state; emit log workflow.emergency_hold_exited (INFO, fields: workflow_id, case_id, target_state, reviewer_confirmation_id)
5. Add validate_emergency_artifact() activity in src/sps/workflows/permit_case/activities.py that queries EmergencyRecord by emergency_id and raises if not found or expired
6. Add validate_reviewer_confirmation() activity in src/sps/workflows/permit_case/activities.py that queries ReviewDecision by decision_id (aliased as reviewer_confirmation_id) and raises if not found
7. Wire both signal handlers into workflow execution flow to handle EMERGENCY_HOLD lifecycle

## Must-Haves

- [ ] EmergencyHoldRequest and EmergencyHoldExitRequest contracts
- [ ] EmergencyHoldEntry signal handler validates emergency_id and transitions to EMERGENCY_HOLD
- [ ] EmergencyHoldExit signal handler validates reviewer_confirmation_id and transitions from EMERGENCY_HOLD
- [ ] validate_emergency_artifact() activity enforces emergency existence and time bounds
- [ ] validate_reviewer_confirmation() activity enforces reviewer confirmation exists
- [ ] workflow.emergency_hold_entered and workflow.emergency_hold_exited logs emitted

## Verification

- Write tests/m012_s01_emergency_hold_workflow_test.py with test cases: test_emergency_hold_entry_with_valid_emergency, test_emergency_hold_entry_with_expired_emergency_raises, test_emergency_hold_exit_with_reviewer_confirmation, test_emergency_hold_exit_without_confirmation_raises
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_emergency_hold_workflow_test.py -v` passes all 4 test cases
- Transition ledger shows CASE_STATE_CHANGED events for EMERGENCY_HOLD entry and exit

## Observability Impact

- Signals added/changed: workflow.emergency_hold_entered (INFO, fields: workflow_id, case_id, emergency_id), workflow.emergency_hold_exited (INFO, fields: workflow_id, case_id, target_state, reviewer_confirmation_id)
- How a future agent inspects this: docker compose exec postgres psql -c "SELECT * FROM case_transition_ledger WHERE to_state='EMERGENCY_HOLD' OR from_state='EMERGENCY_HOLD'" or Temporal UI workflow history
- Failure state exposed: activity raises on invalid emergency_id or reviewer_confirmation_id; Temporal workflow execution shows failed activity in history

## Inputs

- CaseState.EMERGENCY_HOLD enum value from src/sps/workflows/permit_case/contracts.py
- EmergencyRecord ORM model from T01
- ReviewDecision ORM model (existing, for reviewer confirmation validation)
- Temporal signal handler pattern from Phase 3 ReviewDecisionSignal

## Expected Output

- `src/sps/workflows/permit_case/contracts.py` — EmergencyHoldRequest and EmergencyHoldExitRequest contracts
- `src/sps/workflows/permit_case/workflow.py` — EmergencyHoldEntry and EmergencyHoldExit signal handlers
- `src/sps/workflows/permit_case/activities.py` — validate_emergency_artifact() and validate_reviewer_confirmation() activities
