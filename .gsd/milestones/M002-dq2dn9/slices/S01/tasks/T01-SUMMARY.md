---
id: T01
parent: S01
milestone: M002-dq2dn9
provides:
  - Temporal worker entrypoint (`python -m sps.workflows.worker`) with Settings-backed config defaults
  - Deterministic `PermitCaseWorkflow` that bootstraps a case via Postgres activity then waits on `ReviewDecision` signal
  - Postgres bootstrap activity `ensure_permit_case_exists(case_id)` proving the I/O boundary
key_files:
  - pyproject.toml
  - src/sps/config.py
  - src/sps/workflows/worker.py
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/contracts.py
key_decisions:
  - "Keep workflow deterministic: no DB/network access in workflow code; only via activities"
  - "Use Temporal Pydantic data converter when available to keep workflow contracts as Pydantic models"
patterns_established:
  - "Workflow imports activity code via workflow.unsafe.imports_passed_through()"
  - "Synchronous DB activities run via Worker(activity_executor=ThreadPoolExecutor(...))"
observability_surfaces:
  - Temporal UI workflow history + activity failures
  - Worker/activity log lines with workflow_id/run_id/case_id + exception type
duration: 55m
verification_result: passed
completed_at: 2026-03-15T22:11:30Z
blocker_discovered: false
---

# T01: Add Temporal workflow + worker + Postgres bootstrap activity

**Shipped a working Temporal Python worker + deterministic PermitCaseWorkflow that runs a Postgres bootstrap activity then blocks waiting for a ReviewDecision signal.**

## What Happened

- Added Temporal Python SDK dependency and Settings fields with safe local defaults (address/namespace/task queue).
- Implemented stable workflow contracts (`PermitCaseWorkflowInput`, `ReviewDecisionSignal`) as Pydantic models.
- Implemented `ensure_permit_case_exists(case_id)` activity that uses the existing SQLAlchemy sessionmaker pattern to create a minimal `permit_cases` row (idempotent insert-if-missing).
- Implemented `PermitCaseWorkflow` that:
  - executes the bootstrap activity
  - deterministically waits via `workflow.wait_condition` until a `review_decision` signal sets workflow state
- Implemented runnable worker entrypoint (`python -m sps.workflows.worker`) that registers the workflow + activity and polls the configured task queue.

## Verification

- Installed deps: `./.venv/bin/python -m pip install -e ".[dev]"`.
- Brought up local infra: `docker compose up -d`.
  - (Fix applied: Temporal auto-setup expects `DB=postgres12`, `DB_PORT`, and cannot create DBs with the current role; compose now sets `SKIP_DB_CREATE=true`.)
- Ran worker (in background): `./.venv/bin/python -m sps.workflows.worker`.
  - Verified startup log lines: `temporal.worker.start` and `temporal.worker.polling`.
- Started `PermitCaseWorkflow` via Temporal UI (workflow id `CASE-DEV-001`, input `{"case_id":"CASE-DEV-001"}`):
  - Worker logs show `workflow.start` → `activity.ok ensure_permit_case_exists created=True` → `workflow.waiting signal=ReviewDecision`.
  - Verified Postgres row exists: `select ... from permit_cases where case_id='CASE-DEV-001'`.
- Test suite (non-integration): `./.venv/bin/pytest -q` → **pass**.
- Slice-level integration harness (expected to fail until T02):
  - `SPS_RUN_TEMPORAL_INTEGRATION=1 ./.venv/bin/pytest -q tests/m002_s01_temporal_permit_case_workflow_test.py` → **fails** (placeholder).

## Diagnostics

- Run worker: `python -m sps.workflows.worker`
- Inspect:
  - Temporal UI: http://localhost:8080 (workflow history will show activity success/failure)
  - Worker logs: grep for `workflow_id=<id> run_id=<id>`
- Expected log correlation tuple (no secrets): `workflow_id`, `run_id`, `case_id`, `activity name`, `exc_type`.

## Deviations

- Updated `docker-compose.yml` Temporal DB wiring (DB driver/env var names + `SKIP_DB_CREATE`) to make local Temporal boot successfully.
- Added Settings alias support for legacy `TEMPORAL_ADDRESS` env var (repo previously used `TEMPORAL_ADDRESS` in `.env.example`).

## Known Issues

- Operator CLI and the real end-to-end integration test are not implemented yet (T02).

## Files Created/Modified

- `pyproject.toml` — added Temporal runtime dependency.
- `src/sps/config.py` — added Temporal Settings fields (with legacy env alias support).
- `src/sps/workflows/worker.py` — Temporal worker entrypoint with Pydantic payload conversion + threadpool executor.
- `src/sps/workflows/permit_case/contracts.py` — workflow input + signal payload Pydantic contracts.
- `src/sps/workflows/permit_case/activities.py` — Postgres bootstrap activity (`ensure_permit_case_exists`).
- `src/sps/workflows/permit_case/workflow.py` — deterministic workflow (activity + signal wait).
- `docker-compose.yml` — fixed Temporal auto-setup Postgres config for local dev.
- `.env.example` — added `SPS_TEMPORAL_*` vars (and documented legacy alias).
- `tests/m002_s01_temporal_permit_case_workflow_test.py` — created placeholder (fails only when integration opt-in env is set).
