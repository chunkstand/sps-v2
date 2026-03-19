---
phase: 00-concerns
plan: 08
type: execute
wave: 1
depends_on: []
files_modified:
  - PACKAGE-MANIFEST.json
  - sps_full_spec_package/PACKAGE-MANIFEST.json
  - sps_full_spec_package/README.md
  - scripts/generate_release_bundle.py
  - tests/m009_s02_release_bundle_test.py
autonomous: false
must_haves:
  truths:
    - "Only one authoritative spec package source of truth exists"
    - "PACKAGE-MANIFEST.json matches the authoritative package contents"
  artifacts:
    - path: "PACKAGE-MANIFEST.json"
      provides: "root manifest aligned to package contents"
    - path: "sps_full_spec_package/README.md"
      provides: "explicit package role documentation"
  key_links:
    - from: "scripts/generate_release_bundle.py"
      to: "PACKAGE-MANIFEST.json"
      via: "manifest loading"
      pattern: "PACKAGE-MANIFEST.json"
---

<objective>
Re-freeze the authoritative package and align PACKAGE-MANIFEST.json with reality.

Purpose: Eliminate release noise from mismatched package copies and stale manifest data.
Output: Single source of truth + refreshed manifest + clear documentation.
</objective>

<execution_context>
@./.opencode/get-shit-done/workflows/execute-plan.md
@./.opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/codebase/CONCERNS.md
@PACKAGE-MANIFEST.json
@sps_full_spec_package/PACKAGE-MANIFEST.json
@scripts/generate_release_bundle.py
</context>

<tasks>

<task type="checkpoint:decision" gate="blocking">
  <decision>Which package copy is authoritative: repo root or sps_full_spec_package/ ?</decision>
  <context>The manifest and release tooling must point at a single, explicit source of truth.</context>
  <options>
    <option id="option-a">
      <name>Root package is authoritative</name>
      <pros>Fewer nested paths; simplest build tooling</pros>
      <cons>Need to remove or clearly mark sps_full_spec_package as non-authoritative</cons>
    </option>
    <option id="option-b">
      <name>sps_full_spec_package is authoritative</name>
      <pros>Explicit package boundary; aligns with current folder naming</pros>
      <cons>Requires updating tooling/tests to target the nested path</cons>
    </option>
  </options>
  <decision_status>Chosen: sps_full_spec_package is authoritative</decision_status>
</task>

<task type="auto">
  <name>Task 0: Audit package gaps vs spec expectations</name>
  <files>sps_full_spec_package/README.md, sps_full_spec_package/PACKAGE-MANIFEST.json, PACKAGE-MANIFEST.json</files>
  <action>
Compare the implemented package contents against the spec package instructions and document any gaps in the plan summary before changing manifests. Identify missing files, mismatched paths, or duplicate content between root and sps_full_spec_package. Use this gap list to guide regeneration of the authoritative manifest.
  </action>
  <verify>Document gaps in the plan summary and list actionable fixes.</verify>
  <done>Package gaps are enumerated before any manifest or tooling changes.</done>
</task>

<task type="auto">
  <name>Task 1: Align manifest to the authoritative package</name>
  <files>PACKAGE-MANIFEST.json, sps_full_spec_package/PACKAGE-MANIFEST.json</files>
  <action>
Regenerate or update the PACKAGE-MANIFEST.json for the chosen authoritative package so every listed path exists and artifact IDs resolve. If the non-authoritative copy remains, make its manifest explicit (either removed or clearly marked as non-authoritative). Ensure release tooling reads the correct manifest.
  </action>
  <verify>python -m pytest tests/m009_s02_release_bundle_test.py</verify>
  <done>Manifest matches the authoritative package and release bundle tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Make package role explicit</name>
  <files>sps_full_spec_package/README.md, scripts/generate_release_bundle.py</files>
  <action>
Document the chosen source of truth in sps_full_spec_package/README.md (and root README if needed). Update generate_release_bundle.py defaults and help text to point at the authoritative package path and manifest.
  </action>
  <verify>python -m pytest tests/m009_s02_release_bundle_test.py</verify>
  <done>Docs and tooling clearly indicate which package is authoritative.</done>
</task>

</tasks>

<verification>
`python -m pytest tests/m009_s02_release_bundle_test.py` passes.
</verification>

<success_criteria>
- Only one authoritative package is used by tooling.
- Manifest and package contents are in sync.
</success_criteria>

<output>
After completion, create `.planning/phases/00-concerns/00-concerns-08-SUMMARY.md`
</output>
