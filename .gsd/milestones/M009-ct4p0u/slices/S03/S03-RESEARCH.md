# M009-ct4p0u / S03 — Research

**Date:** 2026-03-16

## Summary
This slice owns R025 (rollback rehearsal evidence) and R026 (post-release validation template). The codebase currently has no rollback rehearsal endpoint or artifact class for rollback rehearsal in `ArtifactClass`. Evidence storage is already implemented via the evidence registry (S3 + `evidence_artifacts` table) and release APIs are authenticated with the reviewer API key. The quickest, lowest-risk path is to add a release rollback rehearsal endpoint that creates a `ROLLBACK_REHEARSAL` evidence artifact (class enum addition), uses existing evidence storage conventions, and stores provenance fields expected by the spec.

The post-release validation requirement is currently satisfied only by a runbook template. There is no existing file under `runbooks/sps/post-release-validation.md`, but there is a `release-rollback.md` runbook with the established format and metadata header. We should mirror that style and include explicit stage-gated checks (canary → staged rollout), referencing the spec requirement for a post-release validation report before proceeding to the next stage.

## Recommendation
Add a `ROLLBACK_REHEARSAL` entry to `ArtifactClass`, implement `POST /api/v1/releases/rollbacks/rehearsals` in the releases router (reuse reviewer API key auth), and create the evidence artifact in S3 + Postgres using the same checksum/URI rules as evidence artifacts elsewhere. Use `RetentionClass.RELEASE_EVIDENCE` and provenance fields like `release_id`, `rehearsal_id`, `trigger`, and `verification_evidence`. Create `runbooks/sps/post-release-validation.md` using the same runbook metadata header and include explicit stage-gated validation steps with required post-release validation report fields.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Evidence storage + checksum validation | Evidence registry patterns (`sps.api.routes.evidence`, `sps.documents.registry`) | Standardizes object keys, checksum validation, and evidence metadata persistence |
| Release API auth | `require_reviewer_api_key` dependency on release routes | Keeps release/rollback endpoints aligned with existing protected release surfaces |
| Runbook formatting | Existing `runbooks/sps/*.md` headers (e.g., `release-rollback.md`) | Ensures runbooks are consistent with existing metadata expectations |

## Existing Code and Patterns
- `src/sps/evidence/models.py` — `ArtifactClass` enum (needs `ROLLBACK_REHEARSAL`) and retention classes.
- `src/sps/api/routes/evidence.py` — evidence register/upload patterns for checksum validation and metadata persistence.
- `src/sps/documents/registry.py` — evidence registry helper for S3 writes + sha256 validation, used by workflow artifacts.
- `src/sps/api/routes/releases.py` — release API router with reviewer API key auth and structured error handling.
- `runbooks/sps/release-rollback.md` — runbook metadata header and action/criteria layout to mirror.

## Constraints
- Release/rollback APIs are gated by reviewer API key (`require_reviewer_api_key`), so the new rehearsal endpoint should follow the same dependency.
- Evidence artifacts require sha256 checksums and S3 URIs; the rollback rehearsal artifact must follow the existing evidence registry’s checksum + storage conventions.
- Spec requires rollback rehearsal evidence for critical paths and a post-release validation report before next rollout stage (binding artifact rules).

## Common Pitfalls
- **Forgetting to extend `ArtifactClass`** — evidence register validation will reject new artifact classes; add `ROLLBACK_REHEARSAL` before wiring the endpoint.
- **Skipping S3 content upload or checksum verification** — evidence artifacts rely on verified sha256 content; use the same checksum/URI pattern as other evidence artifacts.

## Open Risks
- The rehearsal endpoint will need content payloads for evidence storage; decide whether to accept raw content or accept pre-uploaded artifact metadata (the existing evidence API supports both patterns, but tests/runbook must match).

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available (npx skills add wshobson/agents@fastapi-templates) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (npx skills add bobmatnyc/claude-mpm-skills@sqlalchemy-orm) |
| Postgres | supabase/agent-skills@supabase-postgres-best-practices | available (npx skills add supabase/agent-skills@supabase-postgres-best-practices) |
| MinIO/S3 | vm0-ai/vm0-skills@minio | available (npx skills add vm0-ai/vm0-skills@minio) |

## Sources
- Rollback/post-release artifact requirements (source: `specs/sps/build-approved/spec.md`)
- Evidence artifact enum + retention classes (source: `src/sps/evidence/models.py`)
- Evidence register/upload patterns (source: `src/sps/api/routes/evidence.py`)
- S3 evidence registry helper (source: `src/sps/documents/registry.py`)
- Runbook formatting reference (source: `runbooks/sps/release-rollback.md`)
