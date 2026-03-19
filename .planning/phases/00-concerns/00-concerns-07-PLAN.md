---
phase: 00-concerns
plan: 07
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sps/auth/rbac.py
  - src/sps/api/templates/reviewer_console.html
  - src/sps/api/templates/ops/index.html
  - src/sps/api/static/ops.js
  - scripts/generate_release_bundle.py
  - tests/m003_s01_reviewer_api_boundary_test.py
  - tests/m008_s01_reviewer_queue_evidence_test.py
  - tests/m009_s01_dashboard_test.py
  - tests/m009_s02_release_bundle_test.py
  - tests/m010_s03_redaction_test.py
autonomous: false
must_haves:
  truths:
    - "Reviewer/ops/release auth model is consistent across API, UI, scripts, and tests"
    - "The chosen auth header is accepted everywhere it is required"
  artifacts:
    - path: "src/sps/auth/rbac.py"
      provides: "authoritative reviewer auth dependency"
    - path: "src/sps/api/templates/reviewer_console.html"
      provides: "reviewer UI auth header usage"
    - path: "src/sps/api/static/ops.js"
      provides: "ops UI auth header usage"
    - path: "scripts/generate_release_bundle.py"
      provides: "release tooling auth header usage"
  key_links:
    - from: "src/sps/auth/rbac.py"
      to: "src/sps/api/static/ops.js"
      via: "auth header contract"
      pattern: "Reviewer-Api-Key|Authorization"
---

<objective>
Reconcile reviewer/ops/release authentication across API, UI, scripts, and tests.

Purpose: Eliminate internal auth drift and prevent failing tests/runbooks.
Output: Single, consistent auth contract applied everywhere.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/auth/rbac.py
@src/sps/api/templates/reviewer_console.html
@src/sps/api/static/ops.js
@scripts/generate_release_bundle.py
</context>

<tasks>

<task type="checkpoint:decision" gate="blocking">
  <decision>Is X-Reviewer-Api-Key still supported, or fully deprecated in favor of JWT + mTLS?</decision>
  <context>This choice determines auth headers for reviewer/ops/release endpoints, UI clients, scripts, and tests.</context>
  <options>
    <option id="option-a">
      <name>Keep X-Reviewer-Api-Key supported</name>
      <pros>Minimizes breaking changes; aligns with existing tests and runbooks</pros>
      <cons>Delays full migration to service-principal/JWT model</cons>
    </option>
    <option id="option-b">
      <name>Deprecate X-Reviewer-Api-Key (JWT + mTLS only)</name>
      <pros>Clear security posture; aligns with service-principal model</pros>
      <cons>Requires updating all clients, tests, and runbooks immediately</cons>
    </option>
  </options>
  <decision_status>Chosen: Keep X-Reviewer-Api-Key supported (minimize breakage)</decision_status>
</task>

<task type="auto">
  <name>Task 1: Align auth dependency + header contract</name>
  <files>src/sps/auth/rbac.py</files>
  <action>
Update reviewer/ops/release auth dependency behavior to match the selected decision (either continue supporting X-Reviewer-Api-Key or enforce JWT + mTLS). Ensure error responses are consistent and the contract is documented in code comments where needed.
  </action>
  <verify>python -m pytest tests/m003_s01_reviewer_api_boundary_test.py</verify>
  <done>Auth dependency behavior matches the chosen header contract.</done>
</task>

<task type="auto">
  <name>Task 2: Update UI, scripts, and tests to match the decision</name>
  <files>src/sps/api/templates/reviewer_console.html, src/sps/api/templates/ops/index.html, src/sps/api/static/ops.js, scripts/generate_release_bundle.py, tests/m003_s01_reviewer_api_boundary_test.py, tests/m008_s01_reviewer_queue_evidence_test.py, tests/m009_s01_dashboard_test.py, tests/m009_s02_release_bundle_test.py, tests/m010_s03_redaction_test.py</files>
  <action>
Update reviewer console, ops UI, release bundle script, and relevant tests to send the correct auth headers. Remove or migrate any legacy header usage based on the decision. Ensure all tests referenced still pass without relying on mixed auth paths.
  </action>
  <verify>python -m pytest tests/m003_s01_reviewer_api_boundary_test.py tests/m008_s01_reviewer_queue_evidence_test.py tests/m009_s01_dashboard_test.py tests/m009_s02_release_bundle_test.py</verify>
  <done>All reviewer/ops/release surfaces and tests use one consistent auth contract.</done>
</task>

</tasks>

<verification>
Selected reviewer/ops/release tests pass with a single auth model.
</verification>

<success_criteria>
- Auth contract is consistent across API dependency, UI clients, scripts, and tests.
- No mixed header expectations remain.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-07-SUMMARY.md`
</output>
