---
estimated_steps: 6
estimated_files: 3
---

# T01: Add offline replay determinism integration test (Replayer + captured history)

**Slice:** S03 — Replay/idempotency closure + final end-to-end integration proof
**Milestone:** M002-dq2dn9

## Description

Add an integration test that runs the canonical `PermitCaseWorkflow` against the real docker-compose Temporal+Postgres stack, fetches the completed workflow history, and replays it offline using `temporalio.worker.Replayer`. This is the determinism closure proof: if workflow code becomes non-deterministic, replay will fail.

## Steps

1. Create `tests/helpers/temporal_replay.py` with a small helper that takes a `WorkflowHistory` (or JSON) and runs `Replayer(workflows=[PermitCaseWorkflow])` against it.
2. Add `tests/m002_s03_temporal_replay_determinism_test.py` that:
   - starts the canonical workflow to completion (reuse the S02 harness pattern),
   - fetches history via `await handle.fetch_history()`,
   - replays the history with the helper, and
   - asserts the workflow result and expected Postgres ledger outcomes exist for the `correlation_id`.
3. Ensure the test uses unique workflow IDs (same convention as S02) to avoid collisions with prior Temporal state.

## Must-Haves

- [ ] The test fetches history from a *real* workflow run (not a fixture-only history file).
- [ ] Replay is performed with `temporalio.worker.Replayer` and fails the test on any non-determinism exception.
- [ ] The test asserts at least one durable Postgres signal (e.g., expected ledger rows for the run) in addition to “workflow completed”.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`

## Observability Impact

- Signals added/changed: deterministic replay failure will surface as a `Replayer` exception pointing at the first diverging event.
- How a future agent inspects this: Temporal UI history for the run + `pytest -q ...` stack trace + Postgres ledger query by `correlation_id`.
- Failure state exposed: divergence event index/type in the replayer error; workflow_id/run_id printed in test logs on failure.

## Inputs

- `tests/m002_s02_temporal_guarded_transition_workflow_test.py` — existing canonical integration harness pattern (client + in-process worker).
- `src/sps/workflows/permit_case/workflow.py` — workflow under replay.

## Expected Output

- `tests/m002_s03_temporal_replay_determinism_test.py` — passes when replay is deterministic; fails on divergence.
- `tests/helpers/temporal_replay.py` — reusable replay helper for future workflows/slices.
