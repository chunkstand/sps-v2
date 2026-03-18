---
phase: 00-concerns
plan: 09
subsystem: ci
tags:
  - pytest
  - ci
  - integration
depends_on: []
provides:
  - split unit and integration test lanes
affects:
  - .github/workflows/ci.yml
  - pyproject.toml
  - tests/conftest.py
tech_stack:
  - github-actions
  - pytest
key_files:
  - .github/workflows/ci.yml
  - pyproject.toml
  - tests/conftest.py
decisions:
  - Use pytest collection hook to auto-tag integration vs unit based on integration guard
metrics:
  duration: not_tracked
  completed_at: 2026-03-17
---

# Phase 00 Plan 09: CI Split Summary

Split CI into unit and integration pytest lanes, with automatic marker tagging to keep the fast lane focused on pure tests and ensure integration coverage includes reviewer auth boundaries.

## Task 1: Add a fast pytest lane for pure tests

- Added `unit-tests` job running `pytest -m "unit"` on every push/PR.
- Added a `unit` marker to pytest config and auto-tagging for tests without integration guards.

## Task 2: Add an integration lane with DB/Temporal services

- Added `integration-tests` job that starts docker-compose services and runs `pytest -m "integration"` with the integration guard enabled.
- Integration lane includes reviewer auth tests that rely on Temporal/Postgres and the legacy header.

## Verification

- Not run locally (CI-only changes).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pytest auto-tagging to avoid manually editing many tests**
- **Found during:** Task 1
- **Issue:** Many integration tests were not explicitly marked, which would have excluded them from the integration lane.
- **Fix:** Added a collection hook in `tests/conftest.py` to mark tests with the integration guard as `integration`, and everything else as `unit`.
- **Files modified:** `tests/conftest.py`
