---
id: S02
parent: M010-w8n5cl
milestone: M010-w8n5cl
provides:
  - service principal auth dependency with baseline mTLS enforcement
requires:
  - slice: S01
    provides: authenticated identity validation + RBAC role gates across routers
affects:
  - S03
key_files:
  - src/sps/auth/identity.py
  - src/sps/auth/rbac.py
  - src/sps/config.py
  - src/sps/api/routes/ops.py
  - src/sps/api/routes/releases.py
  - tests/helpers/auth_tokens.py
  - tests/m010_s02_service_principal_auth_test.py
key_decisions:
  - Extend validate_jwt_identity with expected_principal_type to enforce service principals
  - Require configurable mTLS signal header for service principal access
patterns_established:
  - require_service_principal enforces principal_type + mTLS signal with explicit auth_reason payloads
observability_surfaces:
  - api.auth.denied structured log records with auth_reason for service principal or mTLS failures
  - HTTP 401 payloads include detail.auth_reason and guard identifiers
  - pytest tests/m010_s02_service_principal_auth_test.py
drill_down_paths:
  - .gsd/milestones/M010-w8n5cl/slices/S02/tasks/T01-SUMMARY.md
duration: 1h
verification_result: passed
completed_at: 2026-03-16
---

# S02: Service principal authentication with baseline mTLS signal

**Service principal JWTs now require an explicit principal_type claim plus a configurable mTLS signal header on service routes, with allow/deny coverage in integration tests.**

## What Happened
Service principal validation was added to the existing JWT identity pipeline and wired into the ops and release routers via a new require_service_principal dependency. The dependency enforces principal_type=service_principal, checks for the configured mTLS signal header, and returns explicit auth_reason payloads while emitting api.auth.denied logs. Test helpers now issue service principal tokens, and new integration tests cover valid access plus missing/invalid principal claims and missing mTLS headers.

## Verification
- `.venv/bin/python -m pytest tests/m010_s02_service_principal_auth_test.py -v`
- `rg "api.auth.denied" -n tests/m010_s02_service_principal_auth_test.py`

## Requirements Advanced
- R031 — Implemented service principal validation and mTLS signal enforcement for service-to-service access.

## Requirements Validated
- R031 — pytest coverage proves allow/deny paths for signed service principals with required mTLS signal headers.

## New Requirements Surfaced
- None.

## Requirements Invalidated or Re-scoped
- None.

## Deviations
None.

## Known Limitations
Baseline mTLS enforcement is header-based only; no real TLS client certificate verification is performed yet.

## Follow-ups
None.

## Files Created/Modified
- `src/sps/auth/identity.py` — added service principal claim validation hook
- `src/sps/auth/rbac.py` — added require_service_principal dependency with mTLS enforcement
- `src/sps/config.py` — added configurable mTLS signal header setting
- `src/sps/api/routes/ops.py` — wired service principal dependency into ops routes
- `src/sps/api/routes/releases.py` — wired service principal dependency into release routes
- `tests/helpers/auth_tokens.py` — added service principal JWT helper and extra claims support
- `tests/m010_s02_service_principal_auth_test.py` — allow/deny coverage for service principal + mTLS enforcement

## Forward Intelligence
### What the next slice should know
- mTLS signal enforcement is purely header-based and uses Settings.SPS_MTLS_SIGNAL_HEADER (default X-Forwarded-Client-Cert).

### What's fragile
- Service principal auth depends on the proxy injecting the configured header; missing proxy config will fail closed.

### Authoritative diagnostics
- `tests/m010_s02_service_principal_auth_test.py` — direct allow/deny coverage of principal_type and mTLS header enforcement.
- `api.auth.denied` log records — trustworthy for distinguishing missing_principal_type, invalid_principal_type, and missing_mtls_signal.

### What assumptions changed
- Assumed a new identity type was needed — reusing validate_jwt_identity with expected_principal_type proved sufficient.
