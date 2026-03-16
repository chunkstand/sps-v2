# S02: Release Bundle and Blocker Gates

**Goal:** Persist release bundles with artifact digests and provide fail-closed release gating via blockers API + CLI.
**Demo:** Operator runs `python scripts/generate_release_bundle.py` for a clean bundle, sees success. Re-running with a hash mismatch or open blocking contradiction causes exit 1 with a fail-closed error.

## Must-Haves
- Release blocker API returns open blocking contradictions and high-risk/authority-boundary dissents under reviewer auth.
- Release bundle API persists `ReleaseBundle` + `ReleaseArtifact` records with explicit timestamps and returns bundle metadata.
- CLI validates `PACKAGE-MANIFEST.json` via existing verifier, checks blockers endpoint, and fails closed on mismatch/blockers before posting bundle.
- Verification covers success + failure paths via pytest + runbook script.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
- `bash scripts/verify_m009_s02.sh --failure-paths`
- `curl -H "X-Reviewer-Api-Key: $SPS_REVIEWER_API_KEY" http://localhost:8000/api/v1/ops/release-blockers | jq '.blockers'`

## Observability / Diagnostics
- Runtime signals: release bundle create logs + API error payloads on blockers/manifest issues
- Inspection surfaces: `release_bundles`/`release_artifacts` tables, `GET /api/v1/ops/release-blockers`, CLI stderr/exit code
- Failure visibility: blocker list with IDs/scopes, manifest mismatch report, non-zero CLI exit
- Redaction constraints: none

## Integration Closure
- Upstream surfaces consumed: `ReleaseBundle`/`ReleaseArtifact` ORM models, `ContradictionArtifact`/`DissentArtifact` tables, `tools/verify_package_manifest.py`, release bundle manifest schema
- New wiring introduced in this slice: ops release-blockers endpoint + release bundle POST route + release bundle CLI
- What remains before the milestone is truly usable end-to-end: rollback rehearsal + post-release validation (S03)

## Tasks
- [x] **T01: Add release blocker queries and release bundle API** `est:2h`
  - Why: The CLI needs authoritative blocker data and a persistent bundle endpoint.
  - Files: `src/sps/db/queries/release_blockers.py`, `src/sps/services/release_blockers.py`, `src/sps/api/routes/ops.py`, `src/sps/api/routes/releases.py`
  - Do: Implement blocker queries with suffix matching, add API contracts, wire `GET /api/v1/ops/release-blockers` with reviewer auth, and add `POST /api/v1/releases/bundles` to persist bundles/artifacts with explicit timestamps.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s02_release_bundle_test.py`
  - Done when: Blocker endpoint returns scoped blockers and bundle POST persists rows with correct artifact refs.
- [x] **T02: Build release bundle CLI, manifest assembly, and runbook verification** `est:2h`
  - Why: Operators need a fail-closed release bundle generator with verified artifacts and blockers.
  - Files: `scripts/generate_release_bundle.py`, `src/sps/services/release_bundle_manifest.py`, `tests/m009_s02_release_bundle_test.py`, `scripts/verify_m009_s02.sh`, `tools/verify_package_manifest.py`
  - Do: Assemble the release manifest from `PACKAGE-MANIFEST.json`, enforce version fields via settings, call the blocker endpoint, exit non-zero on mismatch/blockers, and submit to the bundle API; add tests and the live verify script.
  - Verify: `bash scripts/verify_m009_s02.sh`
  - Done when: CLI succeeds on clean artifacts, fails closed on hash mismatch or open blockers, and tests cover both paths.

## Files Likely Touched
- `src/sps/db/queries/release_blockers.py`
- `src/sps/services/release_blockers.py`
- `src/sps/api/routes/ops.py`
- `src/sps/api/routes/releases.py`
- `src/sps/services/release_bundle_manifest.py`
- `scripts/generate_release_bundle.py`
- `tests/m009_s02_release_bundle_test.py`
- `scripts/verify_m009_s02.sh`
