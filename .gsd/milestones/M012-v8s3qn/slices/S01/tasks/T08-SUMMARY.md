---
id: T08
parent: S01
milestone: M012-v8s3qn
provides:
  - Docker-compose runbook proving emergency/override lifecycle with API, worker, and Postgres assertions
key_files:
  - scripts/verify_m012_s01.sh
  - src/sps/workflows/worker.py
  - .gsd/milestones/M012-v8s3qn/slices/S01/tasks/T08-PLAN.md
key_decisions:
  - Added Temporal namespace check/registration in the runbook to ensure workflow creation is available.
patterns_established:
  - Runbook uses step/pass/fail logging with psql polling for workflow-driven state transitions.
observability_surfaces:
  - runbook.step/runbook.pass/runbook.fail logs; workflow.emergency_hold_entered/workflow.emergency_hold_exited logs; Postgres case_transition_ledger queries
duration: 2h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T08: Docker-compose runbook for full emergency/override lifecycle

**Shipped a full docker-compose runbook that exercises emergency/override creation, guard bypass, expiry denial, and EMERGENCY_HOLD cleanup with API + worker + Postgres proofs.**

## What Happened
- Authored `scripts/verify_m012_s01.sh` to provision the stack, create intake/emergency/override artifacts, apply override-protected transitions, expire overrides, and drive EMERGENCY_HOLD entry/exit with ledger assertions and structured runbook logs.
- Added Temporal namespace readiness/registration to avoid workflow startup failures during runbook execution.
- Registered emergency validation activities in the worker so emergency hold signals resolve successfully in runtime.
- Tightened runbook sequencing: confirm EMERGENCY_HOLD entry via ledger polling before sending exit signals, ensuring deterministic exit verification.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m012_s01_override_guard_test.py -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m012_s01_emergency_hold_test.py -v`
- `bash scripts/verify_m012_s01.sh`

## Diagnostics
- `bash scripts/verify_m012_s01.sh` emits runbook.step/runbook.pass/runbook.fail logs and uses Postgres queries for evidence.
- `docker compose exec -T postgres psql -U sps -d sps -c "SELECT event_type, payload->>'guard_assertion_id' FROM case_transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY occurred_at DESC LIMIT 3"`

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `scripts/verify_m012_s01.sh` — end-to-end docker-compose runbook with lifecycle assertions and Temporal namespace readiness.
- `src/sps/workflows/worker.py` — registers emergency validation activities required by EMERGENCY_HOLD signals.
- `.gsd/milestones/M012-v8s3qn/slices/S01/tasks/T08-PLAN.md` — reduced step count and consolidated steps.
