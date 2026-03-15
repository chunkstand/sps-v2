---
estimated_steps: 8
estimated_files: 6
---

# T02: Add operator CLI + integration test proving signal wait/resume

**Slice:** S01 — Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI
**Milestone:** M002-dq2dn9

## Description

Close the loop with a repeatable proof harness:
- an operator-facing CLI to start the workflow and to send a `ReviewDecision` signal,
- and an automated integration test that proves the canonical start → wait → signal → completion path while asserting the bootstrap activity wrote to Postgres.

This makes S02/S03 work cheaper: future slices can reuse the same start/signal plumbing to exercise guarded transitions.

## Steps

1. Implement `python -m sps.workflows.cli` with subcommands:
   - `start --case-id ...` (prints `workflow_id` + `run_id`)
   - `signal-review --case-id ... --decision-outcome ... --reviewer-id ...` (sends signal to the stable workflow id)
2. Ensure the CLI uses the same Temporal config defaults as the worker (Settings-driven) and uses a stable workflow ID convention (`permit-case/<case_id>`).
3. Add `tests/m002_s01_temporal_permit_case_workflow_test.py`:
   - start docker-compose Temporal + Postgres externally (test assumes availability when enabled)
   - start workflow via Temporal client
   - assert workflow is RUNNING (waiting) before signal
   - assert `permit_cases.case_id == <case_id>` exists after bootstrap activity
   - send `ReviewDecision` signal
   - assert workflow completes and returns a simple acknowledgment payload
4. Gate the integration test behind an env flag (e.g. `SPS_RUN_TEMPORAL_INTEGRATION=1`) so the default unit test run doesn’t hang/fail in environments without Temporal.
5. Update `.env.example` and `README-DEV.md` with the minimal operator commands for the demo.

## Must-Haves

- [ ] Operator can start a `PermitCaseWorkflow` by `case_id` and gets back `workflow_id/run_id`.
- [ ] Operator can send a `ReviewDecision` signal to a running workflow.
- [ ] Automated test proves workflow blocks waiting for signal, then resumes and completes after signal.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
- Manual demo:
  - `docker compose up -d`
  - `python -m sps.workflows.worker`
  - `python -m sps.workflows.cli start --case-id CASE-<ulid>`
  - `python -m sps.workflows.cli signal-review --case-id CASE-<ulid> --decision-outcome APPROVE --reviewer-id reviewer-1`

## Observability Impact

- Signals added/changed: CLI prints stable `workflow_id` and `run_id` (copy/pasteable); worker logs show signal receipt.
- How a future agent inspects this: Temporal UI history for the workflow id printed by CLI; pytest output for integration failure.
- Failure state exposed: signal failures show as CLI exceptions; activity failures show in Temporal history.

## Inputs

- `src/sps/workflows/worker.py` — task queue + workflow registration that CLI must target
- `src/sps/workflows/permit_case/contracts.py` — signal payload model to serialize in CLI/test

## Expected Output

- `src/sps/workflows/cli.py` — operator CLI for start + signal
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — repeatable proof of wait/signal path + DB bootstrap assertion
- `README-DEV.md` / `.env.example` — minimal runbook for starting worker and exercising the workflow
