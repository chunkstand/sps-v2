---
estimated_steps: 6
estimated_files: 7
---

# T01: Implement JWT identity validation + RBAC dependencies and wire routers

**Slice:** S01 — Authenticated identity + RBAC gate for all API routers
**Milestone:** M010-w8n5cl

## Description
Add the JWT identity validator and RBAC enforcement layer, then attach it to every API router (including reviewer/ops pages). This establishes the authenticated boundary required by R027/R028 and replaces reviewer API key gating.

## Steps
1. Add auth settings to `Settings` (issuer, audience, secret, algorithm) and implement JWT validation helpers + identity model in `src/sps/auth/identity.py`.
2. Define role enumeration and `require_identity` / `require_roles` dependencies in `src/sps/auth/rbac.py`, emitting structured denial logs without leaking tokens.
3. Apply RBAC dependencies to all API routers and page routes in `src/sps/api/main.py` and `src/sps/api/routes/*`, removing `require_reviewer_api_key` usage.

## Must-Haves
- [ ] JWT validation enforces issuer, audience, and expiry, and never logs tokens.
- [ ] Every router is protected by `require_identity` plus role checks aligned to its surface.

## Verification
- `pytest tests/m010_s01_auth_rbac_test.py -k "auth_required or role_denied" -v`

## Observability Impact
- Signals added/changed: structured auth denial log event (`api.auth.denied`) with error code + subject/roles only
- How a future agent inspects this: API logs + 401/403 error responses
- Failure state exposed: error_code + required_roles in 403 response; auth_reason in 401 response

## Inputs
- `src/sps/api/main.py` — current router registration
- `src/sps/api/routes/*.py` — existing endpoints and reviewer API key gating

## Expected Output
- `src/sps/auth/identity.py` — JWT validation + identity parsing
- `src/sps/auth/rbac.py` — role definitions + auth dependencies
- `src/sps/api/routes/*` — router-level RBAC enforcement replacing API key gating
