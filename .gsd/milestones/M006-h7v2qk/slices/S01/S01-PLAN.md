# S01: Deterministic document artifacts + submission package persistence
**Goal:** Generate deterministic document artifacts from Phase 6 fixtures, seal them into a SubmissionPackage with manifest + digests, and persist the package so evidence artifacts are retrievable with matching checksums.
**Demo:** A fixture-backed document generation run stores document artifacts + manifest in the evidence registry, persists a SubmissionPackage with matching digests, sets `permit_cases.current_package_id`, and exposes package + manifest retrieval via API.

## Decomposition Rationale
We split the slice into three increments to control risk around determinism and persistence. First we add the Phase 6 fixture dataset plus contract models and tests to lock the deterministic inputs. Next we introduce schema + registry wiring to persist packages and evidence artifacts without touching workflow wiring yet. Finally we wire document generation into the workflow and API read surfaces, then complete the integration tests that assert digest determinism and evidence retrieval. This order isolates the highest-risk boundary (digest integrity) and ensures the tests prove the full package path once wiring is complete.

## Must-Haves
- Phase 6 fixture templates + loader (with case_id override) provide deterministic document bytes for tests and workflow runs.
- SubmissionPackage + DocumentArtifact persistence stores manifest + artifact digests and updates `permit_cases.current_package_id`.
- Document artifacts and manifest are stored as EvidenceArtifacts with sha256 digests computed from final bytes, and API retrieval returns manifest references that match the evidence registry.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m006_s01_document_package_test.py -k fixtures -v`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m006_s01_document_package_test.py -k integration -v -s`
- **Failure path check:** `pytest tests/m006_s01_document_package_test.py -k "digest_mismatch or invalid_template" -v` (validates structured error output for checksum failures and template rendering errors)

## Observability / Diagnostics
- Runtime signals: structured activity logs for document generation + package persistence (start/ok/error with case_id + package_id).
- Inspection surfaces: `submission_packages`, `document_artifacts`, `evidence_artifacts`, `permit_cases.current_package_id`, API package/manifest endpoints.
- Failure visibility: error logs include case_id/package_id/manifest_id and checksum mismatch details; evidence registry exposes stored checksums.
- Redaction constraints: do not log template content or rendered document bodies; log digests + IDs only.

## Integration Closure
- Upstream surfaces consumed: Phase 6 fixture loader, evidence registry + S3 storage adapter, guarded workflow state transitions.
- New wiring introduced in this slice: document generation activity + package persistence activity, workflow step to DOCUMENT_COMPLETE, package/manifest read API.
- What remains before the milestone is truly usable end-to-end: S02 docker-compose runbook proving DOCUMENT_COMPLETE in a live workflow.

## Tasks
- [x] **T01: Add Phase 6 fixtures, contracts, and test scaffolding** `est:2h`
  - Why: Locks deterministic inputs and test harness before persistence and workflow wiring.
  - Files: `specs/sps/build-approved/fixtures/phase6/*`, `src/sps/fixtures/phase6.py`, `src/sps/documents/contracts.py`, `tests/m006_s01_document_package_test.py`
  - Do: Add Phase 6 fixture dataset (templates + manifest fixture metadata); implement fixture loader with case_id override env; define document/manifest contract models aligned with spec; add tests validating fixture schema load and override selection plus placeholders for package persistence assertions.
  - Verify: `pytest tests/m006_s01_document_package_test.py -k fixtures -v`
  - Done when: Phase 6 fixtures load via tests, override selection is proven, and the test module defines the integration assertions that will pass after wiring.
- [x] **T02: Persist submission packages and evidence artifacts** `est:3h`
  - Why: Establishes the authoritative storage path for SubmissionPackage metadata + EvidenceArtifact digests.
  - Files: `src/sps/db/models.py`, `alembic/versions/*_submission_packages.py`, `src/sps/documents/registry.py`, `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/activities.py`
  - Do: Add SubmissionPackage + DocumentArtifact tables and migration; implement evidence registry helper that registers artifacts and uploads content with sha256 checks; add activity request/response contracts and persistence activity to store package rows, artifact rows, and update `permit_cases.current_package_id` in one transaction.
  - Verify: `pytest tests/m006_s01_document_package_test.py -k persistence -v`
  - Done when: Package persistence activity stores rows + evidence artifacts with digests, and tests can assert DB + evidence metadata without workflow wiring.
- [x] **T03: Wire document generation, workflow stage, and package read API** `est:4h`
  - Why: Completes the end-to-end path needed to prove R015 with real workflow and API retrieval.
  - Files: `src/sps/documents/generator.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/api/routes/cases.py`, `src/sps/api/contracts/cases.py`, `tests/m006_s01_document_package_test.py`
  - Do: Implement deterministic document generation from Phase 6 templates; create manifest payload from final bytes and register document + manifest evidence artifacts; call persistence activity; wire workflow to advance INCENTIVES_COMPLETE → DOCUMENT_COMPLETE; add package/manifest read endpoints; update integration tests to assert digest determinism, evidence registry consistency, and API readbacks.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m006_s01_document_package_test.py -k integration -v -s`
  - Done when: The workflow reaches DOCUMENT_COMPLETE with a persisted SubmissionPackage, evidence artifacts match manifest digests, and API readbacks succeed in tests.

## Files Likely Touched
- `specs/sps/build-approved/fixtures/phase6/*`
- `src/sps/fixtures/phase6.py`
- `src/sps/documents/contracts.py`
- `src/sps/documents/registry.py`
- `src/sps/documents/generator.py`
- `src/sps/db/models.py`
- `alembic/versions/*_submission_packages.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/api/routes/cases.py`
- `src/sps/api/contracts/cases.py`
- `tests/m006_s01_document_package_test.py`
