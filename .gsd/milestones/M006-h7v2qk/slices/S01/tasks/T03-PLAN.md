---
estimated_steps: 7
estimated_files: 6
---

# T03: Wire document generation, workflow stage, and package read API
**Slice:** S01 — Deterministic document artifacts + submission package persistence
**Milestone:** M006-h7v2qk

## Description
Generate deterministic documents from Phase 6 templates, seal them into a manifest, persist the SubmissionPackage, and wire the workflow + API read surface. This completes the end-to-end path needed to prove R015 with real workflow execution and evidence retrieval.

## Steps
1. Implement `src/sps/documents/generator.py` to render deterministic document bytes from Phase 6 templates and build a manifest payload from final bytes.
2. Extend workflow activities to generate documents, register document + manifest evidence artifacts, and call the persistence activity.
3. Wire `PermitCaseWorkflow` to advance INCENTIVES_COMPLETE → DOCUMENT_COMPLETE using the document generation activity and guarded transition.
4. Add API response models and routes to fetch the current package and manifest for a case (linked evidence artifact IDs + digests).
5. Update `tests/m006_s01_document_package_test.py` with Temporal integration coverage for DOCUMENT_COMPLETE, manifest digest matching, evidence registry consistency, and API retrieval.
6. Run integration tests with `SPS_RUN_TEMPORAL_INTEGRATION=1`.

## Must-Haves
- [ ] Workflow reaches DOCUMENT_COMPLETE with a persisted SubmissionPackage and updated `permit_cases.current_package_id`.
- [ ] Manifest digest entries match evidence registry checksums; API readbacks return the same references.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m006_s01_document_package_test.py -k integration -v -s`

## Observability Impact
- Signals added/changed: document generation + package persistence logs (start/ok/error) with case_id, package_id, manifest_id.
- How a future agent inspects this: workflow logs, evidence metadata API, Postgres package tables, and case read endpoints.
- Failure state exposed: digest mismatch or missing evidence artifacts is logged with IDs and prevents DOCUMENT_COMPLETE transition.

## Inputs
- `src/sps/fixtures/phase6.py` — fixture templates + override logic.
- `src/sps/documents/registry.py` — evidence registration helper.

## Expected Output
- `src/sps/documents/generator.py` — deterministic document + manifest generation.
- `src/sps/workflows/permit_case/workflow.py` — document stage wiring to DOCUMENT_COMPLETE.
- `src/sps/api/routes/cases.py` + `src/sps/api/contracts/cases.py` — package/manifest read surfaces.
- `tests/m006_s01_document_package_test.py` — integration assertions for evidence + manifest determinism.
