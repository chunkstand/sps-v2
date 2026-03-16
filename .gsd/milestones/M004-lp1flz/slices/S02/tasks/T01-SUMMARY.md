---
id: T01
parent: S02
milestone: M004-lp1flz
provides:
  - phase4 fixture datasets, loader/validator, and DB schema for jurisdiction + requirements artifacts
key_files:
  - specs/sps/build-approved/fixtures/phase4/jurisdiction.json
  - specs/sps/build-approved/fixtures/phase4/requirements.json
  - src/sps/fixtures/phase4.py
  - src/sps/db/models.py
  - alembic/versions/b2c4f7e8a901_jurisdiction_requirements.py
  - tests/m004_s02_jurisdiction_requirements_workflow_test.py
key_decisions:
  - Stored provenance and evidence payloads as JSONB columns on the new tables to preserve fixture metadata.
patterns_established:
  - Phase 4 fixtures validated via pydantic dataset loaders with evidence-id validation.
observability_surfaces:
  - jurisdiction_resolutions/requirement_sets tables plus loader validation errors for fixture schema mismatches
duration: 1h
verification_result: mixed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add jurisdiction/requirements fixtures + persistence schema

**Added phase4 fixtures, loader/validator, and DB schema for jurisdiction/requirements artifacts.**

## What Happened
- Added phase 4 jurisdiction/requirements fixture datasets with evidence/support/freshness fields and metadata.
- Implemented pydantic-based fixture loaders with evidence-id validation and project-root path resolution.
- Added JurisdictionResolution and RequirementSet ORM models with JSONB provenance/evidence payloads and timestamps.
- Created Alembic migration for the new tables and indexes.
- Added fixture schema test coverage.

## Verification
- `./.venv/bin/pytest tests/m004_s02_jurisdiction_requirements_workflow_test.py` ✅
- `./.venv/bin/alembic upgrade head` ✅
- `bash scripts/verify_m004_s02.sh` ❌ (script missing: `scripts/verify_m004_s02.sh` not found)

## Diagnostics
- Inspect fixture validation by calling `load_phase4_fixtures()` (raises validation error with fixture path on failure).
- Inspect persisted data via `jurisdiction_resolutions` and `requirement_sets` tables.

## Deviations
- None.

## Known Issues
- `scripts/verify_m004_s02.sh` is missing, so slice verification script cannot run yet.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase4/jurisdiction.json` — phase 4 jurisdiction fixture dataset.
- `specs/sps/build-approved/fixtures/phase4/requirements.json` — phase 4 requirements fixture dataset.
- `src/sps/fixtures/__init__.py` — fixtures module init.
- `src/sps/fixtures/phase4.py` — fixture loader/validator models and helpers.
- `src/sps/db/models.py` — added JurisdictionResolution and RequirementSet ORM models.
- `alembic/versions/b2c4f7e8a901_jurisdiction_requirements.py` — migration for new tables and indexes.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — fixture schema validation tests.
