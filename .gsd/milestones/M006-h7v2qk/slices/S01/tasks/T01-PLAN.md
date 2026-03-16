---
estimated_steps: 5
estimated_files: 4
---

# T01: Add Phase 6 fixtures, contracts, and test scaffolding
**Slice:** S01 — Deterministic document artifacts + submission package persistence
**Milestone:** M006-h7v2qk

## Description
Define the Phase 6 fixture dataset (templates + metadata), add contract models for document/manifest payloads, and create the integration test module that will validate fixture determinism and later package persistence. This locks the inputs and test harness before we touch persistence or workflow wiring.

## Steps
1. Add `specs/sps/build-approved/fixtures/phase6` assets (document templates + fixture metadata JSON) aligned to the spec package.
2. Implement `src/sps/fixtures/phase6.py` with Pydantic fixture models, deterministic loader, and case_id override env var (mirroring Phase 4/5 patterns).
3. Create document/manifest contract models in `src/sps/documents/contracts.py` for typed generation + manifest assembly.
4. Add `tests/m006_s01_document_package_test.py` with fixture schema load tests and override selection assertions; stub the integration tests that will later assert package persistence/digest determinism.
5. Run the fixture-only test subset to validate the dataset loads cleanly.

## Must-Haves
- [ ] Phase 6 fixtures load via a deterministic loader with case_id override support.
- [ ] Test module exists and exercises fixture schema validation + override selection.

## Verification
- `pytest tests/m006_s01_document_package_test.py -k fixtures -v`

## Observability Impact
- **Runtime signals:** Fixture loader logs structured events (start/ok/error with fixture_name + case_id on load); test framework records fixture schema validation failures with field paths.
- **Inspection surfaces:** Tests expose loaded fixture metadata as test fixtures; fixture models surface field errors via Pydantic validation exceptions.
- **Failure visibility:** Schema validation failures include field name + error message; missing fixture files produce FileNotFoundError with path; case_id override selection failures log expected vs actual case_id.
- **Future agent hook:** Read `tests/m006_s01_document_package_test.py::test_load_phase6_fixtures` output to see fixture schema + loaded case count; check `src/sps/fixtures/phase6.py::load_fixtures()` implementation to understand override mechanism.

## Inputs
- `specs/sps/build-approved/fixtures/phase5/*` — prior fixture pattern and schema shape guidance.
- `src/sps/fixtures/phase4.py` — loader/override patterns to mirror.

## Expected Output
- `specs/sps/build-approved/fixtures/phase6/*` — Phase 6 template + metadata fixtures.
- `src/sps/fixtures/phase6.py` — deterministic fixture loader + models.
- `src/sps/documents/contracts.py` — typed document + manifest contracts.
- `tests/m006_s01_document_package_test.py` — fixture tests + integration scaffolding.
