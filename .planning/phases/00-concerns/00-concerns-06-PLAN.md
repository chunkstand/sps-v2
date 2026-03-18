---
phase: 00-concerns
plan: 06
type: execute
wave: 3
depends_on:
  - "00-concerns-04"
files_modified:
  - src/sps/workflows/permit_case/workflow.py
  - src/sps/workflows/permit_case/activities.py
  - src/sps/workflows/permit_case/*.py
  - tests/workflows/test_permit_case_workflow.py
autonomous: true
must_haves:
  truths:
    - "Permit case workflow logic is split by domain area with smaller modules"
    - "Workflow behavior remains unchanged after refactor"
  artifacts:
    - path: "src/sps/workflows/permit_case/workflow.py"
      provides: "orchestrator wiring only"
    - path: "src/sps/workflows/permit_case"
      provides: "new domain-focused modules"
  key_links:
    - from: "src/sps/workflows/permit_case/workflow.py"
      to: "src/sps/workflows/permit_case"
      via: "imported helpers"
      pattern: "from sps.workflows.permit_case"
---

<objective>
Refactor permit case workflow modules into smaller, domain-focused units.

Purpose: Reduce regression risk and review complexity for workflow changes.
Output: Modular workflow code with unchanged behavior and tests passing.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/workflows/permit_case/workflow.py
@src/sps/workflows/permit_case/activities.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Split workflow logic into domain-focused modules</name>
  <files>src/sps/workflows/permit_case/workflow.py, src/sps/workflows/permit_case/*.py</files>
  <action>
Extract large workflow sections into focused modules (e.g., intake transitions, document package generation, submission handling, correction/resubmission flows). Keep workflow.py as the orchestrator that wires together the steps and shared helpers. Avoid changing behavior; only move code and improve readability.
  </action>
  <verify>python -m pytest tests/workflows -k permit_case</verify>
  <done>Workflow logic is organized into smaller modules with the same runtime behavior.</done>
</task>

<task type="auto">
  <name>Task 2: Update imports and tests to match new structure</name>
  <files>src/sps/workflows/permit_case/workflow.py, src/sps/workflows/permit_case/activities.py, tests/workflows/test_permit_case_workflow.py</files>
  <action>
Update imports, helper references, and any test fixtures that point at the refactored workflow modules. Ensure unit/integration tests continue to validate core transitions without changing assertions.
  </action>
  <verify>python -m pytest tests/workflows -k permit_case</verify>
  <done>Workflow tests pass with the refactored module structure.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/workflows -k permit_case` passes.
</verification>

<success_criteria>
- Permit case workflow is split into smaller, domain-focused modules.
- Tests confirm behavior parity after refactor.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-06-SUMMARY.md`
</output>
