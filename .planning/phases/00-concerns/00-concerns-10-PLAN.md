---
phase: 00-concerns
plan: 10
type: execute
wave: 2
depends_on:
  - "00-concerns-07"
  - "00-concerns-08"
  - "00-concerns-09"
files_modified:
  - scripts/generate_release_bundle.py
  - src/sps/api/templates/ops/index.html
  - src/sps/api/templates/reviewer_console.html
  - src/sps/api/static/ops.js
  - tests/m009_s02_release_bundle_test.py
  - tests/m009_s01_dashboard_test.py
autonomous: true
must_haves:
  truths:
    - "Release bundle generation succeeds end-to-end with the chosen auth model"
    - "Ops and reviewer UIs function with the chosen credentials flow"
  artifacts:
    - path: "scripts/generate_release_bundle.py"
      provides: "release bundle generation using authoritative package"
    - path: "src/sps/api/templates/ops/index.html"
      provides: "operator dashboard with working auth"
  key_links:
    - from: "scripts/generate_release_bundle.py"
      to: "src/sps/api/routes/ops.py"
      via: "release blocker calls"
      pattern: "release-blockers"
---

<objective>
Finish control-plane hardening: auth consistency + end-to-end release bundle generation + usable operator/reviewer surfaces.

Purpose: Make the operational layer reliable and testable.
Output: Working release bundle flow and operator/reviewer UX with consistent auth.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@scripts/generate_release_bundle.py
@src/sps/api/templates/ops/index.html
@src/sps/api/templates/reviewer_console.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Validate release bundle generation end-to-end</name>
  <files>scripts/generate_release_bundle.py, tests/m009_s02_release_bundle_test.py</files>
  <action>
Ensure generate_release_bundle.py uses the authoritative package/manifest and the chosen auth model from plan 07. Add or update tests to exercise release bundle generation end-to-end (manifest load → blocker checks → bundle creation) with deterministic fixtures.
  </action>
  <verify>python -m pytest tests/m009_s02_release_bundle_test.py</verify>
  <done>Release bundle generation succeeds end-to-end in tests with the correct auth model.</done>
</task>

<task type="auto">
  <name>Task 2: Make operator/reviewer UI flows usable</name>
  <files>src/sps/api/templates/ops/index.html, src/sps/api/templates/reviewer_console.html, src/sps/api/static/ops.js, tests/m009_s01_dashboard_test.py</files>
  <action>
Update ops and reviewer console UIs to match the chosen auth flow and ensure the fetch logic is aligned. Refresh dashboard tests to validate the updated credentials flow.
  </action>
  <verify>python -m pytest tests/m009_s01_dashboard_test.py</verify>
  <done>Ops and reviewer UIs work with the chosen credentials flow and tests pass.</done>
</task>

</tasks>

<verification>
Release bundle and dashboard tests pass with the chosen auth model.
</verification>

<success_criteria>
- Release bundle generation is validated end-to-end.
- Ops/reviewer surfaces are usable with consistent auth.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-10-SUMMARY.md`
</output>
