---
id: T07
parent: S01
milestone: M012-v8s3qn
provides:
  - EMERGENCY_HOLD integration tests proving entry, forbidden direct submission, and exit transitions
key_files:
  - tests/m012_s01_emergency_hold_test.py
  - src/sps/workflows/permit_case/activities.py
key_decisions:
  - Deny EMERGENCY_HOLD → SUBMITTED transitions with STATE_TRANSITION_DENIED + FORBIDDEN_TRANSITION to enforce spec section 9.3.
patterns_established:
  - Temporal+Postgres integration tests that use API-created artifacts and workflow signals with ledger correlation assertions.
observability_surfaces:
  - case_transition_ledger CASE_STATE_CHANGED rows for EMERGENCY_HOLD entry/exit and STATE_TRANSITION_DENIED for forbidden transitions
  - workflow.emergency_hold_entered / workflow.emergency_hold_exited logs (existing)
duration: 1.5h
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T07: Integration tests for EMERGENCY_HOLD transitions

**Added Temporal+Postgres integration tests for EMERGENCY_HOLD entry/exit and enforced forbidden direct SUBMITTED transitions.**

## What Happened
- Added `tests/m012_s01_emergency_hold_test.py` to exercise emergency declaration via API, workflow EmergencyHoldEntry/Exit signals, and ledger correlation checks.
- Introduced a forbidden transition guard in `apply_state_transition` to deny EMERGENCY_HOLD → SUBMITTED with `STATE_TRANSITION_DENIED` + `FORBIDDEN_TRANSITION` per spec section 9.3.
- Adjusted review decision creation in exit tests to use reviewer JWT auth and avoid unintended workflow transitions by creating the review decision before workflow start.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_emergency_hold_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_override_guard_test.py -v`
- `bash scripts/verify_m012_s01.sh` → **failed** (script missing).
- `docker compose exec postgres psql -U sps -d sps -c "SELECT override_id, expires_at < NOW() as expired FROM override_artifacts ORDER BY created_at DESC LIMIT 5"`
- `docker compose exec postgres psql -U sps -d sps -c "SELECT event_type, details->>'guard_assertion_id' as guard_id FROM transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY created_at DESC LIMIT 3"` → **failed** (relation transition_ledger missing).

## Diagnostics
- Inspect EMERGENCY_HOLD transitions: `SELECT event_type, from_state, to_state, correlation_id FROM case_transition_ledger WHERE to_state='EMERGENCY_HOLD' OR from_state='EMERGENCY_HOLD' ORDER BY occurred_at DESC;`
- Confirm forbidden SUBMITTED transition remains denied: `SELECT event_type, from_state, to_state FROM case_transition_ledger WHERE to_state='SUBMITTED' ORDER BY occurred_at DESC LIMIT 5;`

## Deviations
- Added a forbidden transition guard for EMERGENCY_HOLD → SUBMITTED in `apply_state_transition` to align implementation with spec 9.3.

## Known Issues
- `scripts/verify_m012_s01.sh` does not exist yet (T08).
- Verification query references a non-existent `transition_ledger` table; current table is `case_transition_ledger` with payload in `payload` column.

## Files Created/Modified
- `tests/m012_s01_emergency_hold_test.py` — integration tests covering emergency hold entry/exit and forbidden transitions.
- `src/sps/workflows/permit_case/activities.py` — added forbidden EMERGENCY_HOLD → SUBMITTED guard denial.
