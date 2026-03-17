---
estimated_steps: 5
estimated_files: 1
---

# T07: Integration tests for EMERGENCY_HOLD transitions

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Prove EMERGENCY_HOLD entry/exit transitions require valid artifacts (emergency_id and reviewer_confirmation_id) via Temporal+Postgres integration tests. Validates that EMERGENCY_HOLD → SUBMITTED is forbidden and exit requires cleanup workflow.

## Steps

1. Create tests/m012_s01_emergency_hold_test.py with Temporal+Postgres test harness
2. Test case 1: POST /emergencies to create EmergencyRecord; send EmergencyHoldEntry signal to workflow with emergency_id → case enters EMERGENCY_HOLD state; query transition ledger and assert CASE_STATE_CHANGED event with to_state=EMERGENCY_HOLD
3. Test case 2: Attempt EMERGENCY_HOLD → SUBMITTED transition via apply_state_transition (without exit signal) → transition denied (forbidden per spec section 9.3); assert no CASE_STATE_CHANGED event for SUBMITTED
4. Test case 3: POST /reviews/decisions to create ReviewDecision; send EmergencyHoldExit signal with reviewer_confirmation_id → case exits EMERGENCY_HOLD to REVIEW_PENDING; query ledger and assert CASE_STATE_CHANGED event with from_state=EMERGENCY_HOLD, to_state=REVIEW_PENDING
5. Assert all state transitions are correlated in ledger with workflow_id and include expected from_state/to_state values

## Must-Haves

- [ ] Test case proving EMERGENCY_HOLD entry with valid emergency_id succeeds
- [ ] Test case proving EMERGENCY_HOLD → SUBMITTED is forbidden (denied transition)
- [ ] Test case proving EMERGENCY_HOLD exit with reviewer_confirmation_id succeeds
- [ ] Transition ledger assertions for all state changes (entry, forbidden direct exit, valid exit)

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_emergency_hold_test.py -v` passes all 3 test cases
- docker compose exec postgres psql shows CASE_STATE_CHANGED events for EMERGENCY_HOLD entry and exit, no event for forbidden SUBMITTED transition

## Inputs

- EMERGENCY_HOLD signal handlers from T05 (workflow.py)
- EmergencyRecord and ReviewDecision ORM models (T01 + existing)
- Temporal signal delivery pattern from Phase 3 M003/S01
- Forbidden transition enforcement from spec section 9.3

## Expected Output

- `tests/m012_s01_emergency_hold_test.py` — 3 integration test cases proving EMERGENCY_HOLD lifecycle with signal-based entry/exit and forbidden direct transitions

## Observability Impact

- Signals touched: `workflow.emergency_hold_entered`, `workflow.emergency_hold_exited` logs and `CASE_STATE_CHANGED` transition ledger events are asserted indirectly in integration tests.
- Inspection path: use `docker compose exec postgres psql -U sps -d sps -c "SELECT event_type, from_state, to_state, workflow_id FROM case_transition_ledger WHERE to_state='EMERGENCY_HOLD' OR from_state='EMERGENCY_HOLD' ORDER BY occurred_at DESC;"` to validate entry/exit events, and check Temporal worker logs for the workflow log signals above.
- Failure visibility: missing/invalid artifacts should surface as denied transitions (no CASE_STATE_CHANGED rows), and forbidden EMERGENCY_HOLD → SUBMITTED attempts should leave the ledger without a SUBMITTED transition.
