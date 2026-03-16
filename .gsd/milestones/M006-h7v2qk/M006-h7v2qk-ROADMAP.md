# M006-h7v2qk: Phase 6 — document and submission package generation

**Vision:** PermitCaseWorkflow emits a sealed SubmissionPackage with deterministic document artifacts, manifest, and digests that are persisted, retrievable, and ready for review/submission gating.

## Success Criteria
- A fixture-backed document generation run persists a SubmissionPackage with manifest + artifact digests and sets `permit_cases.current_package_id`.
- Generated document artifacts and the manifest are stored in the evidence registry and retrievable via API, with manifest references matching evidence digests.
- A live docker-compose workflow run advances to DOCUMENT_COMPLETE and proves package + artifact retrieval end-to-end.

## Key Risks / Unknowns
- Digest determinism across manifest + artifact bytes — a mismatch would invalidate sealed packages and block later submission.
- Template provenance placement — templates must be stored in a traceable, auditable location aligned with prior fixture strategy.

## Proof Strategy
- Digest determinism across manifest + artifact bytes → retire in S01 by proving integration tests that compute sha256 from final bytes and match evidence registry digests + manifest entries.
- Template provenance placement → retire in S01 by landing fixture templates under the spec fixture tree and loading them through a deterministic fixture loader.
- Live workflow wiring across Temporal/Postgres/MinIO → retire in S02 by running a docker-compose runbook that reaches DOCUMENT_COMPLETE and reads back package + evidence.

## Verification Classes
- Contract verification: pytest integration tests for document generation, package persistence, and manifest/digest validation.
- Integration verification: Temporal + Postgres + MinIO exercised via workflow run to DOCUMENT_COMPLETE.
- Operational verification: docker-compose runbook for end-to-end worker + API proof.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slice deliverables are complete and verified.
- Document generation, evidence registry, and package persistence are wired together in the workflow.
- The real entrypoints (`uvicorn` + worker) are exercised in docker-compose.
- Success criteria are re-checked against live behavior, not just artifacts.
- Final integrated acceptance scenario (DOCUMENT_COMPLETE with package/evidence readback) passes.

## Requirement Coverage
- Covers: R015
- Partially covers: none
- Leaves for later: R016, R017, R018, R019
- Orphan risks: none

## Slices
- [ ] **S01: Deterministic document artifacts + submission package persistence** `risk:high` `depends:[]`
  > After this: fixture-backed document generation persists a sealed SubmissionPackage with manifest/digests and evidence artifacts retrievable via API (proven by integration tests).
- [ ] **S02: Workflow document stage + end-to-end package runbook** `risk:medium` `depends:[S01]`
  > After this: a live docker-compose workflow run reaches DOCUMENT_COMPLETE and proves package + evidence retrieval end-to-end.

## Boundary Map
### S01 → S02
Produces:
- SubmissionPackage + DocumentArtifact ORM/migration and `permit_cases.current_package_id` updates.
- Phase 6 fixture templates + loader with deterministic case_id overrides.
- Document generation activity that registers evidence artifacts (documents + manifest) with sha256 digests.
- Package read surface for manifest + artifact references.

Consumes:
- nothing (first slice)
