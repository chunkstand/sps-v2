---
estimated_steps: 6
estimated_files: 7
---

# T01: Implement service principal + mTLS auth contract and tests

**Slice:** S02 — Service principal authentication with baseline mTLS signal
**Milestone:** M010-w8n5cl

## Description
Add a service principal auth dependency that validates a dedicated JWT claim and requires an mTLS signal header, then wire it into service-to-service routes. Extend auth token helpers and add integration tests proving allow/deny paths with explicit failure reasons.

## Steps
1. Extend `sps.auth.identity` to parse service principal claims (`principal_type=service_principal`) and map role claims into the existing Identity model.
2. Add Settings configuration for the required mTLS signal header (default `X-Forwarded-Client-Cert`) and expose it to auth dependencies.
3. Implement `require_service_principal` in `sps.auth.rbac` that validates the service principal identity and denies when the mTLS header is missing/empty (without logging header contents).
4. Wire `require_service_principal` into service-to-service routers (ops/release service endpoints) alongside existing role enforcement.
5. Extend `tests/helpers/auth_tokens.py` to mint service principal JWTs with the new claim shape and roles.
6. Add `tests/m010_s02_service_principal_auth_test.py` covering success, missing/invalid principal claims, and missing mTLS header denials.

## Must-Haves
- [ ] Service principal validation rejects tokens without `principal_type=service_principal` and denies with explicit reason.
- [ ] mTLS signal header is required for service principal access and configurable via Settings.
- [ ] Service-to-service routers enforce the new dependency with role checks intact.
- [ ] Tests prove allow/deny behavior for valid principals, invalid claims, and missing mTLS header.

## Verification
- `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v`

## Observability Impact
- Signals added/changed: `api.auth.denied` reason codes for service principal or mTLS failures.
- How a future agent inspects this: run the pytest file and review structured log events.
- Failure state exposed: 401/403 payload contains reason and guard identifiers for auth denial.

## Inputs
- `src/sps/auth/identity.py` — existing JWT validation and Identity model used by S01.
- `src/sps/auth/rbac.py` — current dependency pattern for auth + role enforcement.
- `tests/helpers/auth_tokens.py` — token minting utilities for auth tests.

## Expected Output
- `src/sps/auth/identity.py` — service principal claim validation integrated into identity parsing.
- `src/sps/auth/rbac.py` — `require_service_principal` dependency enforcing mTLS signal.
- `src/sps/config.py` — settings for mTLS signal header.
- `tests/helpers/auth_tokens.py` — service principal JWT helper.
- `tests/m010_s02_service_principal_auth_test.py` — integration tests proving allow/deny paths.
