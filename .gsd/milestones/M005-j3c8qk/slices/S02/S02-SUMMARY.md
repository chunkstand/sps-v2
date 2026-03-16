---
id: S02
parent: M005-j3c8qk
milestone: M005-j3c8qk
provides:
  - IncentiveAssessment artifacts + incentives API + workflow advance to INCENTIVES_COMPLETE
requires:
  - slice: S01
    provides: ComplianceEvaluation artifacts and COMPLIANCE_COMPLETE workflow state
affects:
  - S03
key_files:
  - specs/sps/build-approved/fixtures/phase5/incentives.json
  - src/sps/fixtures/phase5.py
  - src/sps/db/models.py
  - alembic/versions/9b7a3d2c1f0e_incentive_assessments.py
  - src/sps/workflows/permit_case/contracts.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/workflow.py
  - invariants/sps/guard-assertions.yaml
  - src/sps/api/contracts/cases.py
  - src/sps/api/routes/cases.py
  - tests/m005_s02_incentives_workflow_test.py
key_decisions:
  - None
patterns_established:
  - Incentive freshness guard + incentives API/readback mirrors compliance guard/read patterns with ledger-backed denials
observability_surfaces:
  - incentives_activity.persisted log line
  - cases.incentives_fetched log line
  - case_transition_ledger INCENTIVES_* events
  - GET /api/v1/cases/{case_id}/incentives
  - incentive_assessments table
drill_down_paths:
  - .gsd/milestones/M005-j3c8qk/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M005-j3c8qk/slices/S02/tasks/T02-SUMMARY.md
duration: 3.1h
verification_result: passed
completed_at: 2026-03-15
---

# S02: Incentive assessment artifacts + workflow advance

**Persisted IncentiveAssessment artifacts with guarded workflow advancement to INCENTIVES_COMPLETE and incentives API readback.**

## What Happened
Fixture-backed incentive programs are now persisted as IncentiveAssessment rows with provenance/evidence JSONB, and a dedicated persistence activity mirrors compliance idempotency semantics. PermitCaseWorkflow now persists incentives after COMPLIANCE_COMPLETE and advances to INCENTIVES_COMPLETE behind a 3-day freshness guard (`INV-SPS-INC-001`). A new incentives read surface (`GET /api/v1/cases/{case_id}/incentives`) returns eligibility outcomes and provenance, and integration tests cover persistence, workflow progression, API readback fidelity, and guard denials for stale assessments.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s --log-cli-level=INFO`

## Requirements Advanced
- None.

## Requirements Validated
- R014 — Incentive assessment (F-005) proved by Temporal/Postgres integration tests and incentives API readback (`tests/m005_s02_incentives_workflow_test.py`).

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
None.

## Known Limitations
S03 docker-compose runbook proof is still pending for the end-to-end runtime path.

## Follow-ups
- Execute S03 docker-compose runbook proof for M005.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase5/incentives.json` — incentive fixture dataset.
- `src/sps/fixtures/phase5.py` — incentive fixture models, loaders, and selectors.
- `src/sps/db/models.py` — IncentiveAssessment ORM model.
- `alembic/versions/9b7a3d2c1f0e_incentive_assessments.py` — incentive_assessments migration.
- `src/sps/workflows/permit_case/contracts.py` — incentive assessment activity contract.
- `src/sps/workflows/permit_case/activities.py` — incentive persistence + freshness guard.
- `src/sps/workflows/permit_case/workflow.py` — workflow advance to INCENTIVES_COMPLETE.
- `invariants/sps/guard-assertions.yaml` — `INV-SPS-INC-001` guard definition.
- `src/sps/api/contracts/cases.py` — incentives response contracts.
- `src/sps/api/routes/cases.py` — incentives API endpoint + logging.
- `tests/m005_s02_incentives_workflow_test.py` — persistence, workflow, and guard denial integration tests.

## Forward Intelligence
### What the next slice should know
- The incentive freshness guard is 3 days; runbook timestamps or fixture overrides must keep `evaluated_at` within that window.
- Workflow progression now expects IncentiveAssessment persistence after COMPLIANCE_COMPLETE and before INCENTIVES_COMPLETE.

### What's fragile
- Incentive assessment freshness relies on fixture timestamps; stale fixtures will trigger `INV-SPS-INC-001` denials in the runbook.

### Authoritative diagnostics
- `case_transition_ledger` rows for `INCENTIVES_*` events — canonical proof of transition outcomes.
- `GET /api/v1/cases/{case_id}/incentives` — confirms persisted assessment payloads.
- `incentives_activity.persisted` / `cases.incentives_fetched` logs — fastest signal of activity and API readback.

### What assumptions changed
- None.
