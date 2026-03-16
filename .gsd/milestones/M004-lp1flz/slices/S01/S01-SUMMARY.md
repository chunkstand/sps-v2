---
id: S01
parent: M004-lp1flz
milestone: M004-lp1flz
provides:
  - Spec-derived intake contract + Project persistence + INTAKE_COMPLETE workflow step
requires: []
affects:
  - S02
  - S03
key_files:
  - src/sps/api/contracts/intake.py
  - src/sps/api/routes/cases.py
  - src/sps/api/main.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - tests/m004_s01_intake_api_workflow_test.py
  - scripts/verify_m004_s01.sh
key_decisions:
  - none
patterns_established:
  - Intake payload normalized into Project with contact_metadata and persisted with PermitCase in a single transaction
  - Workflow branches on PermitCase state snapshot and applies INTAKE_PENDING → INTAKE_COMPLETE via guarded transition
observability_surfaces:
  - Structured logs: intake_api.case_created, workflow.transition_attempt/transition_applied
  - case_transition_ledger rows for INTAKE_COMPLETE
  - scripts/verify_m004_s01.sh runbook output + log tail hints
  - docker compose logs api | grep intake_api
  - docker compose logs worker | grep transition
  - docker compose exec postgres psql -c "select * from case_transition_ledger"
drill_down_paths:
  - .gsd/milestones/M004-lp1flz/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004-lp1flz/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M004-lp1flz/slices/S01/tasks/T03-SUMMARY.md
duration: 4.6h
verification_result: passed
completed_at: 2026-03-15
---

# S01: Intake contract + Project persistence + INTAKE_COMPLETE workflow step

**Spec-derived intake payloads now create PermitCase + Project and the workflow advances to INTAKE_COMPLETE with ledger evidence.**

## What Happened
Added a spec-aligned intake contract and `/api/v1/cases` endpoint that persists PermitCase + Project rows, then starts the PermitCaseWorkflow. Wired a workflow intake branch that snapshots case state and applies a guarded INTAKE_PENDING → INTAKE_COMPLETE transition when Project exists. Added integration tests and a docker-compose runbook that exercise the full HTTP → Postgres → Temporal path and verify the ledger transition.

## Verification
- `./.venv/bin/pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation`
- `./.venv/bin/pytest tests/m004_s01_intake_api_workflow_test.py` (1 skipped unless `SPS_RUN_TEMPORAL_INTEGRATION=1`)
- `bash scripts/verify_m004_s01.sh`

## Requirements Advanced
- R010 — Intake contract persists PermitCase + Project and normalizes intake into Project fields.

## Requirements Validated
- R010 — Runbook + integration tests prove intake persistence and INTAKE_COMPLETE ledger transition.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Temporal integration test remains opt-in via `SPS_RUN_TEMPORAL_INTEGRATION=1` (runbook covers the live workflow path).

## Follow-ups
- Implement jurisdiction + requirements persistence and workflow progression in S02.

## Files Created/Modified
- `src/sps/api/contracts/intake.py` — CreateCase intake request/response contract models.
- `src/sps/api/routes/cases.py` — intake endpoint with transactional PermitCase/Project persistence and workflow start.
- `src/sps/api/main.py` — register `/api/v1/cases` router.
- `src/sps/workflows/permit_case/activities.py` — case state snapshot + INTAKE_COMPLETE guard logic.
- `src/sps/workflows/permit_case/workflow.py` — intake branch and robust snapshot parsing.
- `tests/m004_s01_intake_api_workflow_test.py` — contract validation + Temporal integration test.
- `scripts/verify_m004_s01.sh` — docker-compose runbook with Postgres assertions.

## Forward Intelligence
### What the next slice should know
- The intake runbook starts its own worker and API processes and uses a unique Temporal task queue per run to avoid backlog interference.

### What's fragile
- The INTAKE_COMPLETE guard requires a persisted Project row; missing Project rows will surface as guard denials in `case_transition_ledger`.

### Authoritative diagnostics
- `case_transition_ledger` with `event_type=CASE_STATE_CHANGED` and `to_state=INTAKE_COMPLETE` — authoritative proof that the guard executed and state advanced.

### What assumptions changed
- “Integration test is the only proof surface” — the runbook is now the authoritative live-runtime proof for S01.
