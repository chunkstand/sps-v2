---
phase: 00-concerns
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sps/services/release_bundle_manifest.py
  - tests/services/test_release_bundle_manifest.py
autonomous: true
must_haves:
  truths:
    - "Release bundle generation fails when manifest entries reference missing files"
    - "Release bundle generation fails when artifacts lack artifact_id metadata"
  artifacts:
    - path: "src/sps/services/release_bundle_manifest.py"
      provides: "strict manifest validation with explicit errors"
    - path: "tests/services/test_release_bundle_manifest.py"
      provides: "coverage for missing file and missing artifact ID cases"
  key_links:
    - from: "src/sps/services/release_bundle_manifest.py"
      to: "ReleaseBundleManifestError"
      via: "missing entry guard"
      pattern: "ReleaseBundleManifestError"
---

<objective>
Make release bundle manifest validation strict and observable when artifacts are missing.

Purpose: Prevent silent data loss in release bundles.
Output: Manifest validation errors + tests for missing files/IDs.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/services/release_bundle_manifest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fail fast on missing manifest artifacts</name>
  <files>src/sps/services/release_bundle_manifest.py</files>
  <action>
Update build_release_bundle_components to treat missing entry paths and missing artifact IDs as hard errors. Collect missing items and raise ReleaseBundleManifestError with a list of missing paths and/or artifact IDs so callers can see exactly what failed. Preserve existing duplicate detection.
  </action>
  <verify>python -m pytest tests/services -k release_bundle_manifest</verify>
  <done>Manifest build raises explicit errors for missing files and missing artifact IDs.</done>
</task>

<task type="auto">
  <name>Task 2: Add manifest validation tests</name>
  <files>tests/services/test_release_bundle_manifest.py</files>
  <action>
Add unit tests that cover: missing path entries (manifest points to absent file), missing artifact_id metadata for a present file, and the happy path to ensure no regressions. Use temp directories and minimal files to keep tests fast.
  </action>
  <verify>python -m pytest tests/services -k release_bundle_manifest</verify>
  <done>Tests prove missing entries and missing IDs fail with explicit ReleaseBundleManifestError messages.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/services -k release_bundle_manifest` passes.
</verification>

<success_criteria>
- Missing release artifacts cause bundle generation to fail loudly.
- Test coverage exists for missing path and missing artifact ID scenarios.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-02-SUMMARY.md`
</output>
