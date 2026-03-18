---
phase: 00-concerns
plan: 08
subsystem: spec-package
tags:
  - package-manifest
  - release-tooling
  - documentation
depends_on: []
provides:
  - sps_full_spec_package as authoritative spec package
affects:
  - PACKAGE-MANIFEST.json
  - sps_full_spec_package/PACKAGE-MANIFEST.json
  - scripts/generate_release_bundle.py
  - README.md
  - sps_full_spec_package/README.md
tech_stack:
  - python
  - json-manifest
key_files:
  - PACKAGE-MANIFEST.json
  - sps_full_spec_package/PACKAGE-MANIFEST.json
  - scripts/generate_release_bundle.py
  - README.md
  - sps_full_spec_package/README.md
decisions:
  - sps_full_spec_package is the authoritative spec package
metrics:
  duration: not_tracked
  completed_at: 2026-03-17
---

# Phase 00 Plan 08: Spec Package Alignment Summary

Aligned release tooling defaults and documentation to treat `sps_full_spec_package/` as the authoritative spec package, then refreshed manifests to match updated README contents.

## Task 0: Audit package gaps vs spec expectations

- Root and `sps_full_spec_package/` are duplicate package copies with identical contents and manifest structure, which creates ambiguity about the source of truth.
- Both manifests omit `PACKAGE-MANIFEST.json` itself (the file exists, but is not listed), which is acceptable for verification but worth noting against artifact obligation references.
- Release tooling defaults previously targeted repo root, reinforcing the ambiguity.

## Task 1: Align manifest to authoritative package

- Updated both manifests to match the updated README content (SHA/byte counts refreshed).
- Retained the root manifest as a mirror copy; authority is documented as `sps_full_spec_package/`.

## Task 2: Make package role explicit

- Added authoritative location notes to both README files.
- Updated `scripts/generate_release_bundle.py` defaults and help text to point at `sps_full_spec_package/`.

## Verification

- Not run (user requested skipping tests).

## Deviations from Plan

- None.
