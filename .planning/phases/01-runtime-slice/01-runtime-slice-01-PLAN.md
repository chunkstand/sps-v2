---
phase: 01-runtime-slice
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sps/workflows/permit_case/activities.py
  - src/sps/documents/generator.py
  - src/sps/adapters/__init__.py
  - src/sps/adapters/*.py
  - tests/runtime_slice/test_adapter_wiring.py
autonomous: false
must_haves:
  truths:
    - "Workflow activities can call adapter-backed implementations instead of fixtures"
    - "A single production slice is selected and wired for end-to-end use"
  artifacts:
    - path: "src/sps/adapters"
      provides: "adapter interfaces and wiring"
    - path: "src/sps/workflows/permit_case/activities.py"
      provides: "adapter-backed activity calls"
  key_links:
    - from: "src/sps/workflows/permit_case/activities.py"
      to: "src/sps/adapters"
      via: "adapter dispatch"
      pattern: "adapters"
---

<objective>
Introduce adapter interfaces and wire workflow activities to a single production slice.

Purpose: Replace fixture-backed seams with real adapters in a controlled, narrow scope.
Output: Adapter interfaces + wiring + slice selection.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/workflows/permit_case/activities.py
@src/sps/documents/generator.py
</context>

<tasks>

<task type="checkpoint:decision" gate="blocking">
  <decision>Select the first production slice (jurisdiction + submission path)</decision>
  <context>We will implement adapters for a single, narrow path end-to-end before generalizing.</context>
  <options>
    <option id="option-a">
      <name>City A + manual submission path</name>
      <pros>Lower integration risk; no external portal dependencies</pros>
      <cons>Does not validate automated submission adapters</cons>
    </option>
    <option id="option-b">
      <name>City A + portal submission path</name>
      <pros>Validates full automation; tests real portal adapter path</pros>
      <cons>Higher integration and credential complexity</cons>
    </option>
  </options>
  <decision_status>Chosen: Phaniville + manual submission path (placeholders allowed)</decision_status>
</task>

<task type="auto">
  <name>Task 1: Define adapter interfaces and wiring</name>
  <files>src/sps/adapters/__init__.py, src/sps/adapters/*.py, src/sps/workflows/permit_case/activities.py, src/sps/documents/generator.py</files>
  <action>
Create adapter interfaces for jurisdiction resolution, requirements/source, compliance evaluation, document compilation, submission, and status ingestion. Provide a simple adapter registry and selection mechanism (based on settings or a config map). Update activities.py and generator.py to call adapters instead of fixtures for the selected slice while preserving existing fixtures for other paths. Use the fictional jurisdiction "Phaniville" for the slice and allow placeholder/manual submission handling where needed.
  </action>
  <verify>python -m pytest tests/runtime_slice/test_adapter_wiring.py</verify>
  <done>Workflow activities dispatch through adapters for the selected slice.</done>
</task>

<task type="auto">
  <name>Task 2: Add wiring tests for the selected slice</name>
  <files>tests/runtime_slice/test_adapter_wiring.py</files>
  <action>
Add tests asserting that the selected slice uses adapter-backed implementations and that non-selected paths continue to use fixtures. Keep tests fast and independent of external services.
  </action>
  <verify>python -m pytest tests/runtime_slice/test_adapter_wiring.py</verify>
  <done>Tests confirm adapter dispatch and fallback behavior.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/runtime_slice/test_adapter_wiring.py` passes.
</verification>

<success_criteria>
- Adapter interfaces exist and are wired into workflow activities.
- A single production slice is selected and uses adapters.
</success_criteria>

<output>
After completion, create `.planning/phases/01-runtime-slice/01-runtime-slice-01-SUMMARY.md`
</output>
