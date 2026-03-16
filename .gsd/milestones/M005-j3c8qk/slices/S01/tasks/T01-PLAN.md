---
estimated_steps: 5
estimated_files: 6
---

# T01: Add compliance fixture schema + persistence activity

**Slice:** S01 — Compliance evaluation artifacts + workflow advance  
**Milestone:** M005-j3c8qk

## Description
Define the phase5 compliance fixture dataset, add the ComplianceEvaluation ORM + migration, and implement an idempotent activity that evaluates fixtures deterministically and persists rule results with provenance. This establishes the authoritative data shape and activity contract before workflow wiring.

## Steps
1. Create `src/sps/fixtures/phase5.py` with fixture models (schema_version, generated_at, evaluations) and loader helpers mirroring phase4 patterns, plus a selector that supports an env-gated fixture case_id override.
2. Add the phase5 fixture dataset at `specs/sps/build-approved/fixtures/phase5/compliance.json` with stable IDs, rule-level results, blockers/warnings, and provenance payloads.
3. Add `ComplianceEvaluation` ORM to `src/sps/db/models.py` and an Alembic migration that creates the `compliance_evaluations` table with JSONB columns for rule results, blockers, warnings, provenance, and evidence payload.
4. Add activity contract `PersistComplianceEvaluationRequest` in `src/sps/workflows/permit_case/contracts.py` and implement `persist_compliance_evaluation` in `src/sps/workflows/permit_case/activities.py` with deterministic evaluation + idempotent insert logic and structured logs.
5. Ensure the activity logs `compliance_activity.persisted` and `activity.ok` with workflow/run/case IDs and counts, and returns the persisted evaluation IDs.

## Must-Haves
- [ ] Phase5 compliance fixture dataset validates via Pydantic and includes rule results + provenance.
- [ ] `compliance_evaluations` table exists with JSONB provenance fields and stable primary key.
- [ ] `persist_compliance_evaluation` persists fixtures idempotently and logs structured success events.

## Verification
- `python -m pytest tests/m005_s01_compliance_workflow_test.py -k "fixture_schema" -v`
- `python -c "from sps.fixtures.phase5 import load_compliance_fixtures; print(load_compliance_fixtures().schema_version)"`

## Observability Impact
- Signals added/changed: `compliance_activity.persisted` and `activity.ok name=persist_compliance_evaluation` logs
- How a future agent inspects this: `SELECT compliance_evaluation_id, case_id, created_at FROM compliance_evaluations ORDER BY created_at DESC LIMIT 5;`
- Failure state exposed: activity exception logs include `activity.error name=persist_compliance_evaluation ... exc_type=...`

## Inputs
- `src/sps/fixtures/phase4.py` — fixture loader patterns and override behavior
- `src/sps/db/models.py` — ORM conventions + JSONB columns
- `src/sps/workflows/permit_case/activities.py` — existing idempotent persistence patterns

## Expected Output
- `src/sps/fixtures/phase5.py` — phase5 compliance fixture schema + loader
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — fixture dataset
- `src/sps/db/models.py` and `alembic/versions/*.py` — ComplianceEvaluation storage
- `src/sps/workflows/permit_case/contracts.py` + `src/sps/workflows/permit_case/activities.py` — activity contract + implementation
