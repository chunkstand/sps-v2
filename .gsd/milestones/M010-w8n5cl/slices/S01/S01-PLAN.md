# S01: Authenticated identity + RBAC gate for all API routers

**Goal:** Every FastAPI router (cases, evidence, reviews, contradictions, dissents, releases, ops, reviewer console) requires a verified identity token and enforces role-based access.
**Demo:** Requests without tokens return 401, role-mismatched requests return 403, and correctly-privileged identities can access at least one endpoint per router (including `/reviewer` and `/ops`).

## Must-Haves
- HMAC-signed JWT validation (issuer/audience/expiry) produces a request identity context (subject + roles) without logging secrets.
- RBAC role checks are enforced on all API routers, replacing reviewer API key gating.
- Auth failures return explicit error codes and emit a structured denial log without leaking tokens.

## Proof Level
- This slice proves: integration
- Real runtime required: no
- Human/UAT required: no

## Verification
- `pytest tests/m010_s01_auth_rbac_test.py -v`
- `pytest tests/m010_s01_auth_rbac_test.py -k "denied_log" -v`

## Observability / Diagnostics
- Runtime signals: structured auth-denial log events with error codes and subject/role metadata only
- Inspection surfaces: HTTP error responses (401/403) + API logs
- Failure visibility: error_code + required_roles list (403) and auth_reason (401)
- Redaction constraints: never log raw Authorization headers or JWTs

## Integration Closure
- Upstream surfaces consumed: `src/sps/api/routes/*`, `src/sps/api/main.py`, `src/sps/config.py`
- New wiring introduced in this slice: JWT auth dependency + RBAC role checks on router inclusion
- What remains before the milestone is truly usable end-to-end: service principal + mTLS enforcement (S02), redaction/read-only observability (S03)

## Tasks
- [x] **T01: Implement JWT identity validation + RBAC dependencies and wire routers** `est:3h`
  - Why: Establish the auth boundary and role checks required by R027/R028 across every API router.
  - Files: `src/sps/auth/identity.py`, `src/sps/auth/rbac.py`, `src/sps/config.py`, `src/sps/api/main.py`, `src/sps/api/routes/*.py`
  - Do: Add JWT settings + validation helpers, define identity/roles, implement `require_identity` and `require_roles`, and attach dependencies to all routers (including reviewer/ops pages) while removing reviewer API key gating.
  - Verify: `pytest tests/m010_s01_auth_rbac_test.py -k "auth_required or role_denied" -v`
  - Done when: Every router requires a valid JWT and role mismatches return 403 with explicit error codes.
- [x] **T02: Add integration tests for auth and RBAC gates** `est:2h`
  - Why: Prove the boundary contract: missing/invalid tokens are denied and role mapping works per router.
  - Files: `tests/m010_s01_auth_rbac_test.py`, `tests/helpers/auth_tokens.py`
  - Do: Add ASGI tests that generate JWTs, assert 401/403 error shapes, and confirm success for representative endpoints under correct roles.
  - Verify: `pytest tests/m010_s01_auth_rbac_test.py -v`
  - Done when: Tests cover missing token, invalid token, role denial, and allowed role access for each router category.

## Files Likely Touched
- `src/sps/auth/identity.py`
- `src/sps/auth/rbac.py`
- `src/sps/config.py`
- `src/sps/api/main.py`
- `src/sps/api/routes/cases.py`
- `src/sps/api/routes/evidence.py`
- `src/sps/api/routes/reviews.py`
- `src/sps/api/routes/reviewer_console.py`
- `src/sps/api/routes/contradictions.py`
- `src/sps/api/routes/dissents.py`
- `src/sps/api/routes/releases.py`
- `src/sps/api/routes/ops.py`
- `tests/m010_s01_auth_rbac_test.py`
- `tests/helpers/auth_tokens.py`
