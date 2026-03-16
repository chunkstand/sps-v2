# S03: Replay/idempotency closure + final end-to-end integration proof

**Goal:** Close the remaining Phase 2 risk: prove the existing Temporal+Postgres PermitCaseWorkflow is replay-deterministic and that activity retries / worker restarts do not duplicate authoritative Postgres side effects (transition ledger + review decision writes).

**Demo:** With local docker-compose Temporal+Postgres:
- The canonical workflow run completes via the existing deny → wait → signal → persist → apply path.
- The captured workflow history replays via Temporal’s `Replayer` with no non-determinism.
- A forced post-commit activity retry and/or worker restart does not increase ledger row counts (idempotency holds at the DB boundary).

**Requirement coverage:**
- Supports **R004 (Active)** by providing replay determinism + retry/idempotency proofs against real Temporal+Postgres.
- Strengthens **R005 (Validated)** by proving denial behavior remains stable under retries/replays (no duplicated ledger side effects).

## Must-Haves

- Replay determinism is proven by replaying a real, captured workflow history with `temporalio.worker.Replayer`.
- Activity retry is forced *after* a committed DB side effect (test-only failpoint) and verified to not duplicate `case_transition_ledger` or `review_decisions` rows.
- A runbook-level “start stack → run canonical scenario” script exists and asserts the expected ledger outcomes (operational proof path).

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes
- Human/UAT required: no

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`
- `bash scripts/verify_m002_s03_runbook.sh`

## Observability / Diagnostics

- Runtime signals: structured worker logs with `(workflow_id, run_id, case_id, request_id, event_type)`; Temporal history events; Postgres ledger rows.
- Inspection surfaces: Temporal UI (`http://localhost:8233`), `case_transition_ledger` and `review_decisions` tables, CLI (`python -m sps.workflows.cli`).
- Failure visibility: replay failures surface as `Replayer` exceptions; retries visible in Temporal history; idempotency failures visible as unexpected row counts per `correlation_id`.
- Redaction constraints: never log DB URLs or credentials; never log secrets from env.

## Integration Closure

- Upstream surfaces consumed: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/worker.py`, `src/sps/workflows/cli.py`.
- New wiring introduced in this slice: test-only failpoint hook(s) inside activities (guarded behind env), replay harness in integration tests, runbook verification script.
- What remains before the milestone is truly usable end-to-end: nothing (this slice is the closure proof).

## Tasks

- [x] **T01: Add offline replay determinism integration test (Replayer + captured history)** `est:1h`
  - Why: Closes the determinism/replay risk by proving the workflow code is compatible with real event histories.
  - Files: `tests/m002_s03_temporal_replay_determinism_test.py`, `tests/helpers/temporal_replay.py`
  - Do: Run the canonical workflow to completion, fetch history via `WorkflowHandle.fetch_history()`, and replay it with `temporalio.worker.Replayer(workflows=[PermitCaseWorkflow])`.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
  - Done when: replay succeeds without non-determinism and the test asserts the workflow completed + expected ledger outcomes exist.

- [x] **T02: Prove DB idempotency under real activity retry (post-commit failpoint)** `est:1h`
  - Why: Replayer covers determinism but not “activity re-execution after a committed side effect”; this proves the DB boundary is truly exactly-once-effect.
  - Files: `src/sps/workflows/permit_case/activities.py`, `src/sps/failpoints.py`, `tests/m002_s03_temporal_activity_retry_idempotency_test.py`
  - Do: Add a test-only failpoint that raises *after* commit for a targeted `request_id`/`idempotency_key`, ensure the workflow activity has a retry policy (or relies on default retries), and assert ledger/review rows remain exactly-once.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`
  - Done when: Temporal shows a retry attempt but Postgres row counts for the correlation are unchanged and the workflow still reaches the expected state.

- [x] **T03: Add runbook verification script for canonical scenario (stack → worker → CLI → DB asserts)** `est:45m`
  - Why: Provides an operator-proof path outside pytest and makes regressions obvious during local dev.
  - Files: `scripts/verify_m002_s03_runbook.sh`, `scripts/lib/assert_postgres.sh`
  - Do: Script: start docker compose (if not running), start a worker in background, run CLI to start workflow + send signal, then query Postgres to assert exactly 2 ledger rows (denied+applied) and 1 review row for the correlation; ensure cleanup on exit.
  - Verify: `bash scripts/verify_m002_s03_runbook.sh`
  - Done when: script exits 0 on a clean stack and prints the workflow id/run id + a minimal DB summary that matches expectations.

## Files Likely Touched

- `tests/m002_s03_temporal_replay_determinism_test.py`
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py`
- `tests/helpers/temporal_replay.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/failpoints.py`
- `scripts/verify_m002_s03_runbook.sh`
- `scripts/lib/assert_postgres.sh`
