---
id: T01
parent: S01
milestone: M006-h7v2qk
provides:
  - Phase 6 fixture dataset (document templates + metadata JSON)
  - Deterministic fixture loader with case_id override support
  - Document/manifest contract models for typed generation
  - Integration test module with fixture validation tests
key_files:
  - specs/sps/build-approved/fixtures/phase6/documents.json
  - src/sps/fixtures/phase6.py
  - src/sps/documents/contracts.py
  - tests/m006_s01_document_package_test.py
key_decisions:
  - Phase 6 fixtures follow Phase 4/5 pattern with deterministic loader + override env var
  - Document templates stored as plain text files with mustache-style {{variable}} placeholders
  - Contract models use Pydantic with extra="forbid" for strict validation
  - Fixture metadata includes expected_digest placeholders computed during generation in T03
patterns_established:
  - Document fixture structure: document_sets[] containing documents[] + manifest
  - Template loader provides load_template(name) for runtime rendering
  - Manifest references include document_id, artifact_id, and sha256_digest
observability_surfaces:
  - Fixture loader logs FileNotFoundError with path for missing fixtures
  - Pydantic validation errors expose field paths for schema violations
  - Test output shows loaded fixture count and case_id override resolution
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16T08:56:00Z
blocker_discovered: false
---

# T01: Add Phase 6 fixtures, contracts, and test scaffolding

**Phase 6 fixtures load via deterministic loader with case_id override; document/manifest contracts and integration test module created.**

## What Happened

Created the Phase 6 fixture dataset with two document templates (permit application + site plan checklist) plus fixture metadata JSON defining document variables, manifest structure, and provenance. Implemented the fixture loader following Phase 4/5 patterns with deterministic loading and `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE` env var support for test flexibility.

Added contract models in `src/sps/documents/contracts.py` for typed document/manifest payloads with Pydantic strict validation. These contracts will drive document generation in T03 and ensure manifest references match artifact digests.

Created the integration test module `tests/m006_s01_document_package_test.py` with 10 fixture validation tests (all passing) and 6 stubbed integration tests that will be implemented in T02/T03 for package persistence, digest determinism, workflow wiring, and API retrieval.

Registered pytest marks (`fixtures`, `integration`) in pyproject.toml to eliminate warnings and enable selective test execution.

## Verification

Ran `pytest tests/m006_s01_document_package_test.py -k fixtures -v`:
- ✅ 10 fixture tests passed (schema validation, override selection, template loading, error cases)
- ✅ 6 integration tests correctly skipped with T02/T03 markers
- ✅ No warnings after registering pytest marks

Fixture loading tests confirm:
- Dataset schema validates with required fields (document_set_id, case_id, documents[], manifest)
- Pydantic enforces strict validation (extra fields raise AttributeError)
- Template loading succeeds for valid templates and fails cleanly for missing ones
- Case ID override resolution works with and without env var
- Fixture selection returns empty list when no match found

## Diagnostics

**Fixture inspection:**
- `pytest tests/m006_s01_document_package_test.py::test_load_phase6_fixtures_schema_valid -v -s` — shows loaded fixture structure
- `python -c "from sps.fixtures.phase6 import load_phase6_fixtures; print(load_phase6_fixtures().model_dump_json(indent=2))"` — dump full dataset

**Failure visibility:**
- Missing fixture file: `FileNotFoundError` with full path
- Schema validation failure: Pydantic `ValidationError` with field paths
- Override selection: test assertions verify expected vs actual case_id

**Template content:**
- `specs/sps/build-approved/fixtures/phase6/permit_application_template.txt`
- `specs/sps/build-approved/fixtures/phase6/site_plan_checklist_template.txt`

## Deviations

None. Task plan executed as written.

## Known Issues

None. Fixture loader and tests are complete and passing.

## Files Created/Modified

- `specs/sps/build-approved/fixtures/phase6/permit_application_template.txt` — permit application document template with mustache-style variables
- `specs/sps/build-approved/fixtures/phase6/site_plan_checklist_template.txt` — site plan checklist template
- `specs/sps/build-approved/fixtures/phase6/documents.json` — Phase 6 fixture metadata with document definitions + manifest structure
- `src/sps/fixtures/phase6.py` — deterministic fixture loader with case_id override support + template loader
- `src/sps/documents/__init__.py` — document service package init
- `src/sps/documents/contracts.py` — Pydantic contract models for DocumentArtifactPayload, SubmissionManifestPayload, SubmissionPackagePayload
- `tests/m006_s01_document_package_test.py` — integration test module with 10 fixture tests (passing) + 6 stubbed integration tests for T02/T03
- `pyproject.toml` — registered pytest marks for `fixtures` and `integration`
- `.gsd/milestones/M006-h7v2qk/slices/S01/S01-PLAN.md` — added failure path verification check
- `.gsd/milestones/M006-h7v2qk/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
