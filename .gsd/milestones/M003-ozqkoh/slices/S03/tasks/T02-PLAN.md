---
estimated_steps: 4
estimated_files: 1
---

# T02: Contradiction guard in `apply_state_transition`

**Slice:** S03 — Contradiction artifacts + advancement blocking  
**Milestone:** M003-ozqkoh

## Description

Inserts the blocking-contradiction check into the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` guard branch in `apply_state_transition`. The check queries `contradiction_artifacts` for rows with `blocking_effect=True` and `resolution_status='OPEN'` for the target `case_id`. If any exist, the activity returns a `DeniedStateTransitionResult` with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, and `normalized_business_invariants=["INV-003"]`. This must happen *before* the ReviewDecision check so that contradiction denials take precedence in the audit trail.

The query must run inside the existing `with session.begin()` block after the `session.get(PermitCase, ..., with_for_update=True)` lock — this prevents a race where a contradiction is resolved concurrently with the transition attempt.

No workflow changes, no new tests here — the guard change is verified by T04's integration tests. This task only adds constants and a query block.

## Steps

1. At the top of `src/sps/workflows/permit_case/activities.py`, add two module-level constants next to `_EVENT_APPROVAL_GATE_DENIED`:
   ```python
   _EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"
   _GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"
   ```
2. Add `ContradictionArtifact` to the import from `sps.db.models`.
3. In the `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` branch, after the `case.case_state != req.from_state.value` check (which exits early on state mismatch) and before `review_id = req.required_review_id`, insert the contradiction query block:
   ```python
   # Guard: blocking open contradictions must be resolved before advancement (CTL-14A).
   blocking_contradiction = (
       session.query(ContradictionArtifact)
       .filter(
           ContradictionArtifact.case_id == req.case_id,
           ContradictionArtifact.blocking_effect.is_(True),
           ContradictionArtifact.resolution_status == "OPEN",
       )
       .first()
   )
   if blocking_contradiction is not None:
       result = _deny(
           denied_at=requested_at,
           event_type=_EVENT_CONTRADICTION_ADVANCE_DENIED,
           denial_reason="BLOCKING_CONTRADICTION_UNRESOLVED",
           guard_assertion_id=_GUARD_ASSERTION_CONTRADICTION,
           normalized_business_invariants=get_normalized_business_invariants(
               _GUARD_ASSERTION_CONTRADICTION
           ),
       )
   else:
       # existing ReviewDecision check follows here
   ```
   The ReviewDecision check block becomes the `else` branch.
4. Confirm no changes are needed to the idempotency path (the existing ledger short-circuit runs before entering the guard branch — no modification needed).

## Must-Haves

- [ ] `_EVENT_CONTRADICTION_ADVANCE_DENIED` and `_GUARD_ASSERTION_CONTRADICTION` constants defined.
- [ ] `ContradictionArtifact` imported in `activities.py`.
- [ ] Contradiction check is inside `with session.begin()` block, after `with_for_update=True` lock, before `review_id = req.required_review_id`.
- [ ] Non-integration tests still pass after the change.

## Verification

- `python -c "from sps.workflows.permit_case.activities import _EVENT_CONTRADICTION_ADVANCE_DENIED, _GUARD_ASSERTION_CONTRADICTION; print(_EVENT_CONTRADICTION_ADVANCE_DENIED, _GUARD_ASSERTION_CONTRADICTION)"` → `CONTRADICTION_ADVANCE_DENIED INV-SPS-CONTRA-001`
- `python -c "from sps.workflows.permit_case.activities import apply_state_transition; print('ok')"` → ok
- `pytest tests/ -k "not (integration or temporal)" -x -q` → still passes

## Inputs

- `src/sps/workflows/permit_case/activities.py` — existing `apply_state_transition` implementation; the `_deny()` helper; `_EVENT_APPROVAL_GATE_DENIED` constant as structural reference
- `src/sps/guards/guard_assertions.py` — `get_normalized_business_invariants("INV-SPS-CONTRA-001")` returns `["INV-003"]`
- `src/sps/db/models.py` (T01 output) — `ContradictionArtifact` with `blocking_effect`, `resolution_status`, `case_id` columns

## Observability Impact

**What signals change:** `apply_state_transition` already emits `activity.denied` log lines with `event_type` in the message. After this change, a blocking contradiction produces `event_type=CONTRADICTION_ADVANCE_DENIED` in both the structured log line and the `case_transition_ledger.payload` JSONB column. The existing logging infrastructure captures it without modification.

**How a future agent inspects this task's effect:**
- `SELECT event_type, payload FROM case_transition_ledger WHERE case_id = '<id>' ORDER BY occurred_at;` — denial rows have `event_type='CONTRADICTION_ADVANCE_DENIED'`; `payload` contains `guard_assertion_id='INV-SPS-CONTRA-001'` and `normalized_business_invariants=['INV-003']`
- Log grep: `grep "activity.denied.*CONTRADICTION_ADVANCE_DENIED"` finds every denied advancement caused by a blocking contradiction

**Failure state visible:** When a transition is denied due to a blocking contradiction, the denial is persisted to `case_transition_ledger` atomically (inside the same `session.begin()` block as the `with_for_update` lock). The denial payload is the full `DeniedStateTransitionResult` model dump — `event_type`, `denial_reason`, `guard_assertion_id`, and `normalized_business_invariants` are all present and inspectable without touching Temporal.

**No new log lines added** — the guard piggybacks on existing `activity.denied` telemetry.

## Expected Output

- `src/sps/workflows/permit_case/activities.py` — two new constants; `ContradictionArtifact` import; contradiction guard block inserted in the correct position inside the protected transition branch
