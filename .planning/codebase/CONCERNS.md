# Codebase Concerns

**Analysis Date:** 2026-03-17

## Tech Debt

**Permit case workflow modules are monolithic:**
- Issue: Core workflow logic is concentrated in oversized files, making refactors risky and slowing review cycles.
- Files: `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/api/routes/cases.py`
- Impact: Higher regression risk, harder onboarding, and slower test iterations when changing workflow logic.
- Fix approach: Split by domain (state transitions, document packaging, submissions) and extract shared helpers into focused modules.

**Release bundle manifest silently drops missing artifacts:**
- Issue: Missing paths or missing artifact IDs are skipped without failing the bundle build.
- Files: `src/sps/services/release_bundle_manifest.py`
- Impact: Release bundles can be generated without expected artifacts, masking data integrity issues.
- Fix approach: Treat missing paths/artifact IDs as hard errors or emit explicit validation failures.

**Guard assertion mapping degrades silently:**
- Issue: Unknown guard assertion IDs return an empty invariant list and only log a warning.
- Files: `src/sps/guards/guard_assertions.py`
- Impact: Guard/invariant metadata can go missing without failing requests, reducing policy traceability.
- Fix approach: Fail fast for unknown IDs in production or enforce registry completeness in CI.

## Known Bugs

**Not detected**

## Security Considerations

**Default secrets enabled in settings:**
- Risk: Weak defaults can be used in non-dev environments if env vars are missing.
- Files: `src/sps/config.py`
- Current mitigation: None in code; relies on deployment configuration.
- Recommendations: Require explicit secrets in non-local envs; add startup validation for `auth_jwt_secret`, `reviewer_api_key`, and `s3_secret_key`.

## Performance Bottlenecks

**Reviewer independence metrics require table scans:**
- Problem: Count queries scan `review_decisions` for rolling 90-day windows without supporting indexes.
- Files: `src/sps/api/routes/reviews.py`, `src/sps/db/models.py`
- Cause: Queries filter by `decision_at`, `reviewer_id`, and `subject_author_id` without composite indexes.
- Improvement path: Add indexes on `review_decisions.decision_at` and `(reviewer_id, subject_author_id, decision_at)`.

## Fragile Areas

**Workflow signal delivery is best-effort with no retry:**
- Files: `src/sps/api/routes/reviews.py`, `src/sps/workflows/permit_case/workflow.py`
- Why fragile: Temporal signal failures leave DB state updated but workflow state stale.
- Safe modification: Add an outbox/retry mechanism or a reconciliation job that replays missed signals.
- Test coverage: Limited to integration tests; no automated recovery validation.

**Guard assertion registry relies on repo-relative path:**
- Files: `src/sps/guards/guard_assertions.py`, `invariants/sps/guard-assertions.yaml`
- Why fragile: Runtime packaging that omits the invariants directory fails with `FileNotFoundError`.
- Safe modification: Make the path configurable via settings and validate on startup.
- Test coverage: No unit tests covering missing registry behavior.

## Scaling Limits

**Not detected**

## Dependencies at Risk

**Not detected**

## Missing Critical Features

**Document package workflow coverage is gated by skipped tests:**
- Problem: Key workflow/API/evidence registry scenarios are explicitly skipped.
- Blocks: Confidence in document package end-to-end behavior.
- Files: `tests/m006_s01_document_package_test.py`

## Test Coverage Gaps

**Document package end-to-end tests skipped:**
- What's not tested: Workflow transition to `DOCUMENT_COMPLETE`, package/manifest API readback, evidence registry document retrieval.
- Files: `tests/m006_s01_document_package_test.py`
- Risk: Regressions in document package flow can ship undetected.
- Priority: High

---

*Concerns audit: 2026-03-17*
