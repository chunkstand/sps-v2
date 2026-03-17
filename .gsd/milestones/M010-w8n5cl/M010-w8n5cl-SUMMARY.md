---
id: M010-w8n5cl
provides:
  - Authenticated identity enforcement with RBAC gates, service-principal mTLS validation, and centralized log redaction/read-only observability
key_decisions:
  - Use HMAC-signed JWTs with role claims for baseline identity enforcement and service principals
  - Require service principal `principal_type=service_principal` and a configurable mTLS signal header
  - Attach a shared redaction logging.Filter to root handlers across entrypoints
patterns_established:
  - Router-level auth dependencies enforce `require_identity` + `require_roles` with structured denial logs
  - `require_service_principal` enforces principal type + mTLS signal and emits auth_reason payloads
  - Entry points call `attach_redaction_filter()` after logging config to scrub secrets
observability_surfaces:
  - `api.auth.denied` structured log events with auth_reason payloads
  - Redacted log output via `attach_redaction_filter()` across API/worker/CLI
  - `scripts/verify_m010_s03.sh` runbook proving service-principal+mTLS + redaction in live API
requirement_outcomes:
  - id: R027
    from_status: active
    to_status: validated
    proof: pytest tests/m010_s01_auth_rbac_test.py -v (missing/invalid token denials + allowed access)
  - id: R028
    from_status: active
    to_status: validated
    proof: pytest tests/m010_s01_auth_rbac_test.py -v (role mismatch denials + allowed role access)
  - id: R031
    from_status: active
    to_status: validated
    proof: pytest tests/m010_s02_service_principal_auth_test.py -v (service principal + mTLS signal allow/deny)
  - id: R029
    from_status: active
    to_status: validated
    proof: pytest tests/m010_s03_redaction_test.py -v, pytest tests/m010_s03_observability_readonly_test.py -v, scripts/verify_m010_s03.sh

duration: 4.4h
verification_result: passed
completed_at: 2026-03-16
---

# M010-w8n5cl: Phase 10 — security boundaries (auth/RBAC/mTLS/redaction)

**Authenticated identities and RBAC gates, service-principal mTLS enforcement, and centralized log redaction/read-only observability are live and proven by tests + runbook.**

## What Happened

Phase 10 established the security boundary across all API surfaces by introducing JWT identity validation and RBAC role enforcement on every router, replacing ad-hoc API key checks with structured auth dependencies. Service-to-service access was then hardened by extending the identity pipeline to accept only service principal tokens with explicit `principal_type` claims and a configurable mTLS signal header, wired into ops and release routes. Finally, a centralized redaction filter was attached to all runtime entrypoints (API, worker, CLI) and observability endpoints were verified read-only, with a live runbook proving redaction and denial behavior under a service-principal+mTLS call.

## Cross-Slice Verification

- **Authenticated identities required across interactive/service APIs:** `pytest tests/m010_s01_auth_rbac_test.py -v` covers missing/invalid token denials and allowed access.
- **RBAC role mismatches denied on protected surfaces:** `pytest tests/m010_s01_auth_rbac_test.py -v` covers role mismatch denials and admin overrides.
- **Service-to-service calls require signed principal + mTLS signal:** `pytest tests/m010_s02_service_principal_auth_test.py -v` validates principal_type enforcement and missing mTLS denials.
- **Logs redact sensitive fields + observability is read-only:** `pytest tests/m010_s03_redaction_test.py -v`, `pytest tests/m010_s03_observability_readonly_test.py -v`, and `scripts/verify_m010_s03.sh` confirm redacted log output and mutation rejection in a live API.

## Requirement Changes

- R027: active → validated — `pytest tests/m010_s01_auth_rbac_test.py -v`
- R028: active → validated — `pytest tests/m010_s01_auth_rbac_test.py -v`
- R031: active → validated — `pytest tests/m010_s02_service_principal_auth_test.py -v`
- R029: active → validated — `pytest tests/m010_s03_redaction_test.py -v`, `pytest tests/m010_s03_observability_readonly_test.py -v`, `scripts/verify_m010_s03.sh`

## Forward Intelligence

### What the next milestone should know
- mTLS enforcement is header-based (`SPS_MTLS_SIGNAL_HEADER` default `X-Forwarded-Client-Cert`) and fails closed when the proxy does not inject the header.
- Redaction is only guaranteed when entrypoints call `attach_redaction_filter()` after logging configuration.

### What's fragile
- `scripts/verify_m010_s03.sh` assumes a running API on `localhost:8000`; forgetting to start it fails before any redaction checks.

### Authoritative diagnostics
- `tests/m010_s02_service_principal_auth_test.py` — single source for principal_type + mTLS enforcement expectations.
- `tests/m010_s03_redaction_test.py` — caplog assertions for redaction behavior across common secret patterns.

### What assumptions changed
- Reviewer/ops/release access moved from API keys to role-based JWTs; tooling must send role-appropriate tokens instead of API keys.

## Files Created/Modified

- `src/sps/auth/identity.py` — JWT identity validation with service principal claim support.
- `src/sps/auth/rbac.py` — RBAC role dependencies + `require_service_principal` guard.
- `src/sps/logging/redaction.py` — shared redaction filter attached to entrypoints.
- `src/sps/api/main.py` — auth dependency wiring + redaction filter attachment.
- `src/sps/api/routes/ops.py` — service principal + read-only enforcement.
- `src/sps/api/routes/releases.py` — service principal + read-only enforcement.
- `tests/m010_s01_auth_rbac_test.py` — auth/RBAC integration verification.
- `tests/m010_s02_service_principal_auth_test.py` — service principal + mTLS verification.
- `tests/m010_s03_redaction_test.py` — log redaction verification.
- `tests/m010_s03_observability_readonly_test.py` — read-only observability enforcement verification.
- `scripts/verify_m010_s03.sh` — live runbook proving service principal + redaction behavior.
