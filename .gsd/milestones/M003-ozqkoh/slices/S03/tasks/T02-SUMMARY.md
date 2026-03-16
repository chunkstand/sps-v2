---
id: T02
parent: S03
milestone: M003-ozqkoh
provides:
  - Contradiction guard in apply_state_transition — blocking open contradictions deny REVIEW_PENDING→APPROVED_FOR_SUBMISSION with event_type=CONTRADICTION_ADVANCE_DENIED, guard_assertion_id=INV-SPS-CONTRA-001, normalized_business_invariants=["INV-003"]
key_files:
  - src/sps/workflows/permit_case/activities.py
key_decisions:
  - Contradiction check runs before ReviewDecision check inside the same with_for_update=True lock, ensuring contradiction denials take precedence in the ledger and no race with concurrent resolve is possible
patterns_established:
  - Guard precedence: contradiction denial → review gate denial → approval; each guard has its own event_type and guard_assertion_id constant pair
observability_surfaces:
  - "activity.denied name=apply_state_transition ... event_type=CONTRADICTION_ADVANCE_DENIED" — existing log infrastructure, no new lines
  - "SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at" — denial row has full DeniedStateTransitionResult payload with guard_assertion_id and normalized_business_invariants
duration: ~10m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Contradiction guard in `apply_state_transition`

**Contradiction guard inserted — blocking open contradictions now deny advancement before the review gate check.**

## What Happened

Added two module-level constants (`_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"`, `_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"`) alongside the existing `_EVENT_APPROVAL_GATE_DENIED` constant block. Added `ContradictionArtifact` to the `sps.db.models` import line.

In the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` branch, inserted a `session.query(ContradictionArtifact)` block immediately after the `case.case_state != req.from_state.value` early-exit check and before the ReviewDecision lookup. The query filters on `case_id == req.case_id`, `blocking_effect IS TRUE`, and `resolution_status == 'OPEN'`. If any row is found, `_deny()` is called with the contradiction constants and `get_normalized_business_invariants("INV-SPS-CONTRA-001")` (which returns `["INV-003"]`). The ReviewDecision check is now the `else` branch, preserving its behavior unchanged.

The query runs inside the existing `with session.begin()` block, after the `session.get(PermitCase, ..., with_for_update=True)` row lock — preventing a race where a contradiction is resolved between the guard check and the state write.

## Verification

- `.venv/bin/python -c "from sps.workflows.permit_case.activities import _EVENT_CONTRADICTION_ADVANCE_DENIED, _GUARD_ASSERTION_CONTRADICTION; print(...)` → `CONTRADICTION_ADVANCE_DENIED INV-SPS-CONTRA-001` ✓
- `.venv/bin/python -c "from sps.workflows.permit_case.activities import apply_state_transition; print('ok')"` → `ok` ✓
- `pytest tests/ -k "not (integration or temporal)" -x -q` → `9 passed, 7 skipped` ✓

## Diagnostics

After a blocking contradiction blocks advancement:
- `SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY occurred_at` shows a row with `event_type='CONTRADICTION_ADVANCE_DENIED'`; `payload` contains `denial_reason='BLOCKING_CONTRADICTION_UNRESOLVED'`, `guard_assertion_id='INV-SPS-CONTRA-001'`, `normalized_business_invariants=['INV-003']`
- Log grep: `activity.denied name=apply_state_transition ... event_type=CONTRADICTION_ADVANCE_DENIED`

## Deviations

None. Implementation matched the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/sps/workflows/permit_case/activities.py` — two new constants; `ContradictionArtifact` import added; contradiction guard block inserted before ReviewDecision check (ReviewDecision check becomes `else` branch)
- `.gsd/milestones/M003-ozqkoh/slices/S03/tasks/T02-PLAN.md` — added missing `## Observability Impact` section (pre-flight fix)
