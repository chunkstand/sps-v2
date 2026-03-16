# M009-ct4p0u/S02 — Research

**Date:** 2026-03-16

## Summary
S02 owns R024 (release bundle manifest generation + fail-closed gate). The codebase already contains `ReleaseBundle` and `ReleaseArtifact` ORM models plus the initial alembic table creation, but there are no API contracts, routes, or services for release bundles, and no release blocker endpoint. The CLI script (`scripts/generate_release_bundle.py`) does not exist yet, but there is an existing `tools/verify_package_manifest.py` that already validates `PACKAGE-MANIFEST.json` against disk contents and provides the exact fail-closed behavior we need for the “stale artifacts” gate.

The spec defines a release bundle manifest schema at `model/sps/contracts/release-bundle-manifest.schema.json` and mandates fail-closed behavior for missing/stale binding artifacts and unresolved high-risk blockers. The spec’s artifact contract matrix explicitly calls out release bundle manifest integrity + digest verification, while the decision register (Decision #85) defines the blocker query filters for contradictions and dissents. There is no existing helper for “high-risk surface” detection; dissent scope values are currently free-form and there are no `HIGH_RISK` or `AUTHORITY_BOUNDARY` constants in code, so we’ll need to implement suffix matching as specified and accept that the release blocker query depends on consistent scope strings.

## Recommendation
Implement S02 by adding an authenticated ops endpoint (`GET /api/v1/ops/release-blockers`) that returns open blocking contradictions and open high-risk dissents, plus a release bundle endpoint (`POST /api/v1/releases/bundles`) that persists `ReleaseBundle` + `ReleaseArtifact` rows. Reuse `tools/verify_package_manifest.py` inside the CLI to fail closed on hash/size mismatches; then call the blocker endpoint and fail closed on any blockers. Build the release manifest using the schema contract in `model/sps/contracts/release-bundle-manifest.schema.json`, and ensure `created_at` is set explicitly (no DB default).

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| PACKAGE-MANIFEST hash/size verification | `tools/verify_package_manifest.py` | Already implements exact fail-closed behavior with SHA/byte checks; avoids custom hashing code and keeps manifest validation consistent with CI. |

## Existing Code and Patterns
- `src/sps/db/models.py` — `ReleaseBundle`/`ReleaseArtifact` ORM models already exist; `created_at` has no server default, so API/CLI must set timestamps explicitly.
- `alembic/versions/02b39bad0a95_phase1_schema.py` — release bundle tables already created in Phase 1, no new migration needed for S02.
- `src/sps/api/routes/ops.py` — authenticated ops router pattern (via `require_reviewer_api_key`) that should host the release blocker endpoint.
- `src/sps/db/queries/ops_metrics.py` — query helper pattern for ops queries (release blocker queries can follow this style).
- `src/sps/api/routes/evidence.py` — example of POST route that persists a primary record with explicit timestamps + conflict handling.
- `tools/verify_package_manifest.py` — manifest verifier with detailed mismatch reporting and non-zero exit on failure.
- `model/sps/contracts/release-bundle-manifest.schema.json` — authoritative release bundle manifest contract (required fields and structure).

## Constraints
- Release gating must **fail closed** on missing/stale binding artifacts or blockers (Decision #84 + spec §10A). CLI must exit non-zero on any mismatch or open blocker.
- Release blockers are defined as: `ContradictionArtifact` with `blocking_effect=true` and `resolution_status=OPEN`, or `DissentArtifact` with `scope` ending in `HIGH_RISK` or `AUTHORITY_BOUNDARY` and `resolution_state=OPEN` (Decision #85).
- `/api/v1/ops/*` endpoints are authenticated via `require_reviewer_api_key` (S01 pattern); release blocker endpoint should follow this.
- `ReleaseBundle.created_at` and `ReleaseArtifact.created_at` require explicit timestamps (no DB defaults).

## Common Pitfalls
- **Silent release gating** — forgetting `sys.exit(1)` on manifest mismatch or blockers would violate REL-001; reuse the manifest verifier and propagate non-zero exit.
- **Incorrect dissent scope filtering** — scope values are free-form today (no constants in code). Implement suffix matching exactly as specified and document the dependency on scope naming.

## Open Risks
- The release bundle manifest requires version fields (spec/app/schema/model/policy/invariant/adapter). There are no existing sources of these version strings in code; S02 must decide where to derive them (settings, spec files, or constants) and tests must pin expectations.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | `wshobson/agents@fastapi-templates` | available |
| FastAPI | `mindrally/skills@fastapi-python` | available |
| SQLAlchemy | `bobmatnyc/claude-mpm-skills@sqlalchemy-orm` | available |
| Alembic | `wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review` | available |
| PostgreSQL | `github/awesome-copilot@postgresql-table-design` | available |

## Sources
- Release bundle manifest contract (source: [model/sps/contracts/release-bundle-manifest.schema.json](model/sps/contracts/release-bundle-manifest.schema.json))
- Release bundle artifact contract matrix + fail-closed rules (source: [specs/sps/build-approved/spec.md](specs/sps/build-approved/spec.md))
- Manifest verification helper (source: [tools/verify_package_manifest.py](tools/verify_package_manifest.py))
- Ops router pattern + auth dependency (source: [src/sps/api/routes/ops.py](src/sps/api/routes/ops.py))
- Release bundle ORM models (source: [src/sps/db/models.py](src/sps/db/models.py))
