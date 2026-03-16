# M007-b2t1rz — Research
**Date:** 2026-03-16

## Summary
Phase 7 has no submission/tracking/manual fallback implementation yet: there are no DB models or migrations for `SubmissionAttempt`, `ExternalStatusEvent`, or `ManualFallbackPackage`, and the `PermitCaseWorkflow` stops at `APPROVED_FOR_SUBMISSION`. The codebase already provides the idempotent-activity and evidence registry patterns needed to implement receipt persistence, plus fixture-loading conventions (Phase 6) that can be reused for Phase 7 status-map fixtures. The most immediate risk is wiring submission-side effects directly into the workflow without the idempotent activity + evidence registry pattern, which would violate deterministic + replay-safe constraints.

Primary recommendation: establish the data foundation first (models + migrations + schemas where missing), then implement a single idempotent submission activity that produces a `SubmissionAttempt` and receipt EvidenceArtifact via `EvidenceRegistry`, and only then wire workflow transitions (`APPROVED_FOR_SUBMISSION → SUBMISSION_PENDING → SUBMITTED` or `MANUAL_SUBMISSION_REQUIRED`). Status normalization should be implemented as a pure mapping layer backed by fixtures (new `specs/.../fixtures/phase7`) with fail-closed behavior for unmapped statuses.

## Recommendation
Follow the existing Phase 6/Phase 5 pattern: add Phase 7 fixtures under `specs/sps/build-approved/fixtures/phase7` with a loader module, implement idempotent activities in `permit_case/activities.py` (similar logging + failpoint structure) for submission attempt and status normalization persistence, and gate workflow progress through the existing guard system in `apply_state_transition`. Prove early that receipt artifacts are stored via `EvidenceRegistry` and that duplicate submission attempts return the same attempt/receipt without extra side effects.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Receipt artifact storage + sha256 validation | `EvidenceRegistry` + `S3Storage` (`src/sps/documents/registry.py`, `src/sps/storage/s3.py`) | Already enforces integrity checks and stable IDs; avoids custom S3 logic and keeps evidence provenance consistent. |
| Fixture-backed data selection | Phase 6 fixture loader (`src/sps/fixtures/phase6.py`) | Establishes fixture placement + override patterns; reuse to keep provenance traceable to spec package. |
| Idempotent, deterministic side effects | Activity patterns in `persist_submission_package` + `apply_state_transition` | Ensures Temporal retries are safe; matches existing logging, request_id, and idempotency expectations. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/workflow.py` — Workflow currently stops after `APPROVED_FOR_SUBMISSION`; add submission/tracking/manual fallback paths using activity I/O only.
- `src/sps/workflows/permit_case/activities.py` — Idempotent activity + logging + failpoint pattern; use this structure for submission attempt + status persistence.
- `src/sps/fixtures/phase6.py` — Fixture dataset loading + case_id override pattern to mirror for Phase 7 status map fixtures.
- `src/sps/documents/registry.py` and `src/sps/storage/s3.py` — EvidenceRegistry + S3 storage used for documents/manifest; reuse for receipt artifacts.
- `src/sps/evidence/models.py` — `ArtifactClass.RECEIPT` already defined; wire receipts into evidence registry for SubmissionAttempt.
- `model/sps/model.yaml` — Canonical fields for `SubmissionAttempt`, `ExternalStatusEvent`, `ManualFallbackPackage` exist, but DB models/migrations are missing.

## Constraints
- Workflow code must remain deterministic; all I/O via activities (Temporal replay-safe rule).
- State transitions are mediated by `apply_state_transition` with idempotent ledger semantics; new transitions must use this guard path.
- Evidence artifacts must be persisted with sha256 integrity checks and stable IDs (EvidenceRegistry).

## Common Pitfalls
- **Non-idempotent submission adapters** — Duplicate adapter calls on Temporal retries can double-submit; require idempotency keys and persistence-first semantics.
- **Status mapping fail-open** — Unmapped statuses must fail closed and be observable; avoid implicit fallback to generic statuses.
- **Missing receipt persistence** — Storing a tracking ID without a receipt artifact breaks auditability; ensure EvidenceArtifact is always recorded.

## Open Risks
- Fixture placement for status maps is undecided; if not aligned with spec fixtures, provenance becomes ambiguous.
- Model/schemas may be incomplete (`SubmissionAttempt` contract schema is missing under `model/sps/contracts/`).

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (npx skills add wshobson/agents@temporal-python-testing) |
| FastAPI | wshobson/agents@fastapi-templates | available (npx skills add wshobson/agents@fastapi-templates) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (npx skills add bobmatnyc/claude-mpm-skills@sqlalchemy-orm) |

## Sources
- Submission attempt + manual fallback + tracking requirements (source: [specs/sps/build-approved/spec.md](specs/sps/build-approved/spec.md))
- Submission adapter request contract (source: [model/sps/contracts/submission-adapter-request.schema.json](model/sps/contracts/submission-adapter-request.schema.json))
- Canonical data model fields (source: [model/sps/model.yaml](model/sps/model.yaml))
- Workflow stopping point and transition patterns (source: [src/sps/workflows/permit_case/workflow.py](src/sps/workflows/permit_case/workflow.py))
- Guard + idempotent activity patterns (source: [src/sps/workflows/permit_case/activities.py](src/sps/workflows/permit_case/activities.py))
- Fixture loading conventions (source: [src/sps/fixtures/phase6.py](src/sps/fixtures/phase6.py))
- Evidence registry and S3 storage integrity checks (source: [src/sps/documents/registry.py](src/sps/documents/registry.py), [src/sps/storage/s3.py](src/sps/storage/s3.py))
- Receipt evidence class availability (source: [src/sps/evidence/models.py](src/sps/evidence/models.py))
