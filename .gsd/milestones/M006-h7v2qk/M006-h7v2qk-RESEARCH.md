# M006-h7v2qk — Research

**Date:** 2026-03-15

## Summary
Phase 6 needs a new document generation activity, SubmissionPackage persistence, and manifest/digest sealing wired into PermitCaseWorkflow between INCENTIVES_COMPLETE and REVIEW_PENDING. The current workflow and transition guard stop at INCENTIVES_COMPLETE, and there are no SubmissionPackage tables or fixtures in the codebase yet. Evidence storage and integrity checks already exist (EvidenceArtifact registry + S3 storage) and should be reused to store document artifacts and the manifest so that digests can be validated deterministically.

Primary recommendation: follow the existing fixture and persistence patterns used in Phase 4/5. Add Phase 6 fixtures under `specs/sps/build-approved/fixtures/phase6`, introduce typed fixture loader + case_id override logic, implement a `persist_submission_package` (and document generation) activity that registers EvidenceArtifacts + uploads content, and extend the transition guard to enforce presence/freshness of the package when advancing to DOCUMENT_COMPLETE. This keeps workflow determinism intact and aligns with the evidence registry’s checksum enforcement.

## Recommendation
Reuse the activity-driven, idempotent persistence pattern from Phase 4/5: load fixtures, normalize case_id, persist rows in a single transaction, and rely on EvidenceArtifact registry + S3 storage for document bytes and digests. Wire the workflow to run document generation after incentives and before review, then update the guard in `apply_state_transition` for DOCUMENT transitions. This avoids non-deterministic workflow I/O and preserves the established ledger + guard behavior.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Evidence storage + integrity | `src/sps/api/routes/evidence.py`, `src/sps/storage/s3.py` | Already enforces sha256 checksums, stable IDs, and S3 object-key layout. |
| Case-state guard + ledger | `apply_state_transition` in `src/sps/workflows/permit_case/activities.py` | Centralized fail-closed guard with idempotent ledger; new document checks should live here. |
| Fixture loading + override | `src/sps/fixtures/phase4.py`, `src/sps/fixtures/phase5.py` | Provides a proven pattern for spec-sourced fixture datasets and case_id rewrites. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/workflow.py` — Workflow currently advances through INCENTIVES_COMPLETE and stops; add document generation + DOCUMENT_COMPLETE transition here.
- `src/sps/workflows/permit_case/activities.py` — Transition guard and persistence activities; extend for document package persistence and document guard checks.
- `src/sps/db/models.py` — No SubmissionPackage or document tables yet; PermitCase has `current_package_id` that should be set during package creation.
- `model/sps/contracts/submission-package.schema.json` — Contract for SubmissionPackage fields; use for validation.
- `src/sps/api/routes/evidence.py` + `src/sps/storage/s3.py` — Evidence registry and S3 adapter with checksum enforcement.
- `src/sps/fixtures/phase5.py` — Fixture loader + case_id override pattern to reuse for phase6 fixtures.
- `specs/sps/build-approved/spec.md` — Defines SubmissionPackage fields and state transitions (DOCUMENT_PENDING/DOCUMENT_COMPLETE).

## Constraints
- Workflow determinism: all I/O must be in activities, not in workflow code (`PermitCaseWorkflow` and activities pattern).
- Guarded transitions are the only authoritative state mutation path (`apply_state_transition` writes ledger + updates case_state).
- Evidence registry expects sha256 checksums and stable `ART-<ULID>` IDs with deterministic object keys.
- SubmissionPackage is required in the model export, but no DB table exists yet (migration needed).

## Common Pitfalls
- **Non-deterministic document generation** — avoid runtime randomness; derive IDs and digests deterministically from fixture inputs.
- **Digest mismatch between manifest and artifact content** — compute sha256 from final bytes before registration; use evidence registry checksum enforcement as the source of truth.
- **Skipping guard updates for DOCUMENT transitions** — without guard checks, workflows can advance without a sealed package; extend `apply_state_transition` for DOCUMENT_COMPLETE.
- **Forgetting to persist current_package_id** — PermitCase has `current_package_id`; ensure it is set when a package becomes active.

## Open Risks
- Template provenance placement is still undecided; choose a storage path consistent with Phase 4/5 fixtures and capture provenance metadata so audit trails remain clear.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| FastAPI | wshobson/agents@fastapi-templates | available |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available |
| Alembic | wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review | available |
| MinIO | vm0-ai/vm0-skills@minio | available |

## Sources
- SubmissionPackage fields and state transitions (source: `specs/sps/build-approved/spec.md`)
- SubmissionPackage contract schema (source: `model/sps/contracts/submission-package.schema.json`)
- Evidence registry + S3 adapter (source: `src/sps/api/routes/evidence.py`, `src/sps/storage/s3.py`)
- Workflow + guard patterns (source: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`)
- Fixture loading patterns (source: `src/sps/fixtures/phase5.py`)
