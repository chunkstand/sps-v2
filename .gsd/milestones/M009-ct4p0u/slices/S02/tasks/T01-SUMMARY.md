---
id: T01
parent: S02
milestone: M009-ct4p0u
provides:
  - Release blocker query + API response surface and release bundle POST persistence
key_files:
  - src/sps/db/queries/release_blockers.py
  - src/sps/services/release_blockers.py
  - src/sps/api/routes/ops.py
  - src/sps/api/routes/releases.py
  - tests/m009_s02_release_bundle_test.py
key_decisions:
  - None
patterns_established:
  - Release bundle API validates artifact digest references before persistence
observability_surfaces:
  - GET /api/v1/ops/release-blockers response payload + release_bundle.created/invalid_artifacts logs
duration: 1.5h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add release blocker queries and release bundle API

**Added release blocker queries + response assembly and a reviewer-authenticated release bundle POST that persists bundle/artifact rows with explicit timestamps.**

## What Happened
- Added release blocker query helpers and response models that filter open blocking contradictions and suffix-scoped dissents.
- Wired `GET /api/v1/ops/release-blockers` behind reviewer API key auth with snapshot logging.
- Implemented `POST /api/v1/releases/bundles` with digest reference validation, explicit `created_at` handling, and conflict/error logging.
- Added integration tests covering blockers filtering, bundle persistence, and invalid digest errors.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- Not run: `curl -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" http://localhost:8000/api/v1/ops/release-blockers` (requires live server)

## Diagnostics
- Query blockers via `GET /api/v1/ops/release-blockers` (response includes blocker IDs/scopes).
- Release bundle errors surface `artifact_digest_mismatch` with missing/unknown IDs; logs include `release_bundle.invalid_artifacts` and `release_bundle.created`.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/db/queries/release_blockers.py` — query helpers for contradiction/dissent blockers.
- `src/sps/services/release_blockers.py` — response models + builder for blockers API.
- `src/sps/api/routes/ops.py` — release blockers endpoint wiring.
- `src/sps/api/routes/releases.py` — release bundle POST endpoint and validation.
- `src/sps/api/main.py` — router registration for releases.
- `tests/m009_s02_release_bundle_test.py` — integration coverage for blockers + bundles.
