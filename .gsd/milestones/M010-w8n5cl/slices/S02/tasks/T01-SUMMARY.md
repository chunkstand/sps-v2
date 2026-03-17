---
id: T01
parent: S02
milestone: M010-w8n5cl
provides:
  - service principal auth dependency with mTLS guard + integration tests
key_files:
  - src/sps/auth/identity.py
  - src/sps/auth/rbac.py
  - src/sps/api/routes/ops.py
  - tests/m010_s02_service_principal_auth_test.py
key_decisions:
  - extended validate_jwt_identity with expected_principal_type instead of introducing a new Identity type
patterns_established:
  - require_service_principal enforces principal_type + mTLS signal with explicit auth_reason payloads
observability_surfaces:
  - api.auth.denied logs with auth_reason for service_principal and mtls failures
  - HTTP 401 payloads include guard/auth_reason for auth denial
  - pytest coverage in tests/m010_s02_service_principal_auth_test.py
duration: 1h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Implement service principal + mTLS auth contract and tests

**Added service principal JWT validation with mTLS header enforcement and service-route wiring, plus integration tests for allow/deny paths.**

## What Happened
- Extended JWT validation to enforce `principal_type=service_principal` when requested and added mTLS signal header setting.
- Added `require_service_principal` dependency enforcing principal type and mTLS presence, and wired it into ops/release API routers alongside role checks.
- Updated auth token helpers and existing RBAC tests to issue service principal tokens with the required mTLS header.
- Added integration tests covering success, invalid/missing principal type, missing mTLS header, and configurable header name behavior (with log assertion).

## Verification
- `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v`
- `rg "api.auth.denied" -n tests/m010_s02_service_principal_auth_test.py`

## Diagnostics
- Inspect `api.auth.denied` log records for `auth_reason=missing_principal_type|invalid_principal_type|missing_mtls_signal`.
- Auth failure responses include `detail.error`, `detail.auth_reason`, and `detail.guard` for service principal or mTLS failures.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/auth/identity.py` — added principal_type validation for service principals.
- `src/sps/auth/rbac.py` — added require_service_principal with mTLS enforcement and logging.
- `src/sps/config.py` — added configurable mTLS signal header setting.
- `src/sps/api/routes/ops.py` — enforced service principal dependency on ops API routes.
- `src/sps/api/routes/releases.py` — enforced service principal dependency on release API routes.
- `tests/helpers/auth_tokens.py` — added service principal JWT helper and extra claims support.
- `tests/m010_s01_auth_rbac_test.py` — updated role-access test to use service principal auth on service routes.
- `tests/m010_s02_service_principal_auth_test.py` — added allow/deny coverage for service principal + mTLS enforcement.
- `.gsd/milestones/M010-w8n5cl/slices/S02/S02-PLAN.md` — recorded additional verification step and task completion.
- `.gsd/STATE.md` — updated next action.
