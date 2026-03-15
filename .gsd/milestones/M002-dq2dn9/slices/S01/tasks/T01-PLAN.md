---
estimated_steps: 7
estimated_files: 7
---

# T01: Add Temporal workflow + worker + Postgres bootstrap activity

**Slice:** S01 — Temporal worker + minimal PermitCaseWorkflow (signal wait) + operator CLI
**Milestone:** M002-dq2dn9

## Description

Introduce the minimal Temporal workflow substrate:
- a replay-safe `PermitCaseWorkflow` that performs no I/O directly,
- a single Postgres-backed bootstrap activity (`ensure_permit_case_exists`) to prove activity I/O wiring,
- and a worker entrypoint that can be run locally against docker-compose Temporal.

This task is intentionally focused on the determinism boundary and worker connectivity; the operator CLI + end-to-end test harness lands in T02.

## Steps

1. Add Temporal runtime dependencies and minimal Temporal config fields to `sps.config.Settings` (address/namespace/task-queue with safe local defaults).
2. Create workflow input + signal payload contracts (Pydantic models) for `PermitCaseWorkflow`.
3. Implement `ensure_permit_case_exists(case_id)` activity that upserts a minimal `permit_cases` row using the existing SQLAlchemy session pattern.
4. Implement `PermitCaseWorkflow` that: runs the bootstrap activity, then waits deterministically for a `ReviewDecision` signal (store it in workflow state; no wall-clock, random, or DB access in workflow code).
5. Implement `python -m sps.workflows.worker` entrypoint that registers the workflow + activities and starts polling the configured task queue.

## Must-Haves

- [ ] Temporal worker starts locally and connects to `localhost:7233` by default.
- [ ] `PermitCaseWorkflow` runs the bootstrap activity then blocks waiting on a `ReviewDecision` signal.
- [ ] All Postgres I/O happens in an activity (not in workflow code).

## Verification

- Start local infra: `docker compose up -d`
- Start worker: `python -m sps.workflows.worker`
- Sanity-check via Temporal UI: http://localhost:8080 (worker visible; workflow registration errors absent)

(Full automated integration assertion happens in T02.)

## Observability Impact

- Signals added/changed: worker/activity log lines include `workflow_id`, `run_id`, `case_id`, activity name, and exception type.
- How a future agent inspects this: Temporal UI history + worker stdout logs.
- Failure state exposed: activity failures are visible as Temporal activity failures; worker logs provide correlation tuple for grep.

## Inputs

- `src/sps/db/session.py` — DB sessionmaker/engine pattern to reuse in activities
- `src/sps/db/models.py` — `PermitCase` table definition for the bootstrap activity

## Expected Output

- `src/sps/workflows/worker.py` — runnable worker entrypoint registering workflows/activities
- `src/sps/workflows/permit_case/workflow.py` — minimal deterministic workflow waiting on a signal
- `src/sps/workflows/permit_case/activities.py` — Postgres bootstrap activity proving I/O boundary
- `src/sps/workflows/permit_case/contracts.py` — stable workflow input + signal payload contracts
