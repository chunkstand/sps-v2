---
id: T02
parent: S01
milestone: M002-dq2dn9
provides:
  - Operator Temporal CLI (start + ReviewDecision signal) plus an opt-in integration test proving wait→signal→resume with Postgres side-effect assertion
key_files:
  - src/sps/workflows/cli.py
  - src/sps/workflows/temporal.py
  - src/sps/workflows/permit_case/ids.py
  - tests/m002_s01_temporal_permit_case_workflow_test.py
  - README-DEV.md
  - .env.example
key_decisions:
  - Centralized Temporal client connection + Pydantic data converter selection in `sps.workflows.temporal` for consistent CLI/worker/test behavior.
  - Codified stable workflow id convention (`permit-case/<case_id>`) in `permit_case_workflow_id()` to prevent drift.
patterns_established:
  - Integration tests start an in-process Temporal worker against the docker-compose cluster (Temporal/Postgres external; worker internal) to keep the test automated and repeatable.
observability_surfaces:
  - CLI prints `workflow_id` + `run_id` (copy/paste-able); worker/activity logs already emit `workflow_id`, `run_id`, `case_id`, activity name, and `exc_type`.
duration: 1h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Add operator CLI + integration test proving signal wait/resume

**Shipped an operator CLI + opt-in integration test that proves PermitCaseWorkflow runs bootstrap activity, blocks on signal, then resumes and completes.**

## What Happened

- Added `python -m sps.workflows.cli` with:
  - `start --case-id ...` (starts the workflow using stable workflow id `permit-case/<case_id>`, prints `workflow_id` + `run_id`)
  - `signal-review --case-id ... --decision-outcome ... --reviewer-id ... [--notes ...] [--wait]` (sends `ReviewDecision`)
- Added shared helpers:
  - `sps.workflows.temporal` for Settings-driven Temporal client wiring + best-effort Pydantic data converter
  - `permit_case_workflow_id()` helper to enforce the stable id convention across CLI/tests
- Implemented the slice’s integration proof test:
  - starts an in-process worker registered with `PermitCaseWorkflow` + `ensure_permit_case_exists`
  - starts the workflow
  - asserts Postgres has the `permit_cases` row
  - asserts the workflow is still RUNNING and does not complete before signal
  - signals `ReviewDecision` and asserts completion + returned payload
- Updated `README-DEV.md` / `.env.example` with the minimal operator runbook.

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
  - Result: **passed**
- Manual smoke (local docker-compose running): started `python -m sps.workflows.worker`, then:
  - `python -m sps.workflows.cli start --case-id CASE-<ULID>` prints a non-empty `run_id`
  - `python -m sps.workflows.cli signal-review ... --wait` completes and worker logs include `workflow.signal`/`workflow.complete`

## Diagnostics

- Manual demo:
  - `docker compose up -d`
  - `python -m sps.workflows.worker`
  - `python -m sps.workflows.cli start --case-id CASE-<ULID>`
  - `python -m sps.workflows.cli signal-review --case-id CASE-<ULID> --decision-outcome APPROVE --reviewer-id reviewer-1`
- Inspect via Temporal UI: http://localhost:8080 (history should show activity → waiting → signal → completion)
- Grep worker logs for the stable correlation tuple: `workflow_id=<id> run_id=<id> case_id=<id>`

## Deviations

- None.

## Known Issues

- None known. (Integration test remains opt-in and assumes docker-compose Temporal + Postgres are already running.)

## Files Created/Modified

- `src/sps/workflows/cli.py` — operator CLI (start workflow, signal ReviewDecision)
- `src/sps/workflows/temporal.py` — shared Temporal client/data-converter wiring
- `src/sps/workflows/permit_case/ids.py` — stable workflow id convention helper
- `src/sps/workflows/worker.py` — reuse shared Pydantic data converter helper
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — opt-in integration proof (wait→signal→resume + Postgres assertion)
- `README-DEV.md` — local Temporal workflow demo runbook
- `.env.example` — documented opt-in integration flag
