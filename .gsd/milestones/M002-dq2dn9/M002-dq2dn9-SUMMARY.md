---
id: M002-dq2dn9
provides:
  - Temporal+Postgres local harness (docker compose) with a Python worker entrypoint capable of running a real PermitCaseWorkflow end-to-end
  - Deterministic PermitCaseWorkflow orchestration (activities-only I/O) with signal-driven ReviewDecision injection
  - Postgres-authoritative, fail-closed PermitCase state transition guard with structured denials and an idempotent transition/audit ledger keyed by request_id
  - Replay/"exactly-once" proof surfaces: offline history replay determinism test + post-commit activity-retry idempotency test harness (failpoints)
  - Operator runbook script that drives the canonical scenario (deny → wait → signal → persist → apply) and asserts Postgres invariants
key_decisions:
  - "All authoritative PermitCase state transitions are evaluated and applied inside a Postgres transaction within a Temporal activity (workflow orchestrates only)"
  - "DB-enforced idempotency: StateTransitionRequest.request_id is the case_transition_ledger primary key; duplicates are treated as already-decided"
  - "Deterministic correlation/request IDs derived from workflow_id+run_id (no workflow-side UUID generation)"
  - "Offline replay uses the same Pydantic-aware Temporal data converter as the live client"
  - "Prove real activity retries post-commit using env-gated, key-addressable 'fail once' failpoints"
patterns_established:
  - "Deterministic workflows: no DB/network in workflow code; all I/O via activities"
  - "Transaction-first guard activity: check ledger by request_id → enforce guards/invariants → insert ledger (denied/applied) → mutate case_state only on applied"
  - "Denial-driven orchestration: attempt guarded transition → on APPROVAL_GATE_DENIED wait for ReviewDecision signal → persist decision idempotently → re-attempt"
  - "Replay determinism harness: run → fetch history → offline Replayer → assert no divergence"
  - "Exactly-once harness: commit authoritative write → fire post-commit failpoint → Temporal retry → assert stable DB row counts"
observability_surfaces:
  - "Temporal UI (http://localhost:8080) workflow history shows activity execution, signals, and completion"
  - "Postgres case_transition_ledger rows (denied + applied) keyed by request_id; correlated via correlation_id=workflow_id:run_id"
  - "Worker structured logs keyed by workflow_id/run_id/case_id/request_id"
  - "Runbook: bash scripts/verify_m002_s03_runbook.sh (prints workflow_id/run_id + Postgres summary)"
requirement_outcomes:
  - id: R004
    from_status: active
    to_status: validated
    proof: "Temporal+Postgres integration tests (S01/S03) + offline Replayer determinism test + post-commit activity retry idempotency test + runbook verification"
  - id: R005
    from_status: active
    to_status: validated
    proof: "Temporal+Postgres integration tests proving protected transition denial/apply with invariant IDs, plus replay/retry proofs keeping ledger effects exactly-once"
duration: 7h30m
verification_result: passed
completed_at: 2026-03-16T00:08:36Z
---

# M002-dq2dn9: Phase 2 — Temporal harness + guarded state transitions

**Temporal is now a real, replay-safe harness for PermitCase progression: guarded Postgres state transitions fail closed with durable denials, a signal-driven ReviewDecision unblocks the canonical protected transition, and determinism/idempotency are proven via replay and real activity retries.**

## What Happened

This milestone converted the Phase 1 data foundation into a governable workflow substrate.

Across S01→S03 we built a minimal but *real* PermitCase workflow running on docker-compose Temporal+Postgres, then tightened the authority boundary so the workflow cannot mutate PermitCase state directly:

- **S01** established the deterministic Temporal boundary (activities-only I/O): a worker, a minimal PermitCaseWorkflow that waits for a ReviewDecision signal, and an operator CLI.
- **S02** introduced the **authoritative Postgres guard** and **idempotent transition ledger**. The protected transition proof path (`REVIEW_PENDING → APPROVED_FOR_SUBMISSION`) is fail-closed: without a persisted ReviewDecision, the guard denies with stable guard/invariant identifiers and persists the denial to the ledger.
- **S03** closed the remaining Temporal risks by proving:
  - **offline replay determinism** (Temporal Replayer on a captured history)
  - **exactly-once DB effects under real activity retries** using test-only post-commit failpoints
  - a one-command **operator runbook** that drives the canonical deny→signal→apply flow and asserts Postgres invariants.

The net result is a Temporal+Postgres harness that later phases (reviewer service, contradiction governance, submission adapters) can rely on without re-opening determinism or fail-open authority risks.

## Cross-Slice Verification

Success criteria were verified against *live* docker-compose Temporal+Postgres plus automated integration tests:

1) **Local docker compose Temporal + Postgres + a Python worker runs PermitCaseWorkflow end-to-end; run visible in Temporal UI**
   - `docker compose up -d`
   - `bash scripts/verify_m002_s03_runbook.sh` (starts worker, starts workflow, signals, waits, asserts Postgres)
   - Temporal UI verification (direct history navigation for a real run):
     - Navigated to `http://localhost:8080/namespaces/default/workflows/permit-case%2FM002-S03-20260315180600-65425/019cf3f6-c00e-7d86-8fb9-08aad0e0448d/history`
     - Asserted presence of `Workflow Execution Signaled` (`Signal Name ReviewDecision`) and `Workflow Execution Completed`.

2) **Protected transition is denied fail-closed without ReviewDecision; denial includes guard/invariant IDs and is persisted as ledger/audit**
   - Runbook output showed initial denial result:
     - `event_type=APPROVAL_GATE_DENIED`, `guard_assertion_id=INV-SPS-STATE-002`, `normalized_business_invariants=[INV-001]`
   - Runbook Postgres assertions showed durable ledger presence:
     - `APPROVAL_GATE_DENIED|1`
   - Automated integration coverage:
     - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_transition_guard_db_idempotency_test.py`
     - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`

3) **Signal-driven ReviewDecision unblocks and guarded transition succeeds, updating authoritative Postgres state**
   - Runbook: `signal-review --wait` then final result applied (`event_type=CASE_STATE_CHANGED`) and Postgres summary:
     - `CASE_STATE_CHANGED|1` and a persisted `review_decisions` row keyed by `review/<workflow_id>/<run_id>`.
   - Automated integration coverage:
     - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s02_temporal_guarded_transition_workflow_test.py`

4) **Replay/idempotency proven (no duplicated ledger effects under replay/retry; deterministic denials for same DB snapshot)**
   - Offline determinism replay:
     - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
   - Post-commit activity retry idempotency:
     - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`

Full re-verification run (this unit):
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q \
    tests/m002_s01_temporal_permit_case_workflow_test.py \
    tests/m002_s02_transition_guard_db_idempotency_test.py \
    tests/m002_s02_temporal_guarded_transition_workflow_test.py \
    tests/m002_s03_temporal_replay_determinism_test.py \
    tests/m002_s03_temporal_activity_retry_idempotency_test.py`
  - Result: **6 passed**

## Requirement Changes

- R004: active → validated — proved by Temporal+Postgres integration tests, offline replay determinism (Replayer), post-commit retry idempotency (failpoints), and the operator runbook.
- R005: active → validated — proved by canonical protected transition denial+apply behavior (with stable guard/invariant IDs) and by replay/retry closure proving no duplicated ledger/review side effects.

## Forward Intelligence

### What the next milestone should know
- If you reset Postgres but keep Temporal history, prior executions may keep retrying activities against missing DB rows (dev-noisy but expected). Consider resetting Temporal when doing a clean-room DB reset.
- Offline replay is sensitive to **data converter wiring**: Replayer must use the same converter as the live client.

### What's fragile
- Deterministic ID conventions (`workflow_id`, `correlation_id`, `request_id`, `idempotency_key`) — many tests and the runbook intentionally key DB assertions off these.

### Authoritative diagnostics
- `bash scripts/verify_m002_s03_runbook.sh` — end-to-end truth surface (worker+CLI+DB invariants) without relying on host `psql`.
- Temporal UI workflow history — fast confirmation of signal events + activity retries (including failpoint messages).
- Postgres `case_transition_ledger` for `correlation_id` — most authoritative audit surface.

### What assumptions changed
- “A working workflow run implies replay safety” — replay safety needed explicit offline replay and post-commit retry proofs; both are now first-class verification surfaces.

## Files Created/Modified

- `src/sps/workflows/worker.py` — worker entrypoint registering workflows/activities
- `src/sps/workflows/permit_case/workflow.py` — deterministic orchestration: deny → wait → signal → persist → apply
- `src/sps/workflows/permit_case/activities.py` — authoritative guarded transition + idempotent review persistence (+ test-only post-commit failpoints)
- `src/sps/guards/guard_assertions.py` — YAML-backed guard assertion → invariant lookup for stable denial payloads
- `tests/helpers/temporal_replay.py` — offline history replay helper
- `tests/m002_s03_temporal_replay_determinism_test.py` — determinism proof via Replayer
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py` — exactly-once DB effects under real activity retries
- `scripts/verify_m002_s03_runbook.sh` — operator runbook for the canonical scenario
- `scripts/lib/assert_postgres.sh` — Postgres assertion helpers via docker compose exec
