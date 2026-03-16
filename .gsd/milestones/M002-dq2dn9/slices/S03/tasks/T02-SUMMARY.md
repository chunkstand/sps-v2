---
id: T02
parent: S03
milestone: M002-dq2dn9
provides:
  - Env-gated post-commit failpoints + Temporal integration test proving exactly-once Postgres effects under real activity retry
key_files:
  - src/sps/failpoints.py
  - src/sps/workflows/permit_case/activities.py
  - tests/m002_s03_temporal_activity_retry_idempotency_test.py
key_decisions:
  - Use env-gated, key-addressable “fail once after commit” failpoints to force real Temporal activity retries without introducing production runtime risk.
patterns_established:
  - Post-commit failpoint hook in activities (after SQLAlchemy transaction commit) + integration test asserts retry attempts and exactly-once DB invariants
observability_surfaces:
  - Structured activity log line: "activity.failpoint ... failpoint_key=..." (includes workflow_id/run_id/request_id/idempotency_key)
  - Temporal history contains the failpoint exception message "FAILPOINT_FIRED key=<...>" on the failed attempt
  - Postgres inspection: query `case_transition_ledger` by `correlation_id`, `review_decisions` by `idempotency_key`
duration: 1h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Prove DB idempotency under real activity retry (post-commit failpoint)

**Shipped env-gated post-commit failpoints wired into the authoritative activities, plus an integration test that forces real Temporal retries and proves Postgres effects remain exactly-once.**

## What Happened

- Added `src/sps/failpoints.py`: a minimal, opt-in failpoint facility gated behind `SPS_ENABLE_TEST_FAILPOINTS=1` and keyed via `SPS_TEST_FAILPOINT_KEYS`.
  - Fires at most once per process per key.
  - Tracks per-key “seen” counts (when enabled) so tests can assert the post-commit point was reached multiple times (i.e. a retry happened).
- Wired failpoints *after commit* in:
  - `apply_state_transition(...)` via key `apply_state_transition.after_commit/<request_id>`
  - `persist_review_decision(...)` via key `persist_review_decision.after_commit/<idempotency_key>`
- Added `tests/m002_s03_temporal_activity_retry_idempotency_test.py`:
  - Starts a real workflow run, enables the two failpoints for that run’s deterministic IDs, and runs an in-process worker.
  - Proves “commit then crash then retry” by waiting for each failpoint to fire and immediately asserting the committed DB row is visible.
  - Proves retries occurred (failpoint seen counts ≥ 2) and that Temporal history contains the failpoint exception messages.
  - Asserts exactly-once DB effects: no duplicate ledger rows per `correlation_id` and no duplicate review rows per `idempotency_key`.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`
- Slice-level checks run for this task:
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
  - `bash scripts/verify_m002_s03_runbook.sh` — not run (script is part of T03; does not exist yet)

## Diagnostics

- If you need to confirm retries:
  - Temporal history for the workflow run should contain `FAILPOINT_FIRED key=<...>` failures.
- If you need to confirm DB idempotency:
  - `case_transition_ledger.correlation_id == f"{workflow_id}:{run_id}"` should have exactly 2 rows (denied + applied).
  - `review_decisions.idempotency_key == f"review/{workflow_id}/{run_id}"` should have exactly 1 row.
- Worker logs:
  - Look for `activity.failpoint name=apply_state_transition ... failpoint_key=...` and `activity.failpoint name=persist_review_decision ... failpoint_key=...`.

## Deviations

- None.

## Known Issues

- None.

## Files Created/Modified

- `src/sps/failpoints.py` — env-gated “fail once” failpoint helper + test-visible counters.
- `src/sps/workflows/permit_case/activities.py` — post-commit failpoint hooks + structured failpoint log lines.
- `tests/m002_s03_temporal_activity_retry_idempotency_test.py` — integration test proving idempotency under real activity retry.
