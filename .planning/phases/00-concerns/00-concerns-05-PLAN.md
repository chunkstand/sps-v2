---
phase: 00-concerns
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/m006_s01_document_package_test.py
  - tests/fixtures/*.py
autonomous: true
must_haves:
  truths:
    - "Document package workflow transitions to DOCUMENT_COMPLETE in tests"
    - "Package manifest and evidence registry behavior is validated end-to-end"
  artifacts:
    - path: "tests/m006_s01_document_package_test.py"
      provides: "document package end-to-end coverage"
  key_links:
    - from: "tests/m006_s01_document_package_test.py"
      to: "document package workflow"
      via: "workflow transition assertions"
      pattern: "DOCUMENT_COMPLETE"
---

<objective>
Restore end-to-end coverage for the document package workflow.

Purpose: Detect regressions in package/manifest/evidence behavior before release.
Output: Unskipped tests with valid fixtures.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@tests/m006_s01_document_package_test.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Unskip document package end-to-end tests</name>
  <files>tests/m006_s01_document_package_test.py</files>
  <action>
Remove skip markers and re-enable the document package scenarios called out in the concerns list (transition to DOCUMENT_COMPLETE, package/manifest readback, evidence registry retrieval). Update any outdated fixtures or constants used by these tests to align with current workflow behavior.
  </action>
  <verify>python -m pytest tests/m006_s01_document_package_test.py</verify>
  <done>Document package tests run and cover workflow transition + manifest/evidence checks.</done>
</task>

<task type="auto">
  <name>Task 2: Stabilize fixtures for document package flows</name>
  <files>tests/fixtures/*.py</files>
  <action>
Adjust or add fixtures required by document package tests so they pass deterministically (case setup, package artifacts, evidence registry entries). Keep fixtures narrowly scoped to these tests to avoid cross-suite side effects.
  </action>
  <verify>python -m pytest tests/m006_s01_document_package_test.py</verify>
  <done>Tests pass consistently without external dependencies or manual setup.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/m006_s01_document_package_test.py` passes.
</verification>

<success_criteria>
- Document package end-to-end tests are active and stable.
- Workflow transition and manifest/evidence behaviors are asserted.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-05-SUMMARY.md`
</output>
