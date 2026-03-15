# S01: Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI

**Goal:** Prove the Phase 2 Temporal substrate is real: a Python worker can run a minimal `PermitCaseWorkflow` against the local docker-compose Temporal cluster, perform one Postgres-backed bootstrap activity, and then deterministically wait for a `ReviewDecision` signal.

**Demo:**
1) `docker compose up -d` (Temporal + Postgres)
2) In one shell: `python -m sps.workflows.worker`
3) In another shell: `python -m sps.workflows.cli start --case-id CASE-<ulid>`
4) Open Temporal UI: http://localhost:8080 → observe workflow in RUNNING state and waiting for signal
5) `python -m sps.workflows.cli signal-review --case-id CASE-<ulid> --decision-outcome APPROVE --reviewer-id reviewer-1`
6) Observe signal event in Temporal UI and workflow completion (or clear “signal received” log line)

This slice is deliberately split into two tasks:
- First we get the deterministic workflow/worker/activity boundary correct (highest replay-risk surface).
- Then we add the operator CLI + automated integration test to close the proof loop and keep it repeatable.

## Must-Haves

- Local Temporal worker entrypoint exists and connects to `localhost:7233` (configurable via `sps.config.Settings`).
- `PermitCaseWorkflow` starts with a stable workflow input contract (`case_id`) and blocks waiting for a `ReviewDecision` signal.
- At least one activity performs a real Postgres write (bootstrap/ensure `permit_cases` row exists) so we prove the worker can safely do I/O only in activities.
- Operator CLI can start the workflow and can send the `ReviewDecision` signal.

## Proof Level

- This slice proves: integration + operational
- Real runtime required: yes (docker-compose Temporal + Postgres)
- Human/UAT required: yes (Temporal UI visibility is part of the demo), but an automated integration test must also pass.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
- Manual demo (runbook-level):
  - `docker compose up -d`
  - `python -m sps.workflows.worker`
  - `python -m sps.workflows.cli start --case-id CASE-<ulid>`
  - `python -m sps.workflows.cli signal-review --case-id CASE-<ulid> --decision-outcome APPROVE --reviewer-id reviewer-1`
  - Temporal UI shows start → activity → wait → signal → completion
- Failure-path check (diagnostic):
  - Start a *misconfigured* worker (bad DB port) in a separate shell:
    - `SPS_DB_PORT=5439 python -m sps.workflows.worker`
  - Start a workflow.
  - Confirm the bootstrap activity fails visibly in Temporal UI (ActivityTaskFailed) and the worker logs include `workflow_id`, `run_id`, `case_id`, and the exception type.
  - Stop the misconfigured worker and restart the correctly configured one.

## Observability / Diagnostics

- Runtime signals: structured log lines from worker/activities including `workflow_id`, `run_id`, `case_id`, activity name, and exception type (no DSNs/secrets).
- Inspection surfaces: Temporal UI (history + activity failures), CLI output (workflow/run IDs), Postgres tables (`permit_cases`).
- Failure visibility: activity exceptions show in Temporal history; worker logs include failure context and a stable correlation tuple (`workflow_id`, `run_id`).
- Redaction constraints: never log DSNs, passwords, S3 keys, or Temporal auth (local dev uses none).

## Integration Closure

- Upstream surfaces consumed: `src/sps/config.py`, `src/sps/db/session.py`, `src/sps/db/models.py`.
- New wiring introduced in this slice: `python -m sps.workflows.worker` worker entrypoint + `python -m sps.workflows.cli` operator CLI.
- What remains before the milestone is truly usable end-to-end: S02 adds guarded transitions + fail-closed denials + signal-driven unblock into authoritative state.

## Tasks

- [x] **T01: Add Temporal workflow + worker + Postgres bootstrap activity** `est:2h`
  - Why: Retire the highest-risk surface first: Temporal determinism boundaries and worker connectivity, with I/O restricted to activities.
  - Files: `pyproject.toml`, `src/sps/config.py`, `src/sps/workflows/worker.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: Add Temporal SDK dependency; add Temporal settings; implement a minimal workflow that runs `ensure_permit_case_exists(case_id)` as an activity then waits on `ReviewDecision` signal via `workflow.wait_condition`.
  - Verify: `python -m sps.workflows.worker` starts cleanly and registers the workflow + activities; starting the workflow (via Temporal client or CLI in T02) shows it reaches a waiting state.
  - Done when: Worker runs against local Temporal and the workflow reliably blocks waiting for a signal after completing the bootstrap activity.

- [x] **T02: Add operator CLI + integration test proving signal wait/resume** `est:2h`
  - Why: Make the proof repeatable and operator-friendly; ensure future slices can start/signals workflows deterministically.
  - Files: `src/sps/workflows/cli.py`, `tests/m002_s01_temporal_permit_case_workflow_test.py`, `.env.example`, `README-DEV.md`
  - Do: Implement CLI subcommands to start workflows and send `ReviewDecision` signal; add an integration test that starts a workflow, asserts it is RUNNING, signals it, and asserts it completes (and that bootstrap wrote the `permit_cases` row).
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
  - Done when: The test passes and the manual demo shows the wait/signal path in Temporal UI.

## Files Likely Touched

- `pyproject.toml`
- `src/sps/config.py`
- `src/sps/workflows/worker.py`
- `src/sps/workflows/cli.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/workflows/permit_case/activities.py`
- `tests/m002_s01_temporal_permit_case_workflow_test.py`
- `README-DEV.md`
- `.env.example`
