# Codebase Concerns

**Analysis Date:** 2026-03-17

## Tech Debt

**Release bundle manifest silently skips missing artifacts:**
- Issue: Missing files or missing `artifact_id` values are silently ignored while building release artifacts.
- Files: `src/sps/services/release_bundle_manifest.py`
- Impact: Release bundles can ship without expected artifacts or digests, and missing content is not surfaced until downstream validation.
- Fix approach: Fail fast when `path.exists()` is false or `artifact_id` is missing, or return a structured list of missing entries and require callers to handle it.

**Monolithic workflow activities module:**
- Issue: The permit case workflow activity file is ~2.6k lines with many branching rules in a single module.
- Files: `src/sps/workflows/permit_case/activities.py`
- Impact: High risk of regressions when modifying transition logic; review and test scope is broad for small changes.
- Fix approach: Extract state transition handlers into dedicated modules (per state or per domain action) and add focused unit tests per handler.

**Large API routes module:**
- Issue: Single file holds many endpoints, DTO mapping helpers, and query logic.
- Files: `src/sps/api/routes/cases.py`
- Impact: Hard to reason about API behavior and error handling consistency; onboarding and change review cost increases.
- Fix approach: Split routes by domain (`cases`, `documents`, `submission`) and move row-to-response mappers to a dedicated module.

## Known Bugs

**Manifest endpoint returns a synthetic payload:**
- Symptoms: `/cases/{case_id}/manifest` responds with hardcoded `target_portal_family` and empty `required_attachments` instead of the persisted manifest.
- Files: `src/sps/api/routes/cases.py`
- Trigger: Any call to GET `/cases/{case_id}/manifest` after package creation.
- Workaround: None in API; use direct artifact retrieval from the evidence store if available.

**Workflow + evidence registry integration unimplemented (tests skipped):**
- Symptoms: Workflow does not advance to `DOCUMENT_COMPLETE` and evidence registry readback tests are skipped.
- Files: `tests/m006_s01_document_package_test.py`
- Trigger: Running integration tests for document package workflows.
- Workaround: Manual workflow execution and DB inspection; tests are marked `@pytest.mark.skip`.

## Security Considerations

**Legacy reviewer API key bypasses JWT + mTLS guard:**
- Risk: `X-Reviewer-Api-Key` grants reviewer/ops/release roles without JWT validation or mTLS signal checks.
- Files: `src/sps/auth/rbac.py`
- Current mitigation: Logging of legacy usage only.
- Recommendations: Remove legacy key auth or scope it to a restricted role, enforce mTLS for all non-public routes, and rotate key regularly with audit alerts.

## Performance Bottlenecks

**Unbounded list queries in case/review endpoints:**
- Problem: Multiple endpoints load full row sets with `.all()` without pagination or limits.
- Files: `src/sps/api/routes/cases.py`, `src/sps/api/routes/reviews.py`
- Cause: ORM queries do not apply `limit`/`offset` and responses return full lists.
- Improvement path: Add pagination params and default limits; enforce ordering and server-side caps.

## Fragile Areas

**Override logic can bypass contradiction checks:**
- Files: `src/sps/workflows/permit_case/activities.py`
- Why fragile: Transition behavior depends on override validation ordering; a small change can unintentionally bypass contradiction enforcement.
- Safe modification: Add focused tests around override + contradiction interactions before refactors.
- Test coverage: No targeted unit tests found for override/contradiction interplay.

## Scaling Limits

**Not detected.**

## Dependencies at Risk

**Not detected.**

## Missing Critical Features

**Manifest retrieval is placeholder-only:**
- Problem: Manifest response is synthesized instead of reading the stored manifest artifact.
- Blocks: Clients cannot verify exact manifest contents or required attachments from the source of truth.
- Files: `src/sps/api/routes/cases.py`

## Test Coverage Gaps

**Document package workflow integration coverage missing:**
- What's not tested: Workflow advancement to `DOCUMENT_COMPLETE` and evidence registry readback.
- Files: `tests/m006_s01_document_package_test.py`
- Risk: Package persistence and manifest integrity regressions can slip without detection.
- Priority: High

---

*Concerns audit: 2026-03-17*
