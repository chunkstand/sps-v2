---
id: T03
parent: S03
milestone: M002-dq2dn9
provides:
  - One-command runbook verification (docker compose → worker → CLI → Postgres asserts) for the canonical PermitCaseWorkflow scenario
key_files:
  - scripts/verify_m002_s03_runbook.sh
  - scripts/lib/assert_postgres.sh
key_decisions:
  - Run Postgres assertions via `docker compose exec ... psql` (in-container) to avoid requiring host `psql` and to avoid printing DSNs/passwords.
patterns_established:
  - Runbook script pattern: idempotent `docker compose up -d` + background worker with trap-based cleanup + DB invariant assertions keyed by `(workflow_id, run_id)` correlation.
observability_surfaces:
  - Script prints `workflow_id`, `run_id`, `case_id`, and a minimal DB summary; on failure prints a clear assertion label + tails the worker log.
duration: 45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Add runbook verification script for canonical scenario (stack → worker → CLI → DB asserts)

**Shipped an operator-style runbook script that starts the local Temporal/Postgres stack, runs the canonical PermitCaseWorkflow via the real worker + CLI entrypoints, and asserts the durable Postgres outcomes (ledger + review decision) for the workflow correlation.**

## What Happened

- Added `scripts/lib/assert_postgres.sh`, a small bash helper library to run SQL inside the docker-compose Postgres container and provide scalar/count assertions with safe, non-secret error messages.
- Added `scripts/verify_m002_s03_runbook.sh` which:
  - brings up the required docker compose services (Postgres + Temporal + Temporal UI),
  - applies Alembic migrations,
  - starts `python -m sps.workflows.worker` in the background and waits for readiness,
  - runs `python -m sps.workflows.cli start` and `python -m sps.workflows.cli signal-review --wait`,
  - asserts that for `correlation_id = "{workflow_id}:{run_id}"`:
    - `case_transition_ledger` has exactly 2 rows total (1 `APPROVAL_GATE_DENIED`, 1 `CASE_STATE_CHANGED`),
    - `review_decisions` has exactly 1 row for `idempotency_key = "review/{workflow_id}/{run_id}"`,
  - traps exit/INT/TERM and cleans up the worker process; on failure it tails the worker log for quick diagnosis.

## Verification

- `bash scripts/verify_m002_s03_runbook.sh`
- Slice-level checks re-run:
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_replay_determinism_test.py`
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s03_temporal_activity_retry_idempotency_test.py`

## Diagnostics

- Rerun: `bash scripts/verify_m002_s03_runbook.sh`
- On failure:
  - the script prints the correlation tuple (`workflow_id`, `run_id`, `case_id`)
  - Postgres assertion failures include a stable label (grep-able)
  - the worker log tail is printed (log path is written when the worker starts)
  - use Temporal UI to inspect the printed `workflow_id` / `run_id`

## Deviations

- The task plan referenced older CLI subcommands (`permit-case start` / `signal-review-decision`); the runbook uses the current CLI interface (`start` / `signal-review`).

## Known Issues

- None.

## Files Created/Modified

- `scripts/lib/assert_postgres.sh` — reusable Postgres assertion helpers (runs psql in docker-compose Postgres container, fails fast on mismatches).
- `scripts/verify_m002_s03_runbook.sh` — end-to-end runbook verification for M002/S03 canonical scenario (stack → worker → CLI → DB asserts).
