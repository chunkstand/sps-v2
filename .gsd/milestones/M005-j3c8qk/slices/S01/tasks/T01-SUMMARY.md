---
id: T01
parent: S01
milestone: M005-j3c8qk
provides:
  - Phase 5 compliance fixtures, schema, persistence activity, and storage table.
key_files:
  - src/sps/fixtures/phase5.py
  - specs/sps/build-approved/fixtures/phase5/compliance.json
  - src/sps/workflows/permit_case/activities.py
  - src/sps/db/models.py
  - alembic/versions/e1c2f4b5a6c7_compliance_evaluations.py
key_decisions:
  - None
patterns_established:
  - Phase5 fixture selectors mirror phase4 override + case-id rewrite pattern.
observability_surfaces:
  - structured logs: compliance_activity.persisted + activity.ok name=persist_compliance_evaluation
  - persistence surface: compliance_evaluations table
duration: 50m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add compliance fixture schema + persistence activity

**Added Phase 5 compliance fixtures, ORM/migration storage, and an idempotent activity to persist fixture-backed evaluations with provenance.**

## What Happened
- Added `phase5` fixture schema/models plus case-id override selector helpers and created the compliance fixture dataset.
- Introduced `ComplianceEvaluation` ORM + migration with JSONB fields for rule results, blockers, warnings, provenance, and evidence payloads.
- Implemented `persist_compliance_evaluation` activity using deterministic fixture selection, JSONB serialization, idempotent insert logic, and structured logs.
- Added fixture schema validation test for the new dataset.

## Verification
- `.venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -k "fixture_schema" -v`
- `.venv/bin/python -c "from sps.fixtures.phase5 import load_compliance_fixtures; print(load_compliance_fixtures().schema_version)"`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m005_s01_compliance_workflow_test.py -v -s`

## Diagnostics
- Logs: `compliance_activity.persisted` and `activity.ok name=persist_compliance_evaluation` include workflow/run/case IDs and counts.
- Table inspection: `SELECT compliance_evaluation_id, case_id, created_at FROM compliance_evaluations ORDER BY created_at DESC LIMIT 5;`

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/fixtures/phase5.py` — Phase 5 compliance fixture schema + loader/selector helpers.
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — Fixture dataset with rule results, blockers, warnings, and provenance payloads.
- `src/sps/db/models.py` — Added ComplianceEvaluation ORM mapping.
- `alembic/versions/e1c2f4b5a6c7_compliance_evaluations.py` — Migration for compliance_evaluations table.
- `src/sps/workflows/permit_case/contracts.py` — Added PersistComplianceEvaluationRequest contract.
- `src/sps/workflows/permit_case/activities.py` — Added persist_compliance_evaluation activity and logging.
- `tests/m005_s01_compliance_workflow_test.py` — Fixture schema validation test.
