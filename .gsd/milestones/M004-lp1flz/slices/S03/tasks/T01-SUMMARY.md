---
id: T01
parent: S03
milestone: M004-lp1flz
provides:
  - Phase 4 fixture override selection that rewrites case_ids to runtime values
key_files:
  - src/sps/fixtures/phase4.py
  - src/sps/workflows/permit_case/activities.py
  - tests/m004_s03_fixture_override_test.py
key_decisions:
  - Use env-gated helper functions to select fixtures and rewrite case_id before persistence.
patterns_established:
  - Fixture selection returns (fixtures, fixture_case_id) for logging + error context.
observability_surfaces:
  - activity.lookup logs + LookupError messages include fixture_case_id alongside case_id.
duration: 35m
verification_result: partial
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Add fixture override selection for Phase 4 activities

**Added override-aware fixture selection that rewrites case_ids while persisting artifacts under the runtime intake case_id.**

## What Happened
- Added env-gated selection helpers in `phase4.py` to resolve fixture case IDs and rewrite fixture case_ids to the runtime case_id.
- Updated jurisdiction/requirements activities to use the helpers, log fixture_case_id alongside case_id, and surface both in LookupError text.
- Added focused tests covering override selection and default behavior.

## Verification
- `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
- `bash scripts/verify_m004_s03.sh` (failed: script missing)
- `docker compose logs worker | grep -E "LookupError|fixture_case_id"` (failed: no worker service running)

## Diagnostics
- Check `docker compose logs worker | grep persist_jurisdiction_resolutions` for `fixture_case_id` fields.
- Lookup failures include `fixture_case_id` in the exception message for rapid diagnosis.

## Deviations
- None.

## Known Issues
- `scripts/verify_m004_s03.sh` is not yet present; slice runbook verification still pending in T02.
- Docker compose logs check requires running worker service.

## Files Created/Modified
- `src/sps/fixtures/phase4.py` — added override-aware fixture selection helpers.
- `src/sps/workflows/permit_case/activities.py` — fixture lookup now uses helpers and logs fixture_case_id.
- `tests/m004_s03_fixture_override_test.py` — tests for override and default selection behavior.
