---
estimated_steps: 4
estimated_files: 2
---

# T02: Add integration tests for auth and RBAC gates

**Slice:** S01 — Authenticated identity + RBAC gate for all API routers
**Milestone:** M010-w8n5cl

## Description
Create ASGI integration tests that generate JWTs and assert auth-required and role-based denials across the API surface, proving the boundary contract.

## Steps
1. Add a helper to generate test JWTs with roles using the configured auth settings.
2. Write tests that assert missing/invalid tokens return 401 with stable error codes.
3. Add role-mismatch tests (403) and positive access checks for representative endpoints per router category.

## Must-Haves
- [ ] Tests cover missing token, invalid token, role denial, and allowed role access.
- [ ] Auth failure responses include explicit error codes and omit sensitive data.

## Verification
- `pytest tests/m010_s01_auth_rbac_test.py -v`

## Inputs
- `src/sps/auth/identity.py` — JWT validation helpers
- `src/sps/auth/rbac.py` — role definitions + dependency wiring

## Expected Output
- `tests/helpers/auth_tokens.py` — token factory for tests
- `tests/m010_s01_auth_rbac_test.py` — integration coverage for auth/RBAC gates

## Observability Impact
- Signals exercised: auth denial responses (401/403) with `detail.auth_reason` or `detail.error_code` + `detail.required_roles` in payloads.
- Inspection path: run `pytest tests/m010_s01_auth_rbac_test.py -v` to surface failing cases; inspect response JSON in assertions for missing/incorrect error fields.
- Failure visibility: tests fail with explicit assertion messages when error codes are absent, unexpected, or include sensitive data.
