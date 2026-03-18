---
phase: 00-concerns
plan: 09
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/ci.yml
  - pyproject.toml
autonomous: true
must_haves:
  truths:
    - "CI runs a fast pytest lane for pure/unit tests"
    - "CI runs a separate integration lane for DB/Temporal-backed tests"
    - "Reviewer auth mismatch is caught by CI"
  artifacts:
    - path: ".github/workflows/ci.yml"
      provides: "unit + integration test jobs"
  key_links:
    - from: ".github/workflows/ci.yml"
      to: "tests"
      via: "pytest commands"
      pattern: "pytest"
---

<objective>
Strengthen CI to gate runtime regressions with unit and integration lanes.

Purpose: Catch auth/test mismatches and runtime regressions automatically.
Output: Updated CI with split pytest jobs.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@.github/workflows/ci.yml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add a fast pytest lane for pure tests</name>
  <files>.github/workflows/ci.yml, pyproject.toml</files>
  <action>
Introduce a CI job that runs only pure/unit tests (no DB/Temporal). If pytest markers are not defined, add markers to pyproject.toml and tag existing tests to separate unit vs integration. The fast lane should run on every push/PR and finish quickly.
  </action>
  <verify>python -m pytest -m "unit"</verify>
  <done>CI has a fast lane that runs unit/pure tests only.</done>
</task>

<task type="auto">
  <name>Task 2: Add an integration lane with DB/Temporal services</name>
  <files>.github/workflows/ci.yml, pyproject.toml</files>
  <action>
Add a separate CI job that brings up Postgres/Temporal (service containers or docker-compose) and runs integration tests (marked or targeted). Ensure the reviewer auth tests run in at least one lane to catch header mismatches.
  </action>
  <verify>python -m pytest -m "integration"</verify>
  <done>Integration tests run in CI with required services.</done>
</task>

</tasks>

<verification>
CI workflow includes distinct unit and integration pytest jobs.
</verification>

<success_criteria>
- Unit and integration tests are separated and run in CI.
- Auth/test drift is caught by CI.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-09-SUMMARY.md`
</output>
