---
estimated_steps: 4
estimated_files: 6
---

# T01: Add jurisdiction/requirements fixtures + persistence schema

**Slice:** S02 — Jurisdiction + requirements fixtures, persistence, and workflow progression
**Milestone:** M004-lp1flz

## Description
Create Phase 4 fixture datasets and the persistence schema for JurisdictionResolution and RequirementSet so downstream activities can load authoritative data with provenance.

## Steps
1. Add fixture JSON under `specs/sps/build-approved/fixtures/phase4` aligned with `model/sps/model.yaml` fields (support level, evidence IDs, freshness/contradiction states, rankings).
2. Add JurisdictionResolution + RequirementSet ORM models with JSONB provenance/evidence payloads.
3. Create Alembic migration for the new tables and indexes/foreign keys.
4. Add a fixture loader/validator module in `src/sps/fixtures/phase4.py` used by activities.

## Must-Haves
- [ ] Fixture datasets exist at the decided Phase 4 path with spec-aligned fields.
- [ ] JurisdictionResolution + RequirementSet tables are created via migration and wired to ORM models.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py -k fixture_schema`
- `./.venv/bin/alembic upgrade head` (or existing migration harness in tests)

## Inputs
- `model/sps/model.yaml` — authoritative field shapes for jurisdiction + requirements.
- `src/sps/db/models.py` — current ORM patterns for JSONB provenance fields.

## Observability Impact
- New inspection surfaces: `jurisdiction_resolutions` and `requirement_sets` tables populated from fixtures with JSONB provenance/evidence payloads.
- Loader/validator emits structured validation errors tied to fixture file + record id; failures surface during tests and activity runs.
- Migration adds indexes/foreign keys so failure states (missing case_id) surface as DB constraint errors in logs.

## Expected Output
- `specs/sps/build-approved/fixtures/phase4/jurisdiction.json` — fixture dataset.
- `specs/sps/build-approved/fixtures/phase4/requirements.json` — fixture dataset.
- `src/sps/fixtures/phase4.py` — loader/validator.
- `alembic/versions/<new>_jurisdiction_requirements.py` — migration.
- `src/sps/db/models.py` — new ORM models.
