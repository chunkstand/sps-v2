---
phase: 00-concerns
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sps/config.py
  - src/sps/guards/guard_assertions.py
  - invariants/sps/guard-assertions.yaml
  - tests/guards/test_guard_assertions.py
autonomous: true
must_haves:
  truths:
    - "Non-local environments refuse default secrets at startup"
    - "Guard assertion registry loads from a configurable path and fails fast when missing"
    - "Unknown guard assertion IDs raise a hard error outside local env"
  artifacts:
    - path: "src/sps/config.py"
      provides: "settings validation for secrets and registry path"
      contains: "guard_assertions_path"
    - path: "src/sps/guards/guard_assertions.py"
      provides: "strict guard assertion registry loader"
    - path: "tests/guards/test_guard_assertions.py"
      provides: "coverage for missing registry and unknown IDs"
  key_links:
    - from: "src/sps/guards/guard_assertions.py"
      to: "src/sps/config.py"
      via: "get_settings()"
      pattern: "get_settings\\(\\)"
    - from: "src/sps/guards/guard_assertions.py"
      to: "invariants/sps/guard-assertions.yaml"
      via: "settings path"
      pattern: "guard_assertions_path"
---

<objective>
Harden runtime validation for secrets and guard assertion registry loading.

Purpose: Prevent silent policy/credential failures in non-local environments.
Output: Config validation + strict guard assertion registry behavior with tests.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@src/sps/config.py
@src/sps/guards/guard_assertions.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add non-local settings validation</name>
  <files>src/sps/config.py</files>
  <action>
Add a pydantic model validator that runs after settings load. When env is not "local", fail fast if auth_jwt_secret, reviewer_api_key, or s3_secret_key are missing or still set to the current dev defaults. Add a new settings field guard_assertions_path (defaulting to "invariants/sps/guard-assertions.yaml") and validate that the file exists when env != "local". Keep behavior permissive in local env, but ensure error messages are explicit and actionable.
  </action>
  <verify>python -m pytest tests/guards -k guard_assertions</verify>
  <done>Non-local settings fail fast with clear errors when secrets or registry path are invalid.</done>
</task>

<task type="auto">
  <name>Task 2: Enforce strict guard assertion registry behavior</name>
  <files>src/sps/guards/guard_assertions.py, tests/guards/test_guard_assertions.py</files>
  <action>
Load guard assertions via Settings.guard_assertions_path (use get_settings). When registry file is missing, raise FileNotFoundError in all envs. When guard_assertion_id is unknown, raise a ValueError in non-local envs and keep warning + empty list behavior in local env. Add tests covering: missing registry path, unknown ID in non-local, and local fallback behavior.
  </action>
  <verify>python -m pytest tests/guards -k guard_assertions</verify>
  <done>Unknown IDs and missing registry are treated as hard errors outside local, with tests covering both paths.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/guards -k guard_assertions` passes.
</verification>

<success_criteria>
- Non-local environments reject default secrets and missing guard registry paths.
- Guard assertion resolution cannot silently drop unknown IDs outside local.
- Tests cover missing registry and unknown ID cases.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-01-SUMMARY.md`
</output>
