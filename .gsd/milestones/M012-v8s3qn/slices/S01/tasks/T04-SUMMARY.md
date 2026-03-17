---
id: T04
parent: S01
milestone: M012-v8s3qn
provides:
  - Override guard enforcement in apply_state_transition with OVERRIDE_DENIED ledger entries and warning logs
key_files:
  - src/sps/workflows/permit_case/activities.py
  - tests/m012_s01_override_guard_unit_test.py
key_decisions:
  - Override denial reasons normalized to missing/expired/out_of_scope and evaluated against requested_at for expiry checks
patterns_established:
  - Guard helper returns DeniedStateTransitionResult and emits workflow.override_denied before ledger persistence
observability_surfaces:
  - workflow.override_denied warning log; case_transition_ledger OVERRIDE_DENIED payload with guard_assertion_id
  - tests/m012_s01_override_guard_unit_test.py
  - tests/m012_s01_override_guard_test.py
  - tests/m012_s01_emergency_hold_test.py
  - scripts/verify_m012_s01.sh
duration: 1h
verification_result: partial (unit tests pass; slice checks missing files)
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Override guard in apply_state_transition activity

**Added override validation in apply_state_transition with OVERRIDE_DENIED guard enforcement and unit tests for all paths.**

## What Happened
- Added OVERRIDE_DENIED constants and guard assertion wiring (INV-SPS-EMERG-001) plus OverrideArtifact import.
- Implemented _validate_override helper to enforce override existence, expiry, and affected_surfaces scope, emitting workflow.override_denied logs and guard metadata in denial payloads.
- Wired override guard into the REVIEW_PENDING → APPROVED_FOR_SUBMISSION protected transition before the review gate.
- Added unit tests covering no override, missing/expired/out-of-scope overrides, and valid override pass-through.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m012_s01_override_guard_unit_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m012_s01_override_guard_test.py -v` (fails: file missing)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m012_s01_emergency_hold_test.py -v` (fails: file missing)
- `bash scripts/verify_m012_s01.sh` (fails: file missing)

## Diagnostics
- Check OVERRIDE_DENIED entries: `SELECT event_type, payload FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY occurred_at DESC;`
- Structured warning log: `workflow.override_denied` with guard_assertion_id=INV-SPS-EMERG-001 and normalized_business_invariants.

## Deviations
- None.

## Known Issues
- Slice verification artifacts `tests/m012_s01_override_guard_test.py`, `tests/m012_s01_emergency_hold_test.py`, and `scripts/verify_m012_s01.sh` are not present yet (expected for later tasks).

## Files Created/Modified
- `src/sps/workflows/permit_case/activities.py` — added OVERRIDE_DENIED guard helper and wiring in apply_state_transition.
- `tests/m012_s01_override_guard_unit_test.py` — unit tests for override guard success/denial paths.
- `.gsd/milestones/M012-v8s3qn/slices/S01/S01-PLAN.md` — marked T04 complete.
- `.gsd/STATE.md` — advanced next action to T05.
