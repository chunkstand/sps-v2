---
id: T01
parent: S03
milestone: M002-dq2dn9
provides:
  - Offline replay determinism integration test for PermitCaseWorkflow using real captured Temporal history
key_files:
  - tests/m002_s03_temporal_replay_determinism_test.py
  - tests/helpers/temporal_replay.py
  - tests/__init__.py
key_decisions:
  - Replayer is constructed with the same Pydantic-aware data converter as the live Temporal client (`try_get_pydantic_data_converter`) to ensure payload hydration matches the recorded history.
patterns_established:
  - Integration harness pattern: run workflow to completion on docker-compose Temporal+Postgres → fetch history → offline replay → assert durable DB outcomes.
observability_surfaces:
  - Replay failures surface as `Replayer` exceptions; test re-raises with workflow_id/run_id context.
  - Postgres inspection by `correlation_id` in `case_transition_ledger` and deterministic review decision ID.
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add offline replay determinism integration test (Replayer + captured history)

**Shipped an opt-in integration test that replays a real PermitCaseWorkflow run history offline with Temporal’s `Replayer`, asserting both determinism and durable Postgres side effects.**

## What Happened

- Added a small replay helper (`tests/helpers/temporal_replay.py`) that accepts a `WorkflowHistory` (or exported JSON) and replays it offline with `temporalio.worker.Replayer`.
- Implemented `tests/m002_s03_temporal_replay_determinism_test.py`:
  - runs the canonical deny → wait → signal → persist → apply path against the real docker-compose Temporal+Postgres stack,
  - fetches the completed workflow history via `await handle.fetch_history()`,
  - replays the history offline (fails on any non-determinism), and
  - asserts durable DB outcomes for the run (`PermitCase.case_state`, `case_transition_ledger` rows by `correlation_id`, and the deterministic `review_decisions.decision_id`).
- Made `tests/` a package (`tests/__init__.py`) so the shared helper can be imported reliably during pytest collection.

## Verification

Passed:
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`

Attempted (per slice verification list) but not yet applicable in this task:
- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py` (file not present yet)
- `bash scripts/verify_m002_s03_runbook.sh` (script not present yet)

## Diagnostics

- If replay fails, the test error includes `workflow_id` and `run_id`; the underlying `Replayer` exception points at the first diverging history event.
- Postgres inspection:
  - `case_transition_ledger.correlation_id == f"{workflow_id}:{run_id}"`
  - `review_decisions.decision_id == f"review/{workflow_id}/{run_id}"`

## Deviations

- Added `tests/__init__.py` (not listed in the original task files) to support importing `tests/helpers/temporal_replay.py`.
- `Replayer.replay_workflow` is async in the installed Temporal SDK, so the replay helper is implemented as `async def` and awaited.

## Known Issues

- None in the determinism test itself.
- Slice-level verification items for T02/T03 are still missing and will fail until those tasks land.

## Files Created/Modified

- `tests/helpers/temporal_replay.py` — async helper to replay captured workflow histories offline using `Replayer` (with live data converter wiring).
- `tests/m002_s03_temporal_replay_determinism_test.py` — integration test: run workflow → fetch history → offline replay → assert Postgres outcomes.
- `tests/helpers/__init__.py` — helper package marker.
- `tests/__init__.py` — makes `tests` importable for shared helper usage.
- `.gsd/DECISIONS.md` — appended decision about matching data converter wiring for offline replay.
