# S02: Service principal authentication with baseline mTLS signal

**Goal:** Enforce service-to-service authentication by validating signed service principal JWTs and requiring a baseline mTLS signal before allowing protected service routes to proceed.

**Demo:** Service principal requests with valid JWT + required mTLS header succeed while missing/invalid principals or missing mTLS signal are denied with explicit auth errors.

## Must-Haves
- Service principal JWT validation enforces `principal_type=service_principal` and maps role claims into the existing RBAC flow.
- Baseline mTLS signal header is required for service principal access and is configurable via Settings.
- Service-to-service entrypoints enforce the service principal + mTLS dependency (no per-route bypass).
- Automated tests cover allow + deny paths for service principal JWTs and mTLS header presence.

## Proof Level
- This slice proves: integration
- Real runtime required: no
- Human/UAT required: no

## Verification
- `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v`
- `rg "api.auth.denied" -n tests/m010_s02_service_principal_auth_test.py`

## Observability / Diagnostics
- Runtime signals: structured `api.auth.denied` logs with reason codes for invalid principal or missing mTLS header.
- Inspection surfaces: pytest assertions on denial payloads + structured log records.
- Failure visibility: HTTP 401/403 with `reason` fields that differentiate principal vs mTLS failures.
- Redaction constraints: no secrets in logs (header values not logged).

## Integration Closure
- Upstream surfaces consumed: `sps.auth.identity.validate_jwt_identity`, `sps.auth.rbac.require_roles`.
- New wiring introduced in this slice: `require_service_principal` dependency added to service-to-service routers.
- What remains before the milestone is truly usable end-to-end: run S03 redaction + observability hardening.

## Tasks
- [x] **T01: Implement service principal + mTLS auth contract and tests** `est:2h`
  - Why: Establish the signed service principal and baseline mTLS gate required for SEC-005, with proof via integration tests.
  - Files: `src/sps/auth/identity.py`, `src/sps/auth/rbac.py`, `src/sps/config.py`, `tests/helpers/auth_tokens.py`, `tests/m010_s02_service_principal_auth_test.py`
  - Do: add service principal claim validation and mTLS header enforcement dependency; wire dependency into service routes; update test token helpers; implement tests for allow/deny paths (missing header, invalid claim, role mismatch).
  - Verify: `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v`
  - Done when: tests prove service principal requests require both valid JWT and mTLS signal and deny otherwise.

## Files Likely Touched
- `src/sps/auth/identity.py`
- `src/sps/auth/rbac.py`
- `src/sps/config.py`
- `src/sps/api/main.py`
- `src/sps/api/routes/ops.py`
- `src/sps/api/routes/releases.py`
- `tests/helpers/auth_tokens.py`
- `tests/m010_s02_service_principal_auth_test.py`
