---
estimated_steps: 5
estimated_files: 3
---

# T01: Add fixture override selection for Phase 4 activities

**Slice:** S03 — End-to-end docker-compose proof (API + worker + Postgres + Temporal)
**Milestone:** M004-lp1flz

## Description
Add a test/runbook-only override that allows Phase 4 fixture lookup to target the fixture case_id while persisting artifacts under the runtime intake case_id. This preserves the spec-derived intake contract while enabling the operational runbook to reach RESEARCH_COMPLETE.

## Steps
1. Extend `src/sps/fixtures/phase4.py` with a helper that resolves the fixture case_id from `SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE` (fallback to the requested case_id) and returns fixtures with case_id rewritten to the runtime case_id.
2. Update jurisdiction/requirements activities to use the helper and to log both the runtime case_id and the fixture case_id used for lookup.
3. Add `tests/m004_s03_fixture_override_test.py` to validate that the helper returns fixtures for the override case_id while preserving runtime case_id on the returned models.
4. Ensure override behavior is opt-in (env var unset = existing behavior).

## Must-Haves
- [ ] Fixture selection supports an env-gated override and preserves the runtime case_id on persisted artifacts.
- [ ] Activity logs surface both runtime and fixture case_ids when override is active.

## Verification
- `./.venv/bin/pytest tests/m004_s03_fixture_override_test.py`
- Tests confirm override selection + case_id rewrite with env var set, and default behavior with env var unset.

## Observability Impact
- Signals added/changed: activity logs include `fixture_case_id` alongside `case_id`.
- How a future agent inspects this: `docker compose logs worker | grep persist_jurisdiction_resolutions`.
- Failure state exposed: missing fixtures show `LookupError` with both case IDs for quick diagnosis.

## Inputs
- `src/sps/fixtures/phase4.py` — existing fixture loader and validator models.
- `src/sps/workflows/permit_case/activities.py` — current fixture lookup behavior.

## Expected Output
- `src/sps/fixtures/phase4.py` — helper for override-aware fixture selection.
- `src/sps/workflows/permit_case/activities.py` — updated fixture lookup + logs.
- `tests/m004_s03_fixture_override_test.py` — unit test covering override behavior.
