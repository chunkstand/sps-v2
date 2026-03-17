---
id: T01
parent: S03
milestone: M010-w8n5cl
provides:
  - centralized log redaction filter wired into API/worker/CLI with caplog coverage
key_files:
  - src/sps/logging/redaction.py
  - src/sps/workflows/worker.py
  - src/sps/workflows/cli.py
  - src/sps/api/main.py
  - tests/m010_s03_redaction_test.py
key_decisions:
  - Redaction implemented as a logging.Filter that scrubs message + extra fields and attaches to root handlers.
patterns_established:
  - Entrypoint logging config calls attach_redaction_filter() after logging.basicConfig.
observability_surfaces:
  - pytest caplog assertions + log output with [REDACTED] markers
duration: 0.8h
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add centralized log redaction filter + tests

**Added a shared log redaction filter, wired it into API/worker/CLI logging, and added caplog tests for common secret patterns.**

## What Happened
- Added `sps.logging.redaction` with message + extra-field redaction (Authorization, API keys, JWT secrets, DSN passwords).
- Wired `attach_redaction_filter()` into worker, CLI, and API logging configuration.
- Added caplog tests validating redaction of message args, extra fields, DSN passwords, and failure-surface check.

## Verification
- ✅ `.venv/bin/python -m pytest tests/m010_s03_redaction_test.py -v`
- ✅ `.venv/bin/python -m pytest tests/m010_s03_redaction_test.py -k redaction_failure_surface -v`
- ❌ `.venv/bin/python -m pytest tests/m010_s03_observability_readonly_test.py -v` (file missing)
- ❌ `bash scripts/verify_m010_s03.sh` (script missing)

## Diagnostics
- Inspect redaction behavior via `tests/m010_s03_redaction_test.py` caplog assertions; log output includes `[REDACTED]` markers.

## Deviations
- None.

## Known Issues
- `tests/m010_s03_observability_readonly_test.py` and `scripts/verify_m010_s03.sh` are not present yet (expected in T02).

## Files Created/Modified
- `src/sps/logging/__init__.py` — logging package exports redaction helpers.
- `src/sps/logging/redaction.py` — shared redaction filter and helpers.
- `src/sps/workflows/worker.py` — attach redaction filter after logging config.
- `src/sps/workflows/cli.py` — attach redaction filter after logging config.
- `src/sps/api/main.py` — configure logging and attach redaction filter on import.
- `tests/m010_s03_redaction_test.py` — caplog coverage for redaction behavior.
