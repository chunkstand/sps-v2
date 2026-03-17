---
id: T02
parent: S01
milestone: M010-w8n5cl
provides:
  - Integration coverage for JWT auth and RBAC gates across API/page routers.
key_files:
  - tests/m010_s01_auth_rbac_test.py
  - tests/helpers/auth_tokens.py
key_decisions:
  - None
patterns_established:
  - Parameterized allowed-role checks using JWTs and representative endpoints.
observability_surfaces:
  - Auth denial responses (401/403) and structured `api.auth.denied` log events verified via pytest.
duration: 1h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Add integration tests for auth and RBAC gates

**Added ASGI integration coverage for missing/invalid tokens, role denials, and allowed access across all router categories.**

## What Happened
- Extended the auth/RBAC integration suite to cover missing/invalid token denial shapes, role mismatch denial payloads, and positive access checks for cases, evidence, reviews, reviewer console, contradictions, dissents, releases, and ops routes.
- Added DB migration setup for the test run and tightened denial-log verification to ensure structured auth-denied events emit without leaking credentials.

## Verification
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -v`
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "denied_log" -v`

## Diagnostics
- Inspect 401/403 response payloads for `detail.auth_reason`, `detail.error_code`, and `detail.required_roles`.
- Look for `api.auth.denied` events on the `sps.auth.rbac` logger when missing/invalid auth is exercised.

## Deviations
- None

## Known Issues
- None

## Files Created/Modified
- `tests/m010_s01_auth_rbac_test.py` — expanded auth/RBAC integration coverage and log assertions.
- `.gsd/milestones/M010-w8n5cl/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section.
- `.gsd/milestones/M010-w8n5cl/slices/S01/S01-PLAN.md` — marked T02 complete.
- `.gsd/STATE.md` — updated next action after completing T02.
