---
estimated_steps: 3
estimated_files: 6
---

# T01: Add incentive fixtures, schema, and persistence activity

**Slice:** S02 — Incentive assessment artifacts + workflow advance
**Milestone:** M005-j3c8qk

## Description
Introduce fixture-backed IncentiveAssessment artifacts with deterministic selectors, a durable schema + migration, and an idempotent persistence activity that mirrors compliance. This establishes the authoritative data boundary needed for workflow advancement.

## Steps
1. Add `specs/sps/build-approved/fixtures/phase5/incentives.json` and extend `src/sps/fixtures/phase5.py` with incentive fixture models + selector helpers (including override semantics).
2. Add IncentiveAssessment ORM mapping in `src/sps/db/models.py` and a matching Alembic migration with JSONB provenance/evidence fields.
3. Extend `src/sps/workflows/permit_case/contracts.py` and add `persist_incentive_assessment` activity in `src/sps/workflows/permit_case/activities.py` with idempotent insert semantics mirroring compliance.

## Must-Haves
- [ ] Incentive fixtures load deterministically with case override support.
- [ ] IncentiveAssessment rows persist idempotently with provenance/evidence payloads.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "fixtures" -v -s`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s02_incentives_workflow_test.py -k "persistence" -v -s`

## Observability Impact
- Signals added/changed: `incentives_activity.persisted` log and `incentive_assessments` table rows.
- How a future agent inspects this: query `incentive_assessments` or scan activity logs for persistence IDs.
- Failure state exposed: activity retry behavior or duplicate-key idempotency in logs.

## Inputs
- `src/sps/fixtures/phase5.py` — compliance fixture selector/override pattern to mirror.
- S01 summary — compliance persistence activity pattern and fixture override semantics.

## Expected Output
- `specs/sps/build-approved/fixtures/phase5/incentives.json` — incentive fixture dataset.
- `src/sps/fixtures/phase5.py` — incentive fixture models + selector helpers.
- `src/sps/db/models.py` + `alembic/versions/<new>_incentive_assessments.py` — IncentiveAssessment schema.
- `src/sps/workflows/permit_case/contracts.py` + `src/sps/workflows/permit_case/activities.py` — incentive persistence contract + activity.
