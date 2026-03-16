# M010-w8n5cl: Phase 10 — security boundaries (auth/RBAC/mTLS/redaction) — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement security boundaries for SPS APIs and services: authenticated identities, RBAC separation, baseline mTLS support for service principals, log redaction, and read-only observability enforcement. This milestone applies to existing API surfaces and workflows built in prior phases.

## Why This Milestone

The spec requires authenticated identities, role separation, service-to-service authentication, and protection against sensitive data leakage. Without these controls, SPS violates Tier 3 security requirements and risks authority drift via observability paths.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Access APIs only with authenticated identities and role-appropriate permissions.
- Observe that logs are redacted and observability paths cannot mutate authoritative state.

### Entry point / environment

- Entry point: API services + policy configuration
- Environment: local dev + CI
- Live dependencies involved: Postgres, API stack

## Completion Class

- Contract complete means: auth/RBAC policies and redaction rules validate against spec.
- Integration complete means: real API calls enforce auth/RBAC and mTLS expectations in integration tests.
- Operational complete means: runbook and tests verify redaction and read-only observability constraints.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Authenticated identities are required for interactive and service APIs.
- RBAC separation denies cross-role operations.
- Service-to-service calls enforce mTLS or signed principals (baseline support).
- Logs redact sensitive fields and observability surfaces are read-only.

## Risks and Unknowns

- Auth integration risk — selecting identity provider or token format may constrain future deployment.
- mTLS baseline risk — local dev support must be practical without weakening production policy.

## Existing Codebase / Prior Art

- `src/sps/api/main.py` — FastAPI entrypoint for auth middleware insertion.
- `specs/sps/build-approved/spec.md` — SEC-001..SEC-005 requirements.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R027 — Authenticated identities on interactive and service APIs (SEC-001).
- R028 — RBAC separation across roles (SEC-002).
- R029 — Sensitive field redaction and read-only observability (SEC-003/OBS-004).
- R030 — Legal hold enforcement already exists (SEC-004) — ensure no regressions.
- R031 — Service-to-service mTLS and signed principals (SEC-005).

## Scope

### In Scope

- Auth middleware and identity validation for API surfaces.
- RBAC policy enforcement for key roles.
- Baseline mTLS/signed principal support for service-to-service calls.
- Log redaction and read-only observability enforcement.
- Integration tests + operator runbook proving security controls.

### Out of Scope / Non-Goals

- Full enterprise SSO integrations beyond baseline.
- Advanced SIEM integrations.
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Security controls must fail closed.
- Redaction must never log secrets or high-sensitivity fields.

## Integration Points

- API stack — auth/RBAC middleware.
- Observability stack — read-only enforcement and redaction.
- CI — security tests.

## Open Questions

- Which identity provider or token format should be used in local dev? — decide during planning.
