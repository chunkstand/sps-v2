---
id: S01
parent: M010-w8n5cl
milestone: M010-w8n5cl
provides:
  - JWT-authenticated identity enforcement with RBAC gates on every API/page router
requires: []
affects:
  - S02
key_files:
  - src/sps/auth/identity.py
  - src/sps/auth/rbac.py
  - src/sps/api/main.py
  - src/sps/api/routes/cases.py
  - src/sps/api/routes/evidence.py
  - src/sps/api/routes/reviews.py
  - src/sps/api/routes/contradictions.py
  - src/sps/api/routes/dissents.py
  - src/sps/api/routes/releases.py
  - src/sps/api/routes/ops.py
  - src/sps/api/routes/reviewer_console.py
  - tests/m010_s01_auth_rbac_test.py
key_decisions:
  - RBAC role mapping by router with ADMIN override (DECISIONS #92)
patterns_established:
  - Router-level dependencies apply require_identity + require_roles with structured auth-denied logs
observability_surfaces:
  - api.auth.denied structured log events (validated in tests)
drill_down_paths:
  - .gsd/milestones/M010-w8n5cl/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M010-w8n5cl/slices/S01/tasks/T02-SUMMARY.md
duration: 2h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Authenticated identity + RBAC gate for all API routers

**JWT identity validation and RBAC gates now protect every API/page router with explicit 401/403 responses and structured denial logs.**

## What Happened
JWT validation was added to establish authenticated identities, then RBAC role checks were wired into every FastAPI router (cases, evidence, reviews, contradictions, dissents, releases, ops, reviewer console) with an admin override. Reviewer API key gating was replaced by the role-based dependency layer, and integration tests now prove missing/invalid token denials, role mismatches, and allowed access per router, including structured `api.auth.denied` log emission.

## Verification
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -v`
- `.venv/bin/python -m pytest tests/m010_s01_auth_rbac_test.py -k "denied_log" -v`

## Requirements Advanced
- R027 — Authenticated identity enforcement is now applied across all routers with JWT validation.
- R028 — Router-level RBAC mapping enforces role separation with explicit denials.

## Requirements Validated
- R027 — Proved by `tests/m010_s01_auth_rbac_test.py` covering missing/invalid token denials and allowed access.
- R028 — Proved by `tests/m010_s01_auth_rbac_test.py` covering role mismatch denials and allowed role access.

## New Requirements Surfaced
- none

## Requirements Invalidated or Re-scoped
- none

## Deviations
- none

## Known Limitations
- Service principal authentication + baseline mTLS enforcement are deferred to S02.
- Redaction/read-only observability enforcement is deferred to S03.

## Follow-ups
- none

## Files Created/Modified
- `src/sps/auth/identity.py` — JWT validation and identity parsing.
- `src/sps/auth/rbac.py` — RBAC roles, dependencies, and denial logging.
- `src/sps/config.py` — JWT settings.
- `src/sps/api/main.py` — router wiring with auth dependencies.
- `src/sps/api/routes/*.py` — per-router RBAC enforcement.
- `tests/helpers/auth_tokens.py` — JWT test helper.
- `tests/m010_s01_auth_rbac_test.py` — integration coverage for auth/RBAC gates.

## Forward Intelligence
### What the next slice should know
- JWT validation is HMAC-based with issuer/audience checks; use the same Settings fields for service principal extensions in S02.

### What's fragile
- Test JWT secrets are short, so PyJWT emits key-length warnings; production secrets must be ≥32 bytes to avoid weak-HMAC warnings.

### Authoritative diagnostics
- `tests/m010_s01_auth_rbac_test.py::test_denied_log_emitted` — verifies `api.auth.denied` log events and error payload shape.

### What assumptions changed
- Reviewer/ops surfaces are now gated by roles, not API keys; any tooling still relying on the API key must be updated.
