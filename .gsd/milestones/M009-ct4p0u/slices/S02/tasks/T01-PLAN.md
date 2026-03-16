---
estimated_steps: 4
estimated_files: 4
---

# T01: Add release blocker queries and release bundle API

**Slice:** S02 — Release Bundle and Blocker Gates
**Milestone:** M009-ct4p0u

## Description
Implement blocker queries and API endpoints for release gating and bundle persistence so the CLI can fail closed and store bundles.

## Steps
1. Add query helpers for open blocking contradictions and high-risk/authority-boundary dissents with scope suffix matching.
2. Build a release blocker service response and wire `GET /api/v1/ops/release-blockers` behind reviewer API key auth.
3. Add release bundle request/response contracts and implement `POST /api/v1/releases/bundles` to persist bundle + artifact rows with explicit timestamps.
4. Add logging/error responses that surface blocker details and invalid artifact references.

## Must-Haves
- [ ] Blocker query filters match Decision #85 and return actionable IDs/scopes.
- [ ] Release bundle POST persists `ReleaseBundle` + `ReleaseArtifact` rows with explicit `created_at` values.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- `curl -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" http://localhost:8000/api/v1/ops/release-blockers` (when running locally)

## Observability Impact
- Signals added/changed: release blocker API response payloads + release bundle persistence logs
- How a future agent inspects this: query `release_bundles`/`release_artifacts` tables and call `/api/v1/ops/release-blockers`
- Failure state exposed: blocker list contents and API error messages for invalid references

## Inputs
- `src/sps/db/models.py` — existing ReleaseBundle/ReleaseArtifact/Contradiction/Dissent models
- Decision #85 blocker scope definition

## Expected Output
- `src/sps/db/queries/release_blockers.py` — blocker query helpers
- `src/sps/services/release_blockers.py` — response assembly
- `src/sps/api/routes/ops.py` — new blockers endpoint
- `src/sps/api/routes/releases.py` — release bundle POST route
