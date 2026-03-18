---
phase: 01-runtime-slice
plan: 02
type: execute
wave: 2
depends_on:
  - "01-runtime-slice-01"
files_modified:
  - src/sps/adapters/*.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/documents/generator.py
  - tests/runtime_slice/test_end_to_end_slice.py
autonomous: true
must_haves:
  truths:
    - "Selected slice runs end-to-end with real adapter-backed data"
    - "Workflow completes through submission or manual fallback for the selected slice"
  artifacts:
    - path: "src/sps/adapters"
      provides: "concrete adapter implementations for the selected slice"
    - path: "tests/runtime_slice/test_end_to_end_slice.py"
      provides: "end-to-end slice coverage"
  key_links:
    - from: "src/sps/adapters"
      to: "src/sps/workflows/permit_case/activities.py"
      via: "concrete adapter usage"
      pattern: "adapter"
---

<objective>
Implement the first production slice end-to-end using real adapters.

Purpose: Replace fixture-backed runtime seams with a working, real slice.
Output: Concrete adapter implementations + end-to-end slice test.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/workflows/permit_case/activities.py
@src/sps/documents/generator.py
@src/sps/adapters
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement concrete adapters for the selected slice</name>
  <files>src/sps/adapters/*.py, src/sps/documents/generator.py, src/sps/workflows/permit_case/activities.py</files>
  <action>
Implement adapter logic for jurisdiction resolution, requirements/source, compliance evaluation, document compilation, submission/manual fallback, and status ingestion for the selected jurisdiction and submission path (Phaniville + manual submission). Use explicit placeholders for manual submission steps where external integrations would normally be required, but ensure artifacts and status events are still generated consistently. Ensure the workflow uses adapter outputs to populate evidence, package manifests, review decisions, and status events.
  </action>
  <verify>python -m pytest tests/runtime_slice/test_end_to_end_slice.py</verify>
  <done>The selected slice produces real data and completes through submission or manual fallback.</done>
</task>

<task type="auto">
  <name>Task 2: Add an end-to-end slice test</name>
  <files>tests/runtime_slice/test_end_to_end_slice.py</files>
  <action>
Create an end-to-end test that runs the selected slice through intake → jurisdiction → requirements → compliance → package generation → review → submission/manual fallback → status tracking → resubmission → approval artifacts. Use real adapter outputs (including placeholders for manual submission) and assert the expected workflow state transitions and artifacts.
  </action>
  <verify>python -m pytest tests/runtime_slice/test_end_to_end_slice.py</verify>
  <done>End-to-end slice test passes with adapter-backed data.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/runtime_slice/test_end_to_end_slice.py` passes.
</verification>

<success_criteria>
- One real jurisdiction + submission path works end-to-end.
- Workflow artifacts are produced from real adapters, not fixtures.
</success_criteria>

<output>
After completion, create `.planning/phases/01-runtime-slice/01-runtime-slice-02-SUMMARY.md`
</output>
