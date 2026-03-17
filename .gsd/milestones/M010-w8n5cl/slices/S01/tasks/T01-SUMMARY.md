---
id: T01
parent: S01
milestone: M010-w8n5cl
provides:
  - JWT identity validation + RBAC dependencies applied across all API and page routers
key_files:
  - src/sps/auth/identity.py
  - src/sps/auth/rbac.py
  - src/sps/api/routes/reviews.py
  - tests/m010_s01_auth_rbac_test.py
key_decisions:
  - Router-level RBAC role mapping with ADMIN override (see DECISIONS #92)
patterns_established:
  - require_roles dependency wraps require_identity and emits structured denial logs
observability_surfaces:
  - api.auth.denied structured log + 401/403 error detail payloads
duration: 1h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Implement JWT identity validation + RBAC dependencies and wire routers

**Implemented JWT-backed identity validation and router-level RBAC guards with structured denial logging.**

## What Happened
- Added JWT auth settings plus identity validation helpers and a role-based dependency layer that emits `api.auth.denied` without leaking tokens.
- Replaced reviewer API key gating by wiring RBAC requirements into every router (cases, evidence, reviews, contradictions, dissents, releases, ops, reviewer console) with explicit role mapping and admin override.
- Added auth/RBAC tests including denial log verification.

## Verification
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "auth_required or role_denied" -v`
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -v`
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "denied_log" -v`

## Diagnostics
- Inspect `api.auth.denied` log events for auth failures.
- 401 responses include `detail.auth_reason`; 403 responses include `detail.error_code` + `detail.required_roles`.

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `src/sps/auth/__init__.py` — auth module init.
- `src/sps/auth/identity.py` — JWT validation + identity parsing.
- `src/sps/auth/rbac.py` — RBAC roles, dependencies, and denial logging.
- `src/sps/config.py` — JWT settings added.
- `src/sps/api/routes/cases.py` — INTAKE role guard.
- `src/sps/api/routes/evidence.py` — INTAKE role guard.
- `src/sps/api/routes/reviews.py` — reviewer role guard replacing API key.
- `src/sps/api/routes/contradictions.py` — reviewer role guard.
- `src/sps/api/routes/dissents.py` — reviewer role guard.
- `src/sps/api/routes/releases.py` — release role guard.
- `src/sps/api/routes/ops.py` — ops role guard for API + page.
- `src/sps/api/routes/reviewer_console.py` — reviewer role guard.
- `pyproject.toml` — added PyJWT dependency.
- `tests/helpers/auth_tokens.py` — JWT test helper.
- `tests/m010_s01_auth_rbac_test.py` — auth/RBAC enforcement tests.
- `.gsd/DECISIONS.md` — appended RBAC role mapping decision.
