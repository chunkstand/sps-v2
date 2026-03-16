---
id: T01
parent: S02
milestone: M007-b2t1rz
provides:
  - phase 7 status mapping fixtures + loader selection helper
key_files:
  - specs/sps/build-approved/fixtures/phase7/status-maps.json
  - src/sps/fixtures/phase7.py
  - tests/m007_s02_external_status_events_test.py
key_decisions:
  - none
patterns_established:
  - phase 7 fixtures load via pydantic dataset validation + case_id override selection helpers
observability_surfaces:
  - status mapping selection returns mapping_version metadata; fixture file is the source of truth
  - diagnostics via fixture selection errors (missing adapter family, duplicate raw status)
duration: 0.5h
verification_result: failed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add Phase 7 status mapping fixtures + loader

**Added Phase 7 status mapping fixtures plus loader helpers that select a versioned mapping by adapter family for a case.**

## What Happened
- Added `status-maps.json` fixture dataset with adapter family mapping metadata and sample raw→normalized entries.
- Extended Phase 7 fixture loader with status mapping models, loader, and selection helper that honors the case override.
- Added integration test asserting mapping version + normalized status selection for the fixture case.

## Verification
- `pytest tests/m007_s02_external_status_events_test.py -v -s` failed: `pytest` not found in the environment.
- `python -m pytest tests/m007_s02_external_status_events_test.py -v -s` failed: `python` not found in the environment.

## Diagnostics
- Validate mapping selection via `select_status_mapping_for_case`, which returns `mapping_version` + indexed raw status mappings.
- Fixture file `specs/sps/build-approved/fixtures/phase7/status-maps.json` is the source of truth for adapter family mappings.

## Deviations
- None.

## Known Issues
- Test verification could not run because neither `pytest` nor `python` were available in the environment.

## Files Created/Modified
- `specs/sps/build-approved/fixtures/phase7/status-maps.json` — added Phase 7 status mapping fixtures with version metadata.
- `src/sps/fixtures/phase7.py` — added status mapping fixtures loader and case selection helper.
- `tests/m007_s02_external_status_events_test.py` — added loader selection integration test.
- `.gsd/milestones/M007-b2t1rz/slices/S02/S02-PLAN.md` — marked T01 complete.
- `.gsd/milestones/M007-b2t1rz/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section.
- `.gsd/STATE.md` — advanced next action to T02.
