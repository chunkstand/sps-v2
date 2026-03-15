---
estimated_steps: 8
estimated_files: 6
---

# T01: Implement Postgres guarded transition + idempotent ledger writes (deny + applied)

**Slice:** S02 — Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock
**Milestone:** M002-dq2dn9

## Description

Introduce the authoritative Postgres-backed transition guard as a Temporal activity. The activity must be fail-closed, persist both denial and success outcomes to `case_transition_ledger`, and be idempotent under activity retry/replay by treating `StateTransitionRequest.request_id` as the ledger primary key.

This task also establishes the stable, test-assertable denial payload for the canonical protected transition (`REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) when no valid `ReviewDecision` is present: `event_type=APPROVAL_GATE_DENIED` with `guard_assertion_id=INV-SPS-STATE-002` and `normalized_business_invariants` containing `INV-001`.

## Steps

1. Add typed boundary models:
   - `StateTransitionRequest` (Pydantic v2) aligned to `model/sps/contracts/state-transition-request.schema.json`.
   - `StateTransitionResult` with `applied` vs `denied` shapes that are JSON-serializable for ledger payloads.
2. Implement a small guard assertion lookup that can resolve `INV-SPS-STATE-002 → [INV-001]` from `invariants/sps/guard-assertions.yaml` (cache in-process; activities are long-lived).
3. Implement `apply_state_transition(request)` as a Temporal activity (sync SQLAlchemy) that:
   - loads the `PermitCase` row and verifies `from_state` matches DB
   - for `REVIEW_PENDING → APPROVED_FOR_SUBMISSION`, enforces `required_review_id` present and references a persisted `ReviewDecision` with an allowed outcome
   - fails closed for unknown transitions or missing preconditions (return `denied`, do not raise)
4. Make the DB write atomic + idempotent:
   - in one transaction: if ledger row already exists for `request_id`, return its stored outcome
   - otherwise insert `case_transition_ledger` row with `transition_id=request_id` and a stable JSON payload
   - only on `applied` update `permit_cases.case_state`
5. Register the new activity with the worker so Temporal can execute it.
6. Add a Postgres-backed integration test that directly exercises the idempotency boundary (same `request_id` twice) and asserts:
   - ledger row count stability
   - state update occurs at most once
   - denial payload includes required guard IDs.

## Must-Haves

- [ ] `apply_state_transition(request_id=...)` persists a denial ledger row for missing review gate using `APPROVAL_GATE_DENIED` + `INV-SPS-STATE-002` + `INV-001`.
- [ ] Duplicate `request_id` returns the previously persisted result without duplicating ledger rows or re-applying state changes.
- [ ] Activity never raises for “governance denials” (returns structured `denied` result instead).

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`

## Observability Impact

- Signals added/changed: new activity log lines for `apply_state_transition` including `request_id`, `case_id`, `from_state`, `to_state`, `event_type`, and `result=applied|denied`.
- How a future agent inspects this: query `case_transition_ledger` by `transition_id=request_id` and inspect `event_type` + `payload`.
- Failure state exposed: durable denial entries (audit events) for protected transition attempts.

## Inputs

- `src/sps/db/models.py` — `PermitCase`, `ReviewDecision`, `CaseTransitionLedger` table shapes.
- `invariants/sps/guard-assertions.yaml` — authoritative mapping for guard assertion IDs to invariant IDs.

## Expected Output

- `src/sps/workflows/permit_case/activities.py` — new `apply_state_transition` activity (and any helper code kept activity-safe).
- `src/sps/workflows/worker.py` — registers `apply_state_transition`.
- `tests/m002_s02_transition_guard_db_idempotency_test.py` — DB-backed idempotency + denial payload assertions.
