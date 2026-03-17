# S01: Authenticated identity + RBAC gate for all API routers — UAT

**Milestone:** M010-w8n5cl
**Written:** 2026-03-16

## UAT Type
- UAT mode: artifact-driven
- Why this mode is sufficient: The slice is proven via integration tests that exercise real FastAPI routing and auth dependencies without a live runtime requirement.

## Preconditions
- `.venv` exists with dependencies installed.
- Test database is available (pytest manages setup/teardown).

## Smoke Test
- Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "auth_required" -v` and confirm the missing/invalid token tests pass.

## Test Cases
### 1. Missing token is denied on protected APIs
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "auth_required_missing_token" -v`.
2. **Expected:** Request returns 401 with `detail.auth_reason` indicating missing credentials.

### 2. Invalid token is denied with structured auth reason
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "auth_required_invalid_token" -v`.
2. **Expected:** Request returns 401 with `detail.auth_reason` indicating invalid token.

### 3. Role mismatch is denied with required roles
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "role_denied" -v`.
2. **Expected:** Request returns 403 with `detail.error_code` and `detail.required_roles` listing the router’s required roles.

### 4. Allowed role access succeeds on representative routes
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "allowed_role_access" -v`.
2. **Expected:** Each representative endpoint (cases, evidence, reviews, reviewer console, contradictions, dissents, releases, ops) returns the expected success or validation status (200/404/422) instead of 401/403.

### 5. Auth-denied log event is emitted
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "denied_log" -v`.
2. **Expected:** `api.auth.denied` structured log event is emitted without logging raw tokens.

## Edge Cases
### Invalid signature token
1. Run `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "auth_required_invalid_token" -v`.
2. **Expected:** 401 denial with `detail.auth_reason` and no token data in logs.

## Failure Signals
- Any protected route returns 200 without a token.
- 403 responses omit `detail.error_code` or `detail.required_roles`.
- `api.auth.denied` log entries are missing or include raw Authorization headers.

## Requirements Proved By This UAT
- R027 — Authenticated identities are required for all routers.
- R028 — RBAC role separation is enforced on routers with explicit denials.

## Not Proven By This UAT
- R029 — Redaction/read-only observability (deferred to S03).
- R031 — Service principal + mTLS enforcement (deferred to S02).

## Notes for Tester
- PyJWT may emit warnings about short HMAC keys in tests; these are acceptable for test fixtures but production secrets must be longer.
