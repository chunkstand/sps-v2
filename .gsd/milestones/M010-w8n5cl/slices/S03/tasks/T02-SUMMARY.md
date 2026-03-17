---
id: T02
parent: S03
milestone: M010-w8n5cl
provides:
  - Read-only observability tests plus a service-principal/mTLS runbook with redaction proof output
key_files:
  - tests/m010_s03_observability_readonly_test.py
  - scripts/verify_m010_s03.sh
key_decisions:
  - None
patterns_established:
  - Runbook generates service-principal JWT from config and asserts redacted log output before printing
observability_surfaces:
  - pytest denial assertions + runbook stdout/stderr with redaction markers
duration: 0.6h
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Prove read-only observability + end-to-end runbook

**Added read-only mutation denial tests and a service-principal/mTLS runbook that asserts redacted log output.**

## What Happened
- Added negative tests for mutation attempts against ops metrics/release blockers endpoints (405) and release endpoints (403/405) using service-principal auth with mTLS.
- Wrote `scripts/verify_m010_s03.sh` to generate a service-principal JWT, call ops metrics and release blockers with mTLS, attempt a rejected mutation, and emit redaction-verified log output.
- Ensured runbook requests use Authorization bearer tokens and never the legacy reviewer API key.

## Verification
- `python -m pytest tests/m010_s03_observability_readonly_test.py -v` (failed: `python` not found)
- `.venv/bin/python -m pytest tests/m010_s03_observability_readonly_test.py -v`
- `bash scripts/verify_m010_s03.sh` (failed: API not running on localhost:8000)

## Diagnostics
- Rerun `bash scripts/verify_m010_s03.sh` with the API running to see redacted log output and read-only denial status lines.
- Tests provide per-endpoint 403/405 assertions in `tests/m010_s03_observability_readonly_test.py`.

## Deviations
- None.

## Known Issues
- `scripts/verify_m010_s03.sh` fails if the API server is not running on localhost:8000.

## Files Created/Modified
- `tests/m010_s03_observability_readonly_test.py` — new mutation-denial coverage for ops/release endpoints.
- `scripts/verify_m010_s03.sh` — runbook verification using service-principal JWT, mTLS header, mutation rejection, and redaction proof.
