---
id: S01
parent: M002-dq2dn9
milestone: M002-dq2dn9
provides:
  - Temporal Python worker entrypoint (`python -m sps.workflows.worker`) wired via `sps.config.Settings`
  - Minimal deterministic `PermitCaseWorkflow` (Postgres bootstrap activity → wait on `ReviewDecision` signal → complete)
  - Postgres-backed bootstrap activity `ensure_permit_case_exists(case_id)` proving the I/O-in-activities boundary
  - Operator CLI (`python -m sps.workflows.cli`) to start workflows and send `ReviewDecision` signals
  - Opt-in pytest integration proof that starts a workflow, asserts Postgres side-effect, signals, and asserts completion
requires: []
affects:
  - S02
  - S03
key_files:
  - pyproject.toml
  - src/sps/config.py
  - src/sps/workflows/worker.py
  - src/sps/workflows/cli.py
  - src/sps/workflows/temporal.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/ids.py
  - tests/m002_s01_temporal_permit_case_workflow_test.py
  - docker-compose.yml
  - README-DEV.md
  - .env.example
key_decisions:
  - "Keep workflow deterministic: no DB/network access in workflow code; only via activities"
  - "Centralize Temporal client wiring + payload conversion selection in `sps.workflows.temporal` (worker/CLI/tests consistent)"
  - "Workflow ID convention is `permit-case/<case_id>` (operator-friendly and stable across tools)"
  - "Pre-import `pydantic_core` in workflow contracts to avoid Temporal sandbox late-import warnings"
patterns_established:
  - "Workflow imports activities via `workflow.unsafe.imports_passed_through()`"
  - "Integration tests run an in-process worker against docker-compose Temporal/Postgres for repeatable automation"
observability_surfaces:
  - Temporal UI (http://localhost:8080): workflow history includes activity execution + signal event
  - Worker log correlation tuple: `workflow_id`, `run_id`, `case_id`, `activity name`, `exc_type`
  - CLI prints `workflow_id` + `run_id`
  - Integration proof: `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py`
drill_down_paths:
  - .gsd/milestones/M002-dq2dn9/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002-dq2dn9/slices/S01/tasks/T02-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-15T22:31:07Z
---

# S01: Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI

**Shipped a real Temporal + Postgres runtime harness: a worker can bootstrap a PermitCase via an activity, deterministically wait for a `ReviewDecision` signal, then resume and complete — with an operator CLI and an automated integration proof.**

## What Happened

- Added the Temporal Python SDK runtime dependency and Settings-backed Temporal configuration (address/namespace/task queue) so worker/CLI/tests share the same wiring.
- Implemented a minimal deterministic workflow (`PermitCaseWorkflow`) whose only side-effects occur inside activities:
  - runs `ensure_permit_case_exists(case_id)` as a Postgres-backed activity
  - waits on `workflow.wait_condition(...)` until a `ReviewDecision` signal arrives
  - completes returning the received `ReviewDecision` payload
- Implemented the Postgres bootstrap activity (`ensure_permit_case_exists`) that insert-if-missing creates a `permit_cases` row.
- Implemented an operator CLI that can start the workflow and send the `ReviewDecision` signal (optionally waiting for workflow completion).
- Added an opt-in integration test that proves the end-to-end path (start → activity side-effect → still running → signal → complete).
- Hardened Temporal workflow determinism surface by pre-importing `pydantic_core` in workflow contracts to avoid Temporal workflow sandbox late-import warnings.

## Verification

- Infra:
  - `docker compose up -d` (Temporal + Temporal UI + Postgres)
- Automated integration proof:
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py` → pass
- Manual / operational smoke (runtime surfaces):
  - `./.venv/bin/python -m sps.workflows.worker`
  - `./.venv/bin/python -m sps.workflows.cli start --case-id CASE-...`
  - `./.venv/bin/python -m sps.workflows.cli signal-review --case-id CASE-... --decision-outcome APPROVE --reviewer-id reviewer-1 --wait`
- Failure-path diagnostic (plan-required):
  - `SPS_DB_PORT=5439 ./.venv/bin/python -m sps.workflows.worker` then start a workflow
  - Confirm worker logs emit `activity.error ... exc_type=OperationalError` with `workflow_id/run_id/case_id`
  - Restart correctly configured worker and confirm the workflow recovers and completes after signal

## Requirements Advanced

- R004 — Proved the minimal worker/workflow substrate is real (Temporal + Postgres) and the representative wait→signal→resume path is automated by an integration test.

## Requirements Validated

- (none) — Replay/idempotency closure is deferred to S03, and protected-transition guard behavior is deferred to S02.

## New Requirements Surfaced

- (none)

## Requirements Invalidated or Re-scoped

- None.

## Deviations

- Updated `docker-compose.yml` Temporal auto-setup Postgres environment to boot cleanly in local dev.
- Added `pydantic_core` eager import in workflow contracts after observing Temporal workflow sandbox warnings about late imports.

## Known Limitations

- No guarded state-transition activity yet (protected transitions + structured denials land in S02).
- Replay/idempotency proofs (stable ledger counts under replay/retry) are not in place yet (S03).

## Follow-ups

- S02: implement guarded state transitions + fail-closed denials + signal-driven unblock (authoritative Postgres mutation path).
- S03: prove replay/idempotency (ledger idempotency keys + workflow history replay test).

## Files Created/Modified

- `pyproject.toml` — added Temporal Python SDK dependency.
- `src/sps/config.py` — Settings fields for Temporal address/namespace/task queue (with local defaults).
- `src/sps/workflows/worker.py` — worker entrypoint registering workflow + activities.
- `src/sps/workflows/permit_case/contracts.py` — workflow input + signal payload Pydantic models (+ `pydantic_core` eager import).
- `src/sps/workflows/permit_case/workflow.py` — deterministic workflow (activity + `wait_condition` + signal handler).
- `src/sps/workflows/permit_case/activities.py` — Postgres bootstrap activity.
- `src/sps/workflows/permit_case/ids.py` — stable workflow id helper.
- `src/sps/workflows/temporal.py` — shared client wiring + optional Pydantic data converter selection.
- `src/sps/workflows/cli.py` — operator CLI (start + signal).
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — opt-in integration proof.
- `docker-compose.yml` — local Temporal auto-setup DB env fixes.
- `README-DEV.md`, `.env.example` — operator runbook + env hints.

## Forward Intelligence

### What the next slice should know

- Use `./.venv/bin/python` (not `python`) in runbooks/scripts; system `python` may not be on PATH in this environment.
- Don’t run `python -m sps.workflows.worker` concurrently with the in-process worker used by the integration test unless you intentionally want multiple workers polling the same task queue.

### What's fragile

- Temporal workflow sandbox import hygiene: warnings about late imports are an early smell for determinism issues. If they reappear, fix by eager imports in workflow modules/contracts.

### Authoritative diagnostics

- Temporal UI history + worker logs (`activity.start|activity.ok|activity.error` and `workflow.start|workflow.waiting|workflow.signal|workflow.complete`) are the fastest truth signals for runtime behavior.

### What assumptions changed

- "Pydantic contracts won’t trigger workflow sandbox warnings" — they can; eager-importing `pydantic_core` avoids the late-import warnings and keeps determinism hazards lower.
