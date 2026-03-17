---
id: S03
parent: M010-w8n5cl
milestone: M010-w8n5cl
provides:
  - Central log redaction across API/worker/CLI plus read-only ops/release observability enforcement with runbook proof
requires:
  - slice: S02
    provides: Service principal auth with mTLS signal enforcement
affects:
  - none
key_files:
  - src/sps/logging/redaction.py
  - src/sps/workflows/worker.py
  - src/sps/workflows/cli.py
  - src/sps/api/main.py
  - src/sps/api/routes/ops.py
  - src/sps/api/routes/releases.py
  - tests/m010_s03_redaction_test.py
  - tests/m010_s03_observability_readonly_test.py
  - scripts/verify_m010_s03.sh
key_decisions:
  - Redaction implemented as a logging.Filter that scrubs message + extra fields and is attached to root handlers.
patterns_established:
  - Entrypoint logging config calls attach_redaction_filter() after logging.basicConfig.
observability_surfaces:
  - pytest caplog assertions + runbook stdout with [REDACTED] markers
  - scripts/verify_m010_s03.sh output for ops/release read-only denials
  - log output from API/worker/CLI entrypoints
drill_down_paths:
  - .gsd/milestones/M010-w8n5cl/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010-w8n5cl/slices/S03/tasks/T02-SUMMARY.md
duration: 1.4h
verification_result: passed
completed_at: 2026-03-16
---

# S03: Redaction + read-only observability with end-to-end proof

**Central log redaction now scrubs sensitive fields across runtime entrypoints, and ops/release observability surfaces remain read-only with a live runbook proving auth/mTLS + redaction together.**

## What Happened
Implemented a shared redaction filter that sanitizes messages and structured fields, wired it into API/worker/CLI logging, and added caplog tests for common secret patterns (Authorization, API keys, JWT secrets, DSN passwords). Added mutation-denial tests for ops/release endpoints and authored a runbook that uses a service-principal JWT + mTLS header to read metrics, confirm mutation rejection, and assert redacted log output in a real runtime.

## Verification
- `.venv/bin/python -m pytest tests/m010_s03_redaction_test.py -v`
- `.venv/bin/python -m pytest tests/m010_s03_observability_readonly_test.py -v`
- `bash scripts/verify_m010_s03.sh`

## Requirements Advanced
- None.

## Requirements Validated
- R029 — Proved redaction and read-only observability via pytest coverage and `scripts/verify_m010_s03.sh` runbook.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
- None.

## Known Limitations
- The runbook expects a running API at `localhost:8000`; it does not boot the server itself.

## Follow-ups
- None.

## Files Created/Modified
- `src/sps/logging/redaction.py` — shared redaction filter and helpers.
- `src/sps/logging/__init__.py` — exports redaction helpers.
- `src/sps/workflows/worker.py` — attaches redaction filter after logging config.
- `src/sps/workflows/cli.py` — attaches redaction filter after logging config.
- `src/sps/api/main.py` — attaches redaction filter to API logging handlers.
- `tests/m010_s03_redaction_test.py` — caplog tests for redaction behavior.
- `tests/m010_s03_observability_readonly_test.py` — mutation denial coverage for ops/release endpoints.
- `scripts/verify_m010_s03.sh` — service-principal + mTLS runbook with redaction proof.

## Forward Intelligence
### What the next slice should know
- The redaction filter is attached to root handlers via `attach_redaction_filter()` in each entrypoint; future log setup should follow that pattern to avoid bypassing redaction.

### What's fragile
- `scripts/verify_m010_s03.sh` assumes the API is already running on port 8000; forgetting to start it will fail the runbook before any redaction checks.

### Authoritative diagnostics
- `tests/m010_s03_redaction_test.py` — captures redaction behavior with caplog and flags any unredacted token/secret substrings.
- `scripts/verify_m010_s03.sh` — proves live read-only behavior + redaction output under service-principal + mTLS headers.

### What assumptions changed
- Assumed observability surfaces might be mutation-capable; confirmed they are GET-only with explicit 403/405 denials.
