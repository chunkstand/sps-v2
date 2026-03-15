---
id: T01
parent: S02
milestone: M002-dq2dn9
provides:
  - Postgres-backed, fail-closed Temporal activity for authoritative PermitCase state transitions with idempotent audit/ledger writes (denied + applied)
key_files:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/guards/guard_assertions.py
  - src/sps/workflows/worker.py
  - tests/m002_s02_transition_guard_db_idempotency_test.py
key_decisions:
  - Persist the JSON-serializable StateTransitionResult (applied/denied) as case_transition_ledger.payload and treat StateTransitionRequest.request_id as the ledger primary key for idempotency.
patterns_established:
  - Transaction-first activity pattern: (1) check ledger by request_id, (2) enforce guard preconditions, (3) insert ledger row, (4) update permit_cases.case_state only on applied.
observability_surfaces:
  - Durable denial/audit rows in Postgres: case_transition_ledger keyed by transition_id=request_id (inspect event_type + payload)
  - Structured activity logs: activity.start|activity.ok|activity.denied|activity.error with request_id/case_id/from_state/to_state/event_type/result
duration: 1h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Implement Postgres guarded transition + idempotent ledger writes (deny + applied)

**Shipped a Postgres-authoritative transition guard activity that writes an idempotent audit ledger row for both denials and applied transitions (request_id as PK), including a stable approval-gate denial payload.**

## What Happened

- Added contract-aligned typed boundary models:
  - `StateTransitionRequest` (Pydantic v2) aligned to `model/sps/contracts/state-transition-request.schema.json`.
  - `StateTransitionResult` union (`AppliedStateTransitionResult | DeniedStateTransitionResult`) suitable for JSON persistence.
- Implemented a small cached guard assertion lookup (`INV-SPS-STATE-002 → [INV-001]`) backed by `invariants/sps/guard-assertions.yaml`.
- Implemented `apply_state_transition` as a Temporal activity that:
  - checks `case_transition_ledger` first for idempotency (duplicate request_id returns persisted prior result)
  - enforces `from_state` matches DB state
  - enforces the canonical protected transition (`REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) requires a persisted `ReviewDecision` with allowed outcome (`ACCEPT|ACCEPT_WITH_DISSENT`)
  - fails closed for unknown transitions or missing preconditions by returning structured `denied` results (no exception)
  - persists both denials and applied outcomes to `case_transition_ledger` and updates `permit_cases.case_state` only on applied
- Registered the new activity in the Temporal worker.
- Added a Postgres-backed integration test proving idempotency for both an applied transition and a governance denial, including stable denial payload assertions.

## Verification

- Passed: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`
- Slice-level workflow verification not run in this task (file not yet implemented; expected in T02):
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py` (currently missing)

## Diagnostics

- Query by request_id:
  - `SELECT event_type, payload FROM case_transition_ledger WHERE transition_id = '<request_id>';`
- Denial audit is durable:
  - For the approval gate, expect `event_type=APPROVAL_GATE_DENIED` and payload keys `guard_assertion_id=INV-SPS-STATE-002` and `normalized_business_invariants` containing `INV-001`.
- Worker logs include correlation tuple (when run under the worker): `request_id`, `case_id`, `from_state`, `to_state`, `event_type`, `result`.

## Deviations

- None.

## Known Issues

- The end-to-end Temporal workflow integration test for denial→signal unblock→apply is not yet present; it is planned for T02.

## Files Created/Modified

- `src/sps/workflows/permit_case/contracts.py` — added contract-aligned `StateTransitionRequest` + `StateTransitionResult` models.
- `src/sps/guards/guard_assertions.py` — YAML-backed, cached guard assertion → invariant lookup.
- `src/sps/workflows/permit_case/activities.py` — implemented `apply_state_transition` activity with atomic idempotent ledger writes.
- `src/sps/workflows/worker.py` — registered `apply_state_transition` with the Temporal worker.
- `tests/m002_s02_transition_guard_db_idempotency_test.py` — Postgres-backed idempotency + denial payload assertions.
