# S01: Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI — UAT

**Milestone:** M002-dq2dn9
**Written:** 2026-03-15

## UAT Type

- UAT mode: mixed
- Why this mode is sufficient: This slice is primarily runtime substrate. We validate with an artifact-driven pytest integration proof, plus a human/operational check in Temporal UI (workflow history shows activity → wait → signal → completion) and a deliberate misconfiguration scenario proving failures are visible and diagnosable.

## Preconditions

1. Local infra is running:
   - `docker compose up -d`
   - Temporal UI reachable at http://localhost:8080
2. Python venv is installed:
   - `./.venv/bin/python -m pip install -e "[dev]"`
3. You run commands using `./.venv/bin/python` (system `python` may not exist on PATH).
4. Default settings are acceptable (unless overridden):
   - Temporal: `localhost:7233`, namespace `default`, task queue `sps-permit-case`
   - Postgres: from `sps.config.Settings` defaults / `.env` (docker-compose local)

## Smoke Test

Run the automated integration proof:

1. `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
2. **Expected:** test passes.

## Test Cases

### 1. Worker runs and polls the task queue

1. Start the worker: `./.venv/bin/python -m sps.workflows.worker`
2. **Expected:** log lines include:
   - `temporal.worker.start ...`
   - `temporal.worker.polling ... workflows=['PermitCaseWorkflow'] activities=['ensure_permit_case_exists']`

### 2. Start workflow and confirm it waits for `ReviewDecision` (Temporal UI)

1. In a second shell: `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-<unique>`
2. **Expected:** CLI prints non-empty `workflow_id=permit-case/CASE-<unique>` and `run_id=<uuid>`.
3. Open Temporal UI (http://localhost:8080) → search by workflow id.
4. **Expected:** workflow is RUNNING; history shows:
   - `ensure_permit_case_exists` activity completed
   - workflow is waiting (no completion event yet)

### 3. Send `ReviewDecision` signal and confirm workflow completes

1. `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-<unique> --decision-outcome APPROVE --reviewer-id reviewer-1 --wait`
2. **Expected:**
   - CLI prints it signaled `signal=ReviewDecision`
   - CLI prints the returned payload JSON (decision_outcome/reviewer_id)
3. In Temporal UI, open the workflow history.
4. **Expected:** history includes a `ReviewDecision` signal event, followed by workflow completion.

### 4. Postgres bootstrap side-effect exists (`permit_cases` row)

1. Connect to Postgres (docker-compose):
   - `docker exec -it sps-v2-postgres-1 psql -U sps -d sps`
2. Query for the case created in test case #2:
   - `select case_id from permit_cases where case_id = 'CASE-<unique>';`
3. **Expected:** one row exists.

## Edge Cases

### Duplicate signal is ignored after the first decision

1. Start a workflow for `CASE-<unique2>` and send an APPROVE signal.
2. Send a second signal (e.g. DENY) to the same workflow id:
   - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-<unique2> --decision-outcome DENY --reviewer-id reviewer-2 --wait`
3. **Expected:** workflow result remains the first decision (signals after the first decision are ignored by workflow logic).

### Starting the same workflow id twice

1. Start a workflow: `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-<unique3>`
2. Run the same start again with the same case id.
3. **Expected:** Temporal rejects the second start (workflow-id collision) and CLI exits non-zero with an error (e.g. already started).

### Signaling a non-existent workflow

1. `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-DOES-NOT-EXIST --decision-outcome APPROVE --reviewer-id reviewer-1 --wait`
2. **Expected:** CLI exits non-zero and prints a “not found” / handle error.

## Failure Signals

- Worker logs show `activity.error` (or Temporal UI shows ActivityTaskFailed) without the correlation tuple (`workflow_id`, `run_id`, `case_id`, `exc_type`).
- Workflow completes before a signal is sent (should remain RUNNING/waiting).
- CLI output is missing `workflow_id` or `run_id`.
- Postgres does not contain a `permit_cases` row after the bootstrap activity.

## Requirements Proved By This UAT

- R004 — Proves the Temporal harness can run `PermitCaseWorkflow` end-to-end (activity side-effect + deterministic wait + signal + completion) against local docker-compose Temporal/Postgres.

## Not Proven By This UAT

- Replay/idempotency closure (no history replay test; no transition-ledger idempotency yet).
- R005 protected transition guard denials/audit ledger behavior (lands in S02).

## Notes for Tester

- Always use unique `case_id` values unless you explicitly want to test workflow-id collision behavior.
- If you want to see failure visibility, run the diagnostic scenario:
  1. Stop the correct worker
  2. Start misconfigured worker: `SPS_DB_PORT=5439 ./.venv/bin/python -m sps.workflows.worker`
  3. Start a workflow and observe `activity.error ... exc_type=OperationalError` in worker logs and ActivityTaskFailed events in Temporal UI
  4. Restart the correct worker and re-signal to complete.
