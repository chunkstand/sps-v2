---
id: T01
parent: S02
milestone: M005-j3c8qk
provides:
  - Incentive fixtures, schema, and idempotent persistence activity
key_files:
  - specs/sps/build-approved/fixtures/phase5/incentives.json
  - src/sps/fixtures/phase5.py
  - src/sps/db/models.py
  - alembic/versions/9b7a3d2c1f0e_incentive_assessments.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/contracts.py
  - tests/m005_s02_incentives_workflow_test.py
key_decisions:
  - None
patterns_established:
  - Phase5 incentive fixture schema + selector override mirrors compliance fixtures
observability_surfaces:
  - incentives_activity.persisted log line; incentive_assessments table rows
duration: 1.6h
verification_result: partial (guard_denial selector run had no tests)
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add incentive fixtures, schema, and persistence activity

**Added incentive fixtures, schema, and an idempotent persistence activity with log-backed observability.**

## What Happened
- Added Phase 5 incentive fixture dataset plus Pydantic models, loaders, and case-ID override selectors.
- Introduced IncentiveAssessment ORM model and Alembic migration with JSONB provenance/evidence fields.
- Implemented persist_incentive_assessment activity mirroring compliance idempotency semantics and logging.
- Added new incentives fixture/persistence tests (fixture schema + idempotent persistence + log signal capture).

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "fixtures" -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "persistence" -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "guard_denial" -v -s --log-cli-level=INFO` (no guard_denial tests yet; pytest exit code 5)

## Diagnostics
- Query `incentive_assessments` for persisted rows.
- Inspect `incentives_activity.persisted` log line for idempotency + request correlation.

## Deviations
- None.

## Known Issues
- Guard denial test coverage is pending (added in T02); the guard_denial verification command currently selects no tests.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase5/incentives.json` — incentive fixture dataset.
- `src/sps/fixtures/phase5.py` — incentive models/loaders/selectors with case override semantics.
- `src/sps/db/models.py` — IncentiveAssessment ORM mapping.
- `alembic/versions/9b7a3d2c1f0e_incentive_assessments.py` — incentive_assessments migration.
- `src/sps/workflows/permit_case/contracts.py` — PersistIncentiveAssessmentRequest contract.
- `src/sps/workflows/permit_case/activities.py` — persist_incentive_assessment activity + logging.
- `tests/m005_s02_incentives_workflow_test.py` — fixture and persistence tests.
