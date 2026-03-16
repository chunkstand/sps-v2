---
id: T03
parent: S01
milestone: M004-lp1flz
provides:
  - Intake flow integration test + runbook proving HTTP → Postgres → Temporal → INTAKE_COMPLETE
key_files:
  - tests/m004_s01_intake_api_workflow_test.py
  - scripts/verify_m004_s01.sh
  - src/sps/workflows/permit_case/workflow.py
key_decisions:
  - none
patterns_established:
  - Temporal integration tests wait for ledger rows and are gated by SPS_RUN_TEMPORAL_INTEGRATION
observability_surfaces:
  - runbook: structured runbook: logs + Postgres assertions + log tail diagnostics
duration: 1.6h
verification_result: partial (1 skipped)
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Add integration test + operator runbook for intake flow

**Added a Temporal-backed intake integration test and a docker-compose runbook that proves INTAKE_COMPLETE is recorded in the ledger.**

## What Happened
- Reworked the intake test to spin up a real Temporal worker, call `/api/v1/cases` over ASGI, assert PermitCase/Project persistence, and poll the ledger for INTAKE_COMPLETE.
- Added `scripts/verify_m004_s01.sh` to exercise the full flow against docker-compose services with structured runbook logs, Postgres assertions, and diagnostics.
- Hardened `PermitCaseWorkflow` snapshot parsing to handle activity-returned Pydantic models across the Temporal boundary.
- Ensured the runbook uses a unique Temporal task queue per run to avoid stale workflow backlog interference.

## Verification
- `./.venv/bin/pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation`
- `./.venv/bin/pytest tests/m004_s01_intake_api_workflow_test.py` (1 skipped: `SPS_RUN_TEMPORAL_INTEGRATION` not set)
- `bash scripts/verify_m004_s01.sh`

## Diagnostics
- Runbook emits `runbook:` progress markers, Postgres assertion output, and log tails on failure.
- Ledger inspection via `case_transition_ledger` (see runbook summary + diagnostics in the script).

## Deviations
- None.

## Known Issues
- Temporal integration test is opt-in and will skip unless `SPS_RUN_TEMPORAL_INTEGRATION=1` is set.

## Files Created/Modified
- `tests/m004_s01_intake_api_workflow_test.py` — Temporal-backed intake integration test with ledger polling.
- `scripts/verify_m004_s01.sh` — Operator runbook for the intake flow with Postgres assertions.
- `src/sps/workflows/permit_case/workflow.py` — Robust snapshot parsing for activity-returned models.
