---
id: S02
parent: M002-dq2dn9
milestone: M002-dq2dn9
provides:
  - Postgres-authoritative guarded PermitCase state transitions (fail-closed) with durable, idempotent transition/audit ledger (denied + applied) and a canonical Temporal signal-driven review-unblock workflow path
requires:
  - slice: S01
    provides: Temporal worker + PermitCaseWorkflow (signal wait) + CLI harness + Postgres session pattern
affects:
  - S03
key_files:
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/worker.py
  - src/sps/workflows/cli.py
  - src/sps/guards/guard_assertions.py
  - invariants/sps/guard-assertions.yaml
  - tests/m002_s02_transition_guard_db_idempotency_test.py
  - tests/m002_s02_temporal_guarded_transition_workflow_test.py
key_decisions:
  - Persist the JSON-serializable StateTransitionResult into case_transition_ledger.payload and use StateTransitionRequest.request_id as the ledger primary key for DB-enforced idempotency.
  - Use deterministic workflow correlation/request IDs derived from workflow_id+run_id (attempt-suffixed) to make ledger/review writes replay-safe and inspectable without workflow-side UUID generation.
patterns_established:
  - Transaction-first authoritative activity: (1) check ledger by request_id, (2) enforce guard preconditions, (3) insert ledger row (denied or applied), (4) update permit_cases.case_state only on applied.
  - Denial-driven workflow orchestration: attempt guarded transition → on APPROVAL_GATE_DENIED wait → signal ReviewDecision → persist review idempotently → re-attempt guarded transition.
observability_surfaces:
  - Durable ledger rows in Postgres (case_transition_ledger.transition_id=request_id) for both denials and applied transitions.
  - Structured workflow/activity logs with correlation tuple: workflow_id, run_id, case_id, request_id, event_type.
drill_down_paths:
  - .gsd/milestones/M002-dq2dn9/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002-dq2dn9/slices/S02/tasks/T02-SUMMARY.md
duration: 3h
verification_result: passed
completed_at: 2026-03-15
---

# S02: Postgres-backed guarded transitions (deny + audit) + signal-driven review unblock

**Shipped a Postgres-authoritative, fail-closed transition guard (denials + applied) with an idempotent audit ledger, and proved the canonical workflow path: denied protected transition → wait → signal review decision → persist → apply.**

## What Happened

- Added/expanded contract-aligned Pydantic v2 boundary models for:
  - `StateTransitionRequest` validation at the guard boundary.
  - `StateTransitionResult` as a JSON-serializable applied/denied union persisted into `case_transition_ledger.payload`.
  - Canonical review decision enums and a signal payload model aligned to the proof path.
- Implemented a YAML-backed guard assertion lookup (`INV-SPS-STATE-002 → [INV-001]`) and used it to produce stable denial payloads.
- Implemented `apply_state_transition(request)` Temporal activity as the *only authoritative* PermitCase mutation path for the proof transition:
  - Enforces `from_state` matches the DB row.
  - Fail-closed allowlist: denies unknown transitions.
  - Enforces the protected gate for `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` (requires a persisted valid `ReviewDecision`).
  - Persists *both* denials and applied outcomes to `case_transition_ledger`, keyed by `request_id` for idempotency under retries.
  - Updates `permit_cases.case_state` only on an applied transition.
- Implemented `persist_review_decision(...)` activity to write `review_decisions` idempotently using the table’s unique `idempotency_key`.
- Updated `PermitCaseWorkflow` to orchestrate:
  - initial guarded attempt (expected denial)
  - deterministic wait for `ReviewDecision` signal
  - idempotent persistence of the review decision
  - second guarded attempt that applies and completes the workflow
- Updated the operator CLI to send canonical `ReviewDecisionOutcome` values.

## Verification

- Passed (DB-level integration / idempotency + stable denial payload):
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`
- Passed (Temporal+Postgres end-to-end proof: deny → wait → signal → persist → apply):
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`
- Observability spot-check (live runtime): started worker + used CLI to run a case through the canonical flow and confirmed structured `workflow.*` + `activity.*` logs with correlation tuple.

## Requirements Advanced

- R004 — Exercises the Temporal harness with a non-trivial workflow path (guarded activity denial → wait → signal → resume) and idempotent activities, strengthening the substrate ahead of S03 replay-focused proofs.

## Requirements Validated

- R005 — Proven by Temporal+Postgres integration tests that the protected transition `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` is denied without a valid ReviewDecision (durable `APPROVAL_GATE_DENIED` ledger event including `INV-SPS-STATE-002` + `INV-001`) and succeeds after signal-driven ReviewDecision persistence.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

none

## Known Limitations

- Replay-history determinism and “no duplicated side effects under workflow replay / activity retry across worker restarts” is not fully closed yet; S03 is still responsible for replay-based proofs.
- Local Temporal dev clusters can retain old workflow histories across runs; if Postgres is reset independently, old executions may retry activities against missing rows (expected in dev, but noisy).

## Follow-ups

- In S03, add explicit replay/idempotency proofs using captured workflow histories and ledger row-count invariants.
- Consider adding a dev-only runbook step to reset Temporal state when resetting Postgres to avoid noisy retries from prior runs.

## Files Created/Modified

- `src/sps/workflows/permit_case/contracts.py` — transition + review signal/request/result models (Pydantic v2) with canonical enums.
- `src/sps/guards/guard_assertions.py` — YAML-backed guard assertion → invariant lookup.
- `src/sps/workflows/permit_case/activities.py` — authoritative `apply_state_transition` + idempotent `persist_review_decision`.
- `src/sps/workflows/permit_case/workflow.py` — denial→wait→signal→persist→re-attempt→apply orchestration path.
- `src/sps/workflows/worker.py` — worker registers new activities.
- `src/sps/workflows/cli.py` — CLI supports canonical decision outcomes.
- `tests/m002_s02_transition_guard_db_idempotency_test.py` — idempotency + stable denial payload assertions.
- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — Temporal+Postgres integration proof for the canonical flow.

## Forward Intelligence

### What the next slice should know
- The `request_id` primary key on `case_transition_ledger` is the core idempotency mechanism. Any future transition activities should preserve the “check ledger first, then insert + mutate” transaction pattern.
- Deterministic IDs (`workflow_id/run_id/...`) make Postgres inspection and Temporal-history correlation dramatically easier; keep that convention for new guarded transitions.

### What's fragile
- Local dev Temporal state can outlive Postgres resets; workflows that were mid-flight will continue retrying and can spam logs if their DB rows are gone.

### Authoritative diagnostics
- Postgres ledger (most trustworthy):
  - `SELECT transition_id, event_type, payload FROM case_transition_ledger WHERE correlation_id = '<workflow_id>:<run_id>' ORDER BY occurred_at;`
- Worker logs (correlation tuple): `workflow_id`, `run_id`, `case_id`, `request_id`, `event_type`.

### What assumptions changed
- Assumption: DB-level tests would visibly demonstrate structured activity logs under pytest.
  - Reality: runtime logs are best confirmed via the worker entrypoint (which configures logging level/format); pytest output may not show app logs depending on logging configuration.
