# S03: Replay/idempotency closure + final end-to-end integration proof — UAT

**Milestone:** M002-dq2dn9
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed
- Why this mode is sufficient: This slice’s “user-facing” outcome is operational correctness (Temporal replay determinism + DB idempotency under retry) and is best validated by running the real docker-compose stack plus the shipped runbook and integration tests.

## Preconditions

- Docker is running.
- Python virtualenv exists at `./.venv` and dependencies are installed.
- Required ports are free (Temporal `7233`, Temporal UI `8233`, Postgres `5432` as configured in compose).
- Repo root is the working directory.

## Smoke Test

Run:

1. `bash scripts/verify_m002_s03_runbook.sh`
2. **Expected:** Script exits `0` and prints `runbook: ok` plus a Postgres summary showing:
   - `APPROVAL_GATE_DENIED|1`
   - `CASE_STATE_CHANGED|1`
   - exactly one `review_decisions` row for the printed `review/<workflow_id>/<run_id>` key.

## Test Cases

### 1. Canonical end-to-end scenario (runbook)

1. Run `bash scripts/verify_m002_s03_runbook.sh`.
2. Observe the printed `workflow_id`, `run_id`, `case_id`, and `correlation_id`.
3. **Expected:**
   - The workflow is started, then a `ReviewDecision` signal is sent, and the workflow completes.
   - Postgres assertions pass:
     - `case_transition_ledger` has exactly 2 rows for the correlation: one denial and one applied transition.
     - `review_decisions` has exactly 1 row for the idempotency key `review/{workflow_id}/{run_id}`.

### 2. Offline replay determinism (captured history → Replayer)

1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`.
2. **Expected:**
   - Test passes (`1 passed`).
   - No replay/non-determinism exceptions occur.
   - Durable DB outcomes are asserted for the run correlation (state advanced and ledger/review rows match expectations).

### 3. Post-commit activity retry idempotency (failpoint-forced retry)

1. Run `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`.
2. **Expected:**
   - Test passes (`1 passed`).
   - The test forces at least one retry after a committed write (via env-gated failpoints) and still observes:
     - exactly 2 ledger rows for the correlation,
     - exactly 1 review decision row for the idempotency key,
     - and Temporal history contains the failpoint failure message `FAILPOINT_FIRED key=...`.

## Edge Cases

### Re-run the runbook on an already-running stack

1. Run `bash scripts/verify_m002_s03_runbook.sh` twice in a row.
2. **Expected:** Both runs succeed; each run uses a unique `case_id` and produces exactly one denial + one applied ledger row for its own correlation.

### Temporal UI inspection (optional human check)

1. Open `http://localhost:8233`.
2. Search for the `workflow_id` printed by the runbook.
3. **Expected:** The history shows a signal event for `ReviewDecision` and activity attempts including the initial denial then the successful state change.

## Failure Signals

- Any `Replayer` exception (non-determinism) in `tests/m002_s03_temporal_replay_determinism_test.py`.
- `case_transition_ledger` row counts not equal to 2 for a correlation (duplicate side effects under retry/replay).
- More than one `review_decisions` row for the same `idempotency_key`.
- Runbook fails with a Postgres assertion label or cannot connect to Temporal/Postgres.

## Requirements Proved By This UAT

- R004 — Replay determinism + idempotent/exactly-once DB effects are proven via offline Replayer test, post-commit retry test, and the runbook.
- R005 — Protected transition denial + unblocking behavior remains stable under retries/replays (no duplicated ledger/review effects).

## Not Proven By This UAT

- Large-scale concurrency / multi-worker contention behavior.
- Long-lived workflow upgrades/versioning strategies beyond the current determinism proof.

## Notes for Tester

- These tests intentionally hit real docker-compose services; first run may be slower due to image pull/migrations.
- If the runbook fails, it prints the worker log path and tails the last lines automatically for diagnosis.
