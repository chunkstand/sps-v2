# M006-h7v2qk: Phase 6 — document and submission package generation — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement Phase 6 document and submission package generation. This milestone consumes Project, JurisdictionResolution, RequirementSet, ComplianceEvaluation, and IncentiveAssessment outputs to produce a sealed SubmissionPackage with documents, manifest, and artifact digests. Document generation uses fixture templates and a deterministic generator, wired into PermitCaseWorkflow with authoritative Postgres persistence.

## Why This Milestone

Without a sealed package and document artifacts, SPS cannot progress to reviewer approval or submission workflows. Phase 6 establishes the evidence-backed document layer and ensures package manifests and digests are generated deterministically to support later submission and release gates.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run a PermitCaseWorkflow that advances through DOCUMENT_COMPLETE and persists a SubmissionPackage with manifest and artifact digests.
- Retrieve generated document artifacts and see them referenced in the package manifest.

### Entry point / environment

- Entry point: `./.venv/bin/uvicorn sps.api.main:app` + `./.venv/bin/python -m sps.workflows.worker`
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal, MinIO (evidence storage)

## Completion Class

- Contract complete means: SubmissionPackage, manifest, and document artifacts validate against spec/model shapes with required digests.
- Integration complete means: a real workflow run generates documents and persists a sealed package in Postgres.
- Operational complete means: tests and runbook prove end-to-end behavior against docker-compose Postgres/Temporal/MinIO.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A workflow run produces document artifacts and a SubmissionPackage with manifest/digest fields populated.
- Package artifacts are stored and retrievable via the evidence registry.
- The above is proven against live docker-compose Postgres + Temporal + MinIO.

## Risks and Unknowns

- Template fidelity risk — fixture templates may require changes once real portal formats are known.
- Digest integrity risk — deterministic hashing must be stable across runs and environments.

## Existing Codebase / Prior Art

- `src/sps/storage/s3.py` — evidence storage adapter used for document artifact bytes.
- `src/sps/api/routes/evidence.py` — evidence registry surface for document artifacts.
- `src/sps/workflows/permit_case/workflow.py` — orchestration to extend with document generation.
- `model/sps/model.yaml` — SubmissionPackage and DocumentArtifact definitions.
- `specs/sps/build-approved/spec.md` — normative requirement F-006 and package contract rules.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R015 — Submission package generation (F-006) is implemented with manifest + digests.

## Scope

### In Scope

- Fixture-based document templates and deterministic generator.
- SubmissionPackage creation with manifest and artifact digests.
- Document generation activity wired into PermitCaseWorkflow.
- Evidence registry storage for document artifacts.
- Integration tests + operator runbook proving end-to-end workflow progression.

### Out of Scope / Non-Goals

- External document generation services.
- Submission adapters, tracking, or manual fallback.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Workflow code remains deterministic; all I/O via activities.
- Authoritative state mutation remains orchestrator/guard mediated.
- Evidence artifacts must use stable IDs and integrity checks.

## Integration Points

- Postgres — authoritative persistence for SubmissionPackage and document metadata.
- Temporal — workflow orchestration and activity execution.
- MinIO/S3 — document artifact storage via evidence registry.

## Open Questions

- Where should document templates live to keep provenance clear and auditable? — decide during planning.
