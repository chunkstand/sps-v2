---
estimated_steps: 4
estimated_files: 2
---

# T01: Add Phase 7 status mapping fixtures + loader

**Slice:** S02 — Status normalization + tracking events
**Milestone:** M007-b2t1rz

## Description
Add the Phase 7 status mapping fixture dataset and extend the existing Phase 7 fixture loader to return a deterministic, versioned mapping for a given case/adapter family. This is the single source of truth for status normalization in the activity.

## Steps
1. Create `specs/sps/build-approved/fixtures/phase7/status-maps.json` with adapter family, version metadata, and raw→normalized status mappings.
2. Extend `src/sps/fixtures/phase7.py` to load status mappings and select the correct map for a case (honor `SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`).
3. Add a helper in the loader that returns the selected mapping + version metadata for activity use.
4. Add/extend tests in `tests/m007_s02_external_status_events_test.py` to assert the loader returns expected mapping/version for a fixture case.

## Must-Haves
- [ ] Status mapping fixture file exists under `specs/sps/build-approved/fixtures/phase7` with version metadata.
- [ ] Loader returns the correct mapping entry for the fixture case and exposes version metadata.

## Verification
- `pytest tests/m007_s02_external_status_events_test.py -v -s`
- Assert mapping lookup returns the expected normalized status and mapping version.

## Inputs
- `src/sps/fixtures/phase7.py` — existing Phase 7 fixture loader and override pattern.

## Expected Output
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — versioned status mapping fixture dataset.
- `src/sps/fixtures/phase7.py` — loader exposes mapping lookup helper for status normalization.

## Observability Impact
- Signals: loader now surfaces mapping_version metadata for external status normalization; activity logs should include mapping_version for successful and failed mappings.
- Inspection: verify mapping selection by calling the loader helper in tests; fixture data is the source of truth in `specs/sps/build-approved/fixtures/phase7/status-maps.json`.
- Failure visibility: missing/unknown mapping should raise with raw_status + mapping_version available for diagnostics (no PII).
