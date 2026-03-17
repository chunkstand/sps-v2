# S02: Service principal authentication with baseline mTLS signal — UAT

**Milestone:** M010-w8n5cl
**Written:** 2026-03-16

## UAT Type
- UAT mode: artifact-driven
- Why this mode is sufficient: Integration tests exercise the service principal + mTLS enforcement logic directly against the FastAPI app without requiring a live runtime.

## Preconditions
- Repo dependencies installed (`.venv` exists) and tests can run.
- No external services required.

## Smoke Test
Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v` and confirm all tests pass.

## Test Cases
### 1. Valid service principal with mTLS signal passes
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_allows_with_mtls_header -v`.
2. **Expected:** HTTP 200 response with authenticated access; no auth denial payload.

### 2. Missing principal_type claim is denied
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_missing_principal_type -v`.
2. **Expected:** HTTP 401 with `detail.auth_reason=missing_principal_type` and `detail.guard=service_principal_required`.

### 3. Invalid principal_type claim is denied
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_invalid_principal_type -v`.
2. **Expected:** HTTP 401 with `detail.auth_reason=invalid_principal_type` and `detail.guard=service_principal_required`.

### 4. Missing mTLS signal header is denied
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_missing_mtls_header -v`.
2. **Expected:** HTTP 401 with `detail.auth_reason=missing_mtls_signal` and `detail.guard=service_principal_mtls_required`.

### 5. Custom mTLS header setting is honored
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_honors_mtls_header_setting -v`.
2. **Expected:** Request succeeds only when the configured header is present; denial uses `missing_mtls_signal` when absent.

## Edge Cases
### Missing mTLS header emits auth denial signal
1. Run `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py::test_service_principal_missing_mtls_header -v`.
2. **Expected:** Structured log `api.auth.denied` is captured with `auth_reason=missing_mtls_signal` (asserted in test).

## Failure Signals
- pytest failures in `tests/m010_s02_service_principal_auth_test.py`.
- Missing `api.auth.denied` log record for denial scenarios.

## Requirements Proved By This UAT
- R031 — Service principal JWTs plus required mTLS signal header are enforced with explicit denial reasons.

## Not Proven By This UAT
- Live TLS client certificate validation or proxy configuration in a real runtime.
- R029 redaction + read-only observability enforcement (S03 scope).

## Notes for Tester
- Tests use an HMAC key under the recommended length; warnings are expected and do not indicate failure.
