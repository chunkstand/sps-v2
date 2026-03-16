---
estimated_steps: 6
estimated_files: 2
---

# T03: Add runbook verification script for canonical scenario (stack → worker → CLI → DB asserts)

**Slice:** S03 — Replay/idempotency closure + final end-to-end integration proof
**Milestone:** M002-dq2dn9

## Description

Add a runnable, operator-style verification script that exercises the canonical scenario using the *real entrypoints* (docker compose + worker module + CLI), then asserts the expected Postgres outcomes. This is the end-to-end “runbook proof” that complements pytest.

## Steps

1. Create `scripts/lib/assert_postgres.sh` helpers to run a small SQL query and assert row counts/expected fields (with safe error messages and no credential echo).
2. Create `scripts/verify_m002_s03_runbook.sh` that:
   - ensures docker compose services are up (Temporal + Postgres),
   - starts `python -m sps.workflows.worker` in the background and waits for readiness,
   - runs `python -m sps.workflows.cli permit-case start ...` then `... signal-review-decision ...`,
   - waits for completion (via CLI or Temporal query),
   - asserts via SQL that the correlation has exactly 2 ledger rows (denied + applied) and 1 review decision row,
   - cleans up the worker process on exit.
3. Document expected environment variables at the top of the script (use existing Settings defaults; never print secrets).

## Must-Haves

- [ ] Script uses the real worker + CLI entrypoints (no in-process pytest worker).
- [ ] Script asserts durable Postgres outcomes (ledger + review decision rows) and exits non-zero if they’re wrong.
- [ ] Script cleans up background processes on failure or Ctrl-C.

## Verification

- `bash scripts/verify_m002_s03_runbook.sh`

## Observability Impact

- Signals added/changed: the script prints workflow_id/run_id/case_id and a minimal DB summary (counts + key IDs) to make failures diagnosable.
- How a future agent inspects this: rerun the script; open Temporal UI for the printed workflow_id/run_id; run the printed SQL snippets manually if needed.
- Failure state exposed: explicit failing SQL assertion + correlation tuple printed.

## Inputs

- `src/sps/workflows/worker.py` — worker entrypoint.
- `src/sps/workflows/cli.py` — operator CLI.

## Expected Output

- `scripts/verify_m002_s03_runbook.sh` — one-command end-to-end integration proof for Phase 2.
- `scripts/lib/assert_postgres.sh` — reusable SQL assertion helpers for future runbook checks.
