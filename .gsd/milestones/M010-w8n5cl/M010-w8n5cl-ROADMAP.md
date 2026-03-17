# M010-w8n5cl: Phase 10 — security boundaries (auth/RBAC/mTLS/redaction)

**Vision:** All SPS API surfaces require authenticated identities with enforced role separation, service-to-service calls are authenticated with signed principals and baseline mTLS checks, and observability/logging paths never leak sensitive data or mutate authority.

## Success Criteria
- All interactive and service APIs reject requests without a valid identity token.
- Role mismatches are denied on protected surfaces with explicit, inspectable error responses.
- Service-to-service calls are accepted only with a signed service principal and baseline mTLS signal present.
- Logs and observability outputs redact sensitive fields and no observability endpoint allows mutation.

## Key Risks / Unknowns
- Token format choice could constrain future identity provider integration — must be minimal but extensible.
- Baseline mTLS enforcement in local dev could be brittle without proxy support — need a reliable fallback that still fails closed.
- Redaction gaps in existing logging could leak sensitive payloads if not centrally filtered.

## Proof Strategy
- Token/RBAC risk → retire in S01 by enforcing auth+roles across real routers and proving denials/acceptance in integration tests.
- Service principal + mTLS risk → retire in S02 by exercising signed principal flow (including failure paths) against live API entrypoints.
- Redaction/read-only risk → retire in S03 by running an end-to-end runbook that inspects logs and verifies observability endpoints reject mutation.

## Verification Classes
- Contract verification: pytest security/auth tests covering auth header validation, RBAC denials, redaction filter behavior.
- Integration verification: docker-compose runbook exercising authenticated API calls, service principal flow, and mTLS header enforcement.
- Operational verification: runbook step to restart API/worker and re-verify auth gates still fail closed.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slice deliverables are complete.
- Auth/RBAC, service principal validation, and redaction filters are wired into the FastAPI entrypoint and used by all routers.
- The real API entrypoints are exercised with missing/invalid identity, role mismatch, and service principal scenarios.
- Success criteria are re-checked against live behavior, not just artifacts.
- Final integrated acceptance scenarios (auth + RBAC + service principal + redaction) pass in a real environment.

## Requirement Coverage
- Covers: R027, R028, R029, R031
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices
- [x] **S01: Authenticated identity + RBAC gate for all API routers** `risk:high` `depends:[]`
  > After this: API endpoints (cases, evidence, reviews, ops, releases) deny missing/invalid identities and enforce role-based access via real requests/tests.
- [ ] **S02: Service principal authentication with baseline mTLS signal** `risk:medium` `depends:[S01]`
  > After this: service-to-service calls using signed principals (and required mTLS signal) succeed while invalid/absent principals or mTLS signals are denied.
- [ ] **S03: Redaction + read-only observability with end-to-end proof** `risk:low` `depends:[S02]`
  > After this: logs redact sensitive fields, observability endpoints remain read-only, and a live runbook proves auth/RBAC/mTLS/redaction together.

## Boundary Map
### S01 → S02
Produces:
- Identity token validation contract (claims schema, issuer/audience validation) and request auth context.
- RBAC role mapping applied to all FastAPI routers.

Consumes:
- nothing (first slice)

### S02 → S03
Produces:
- Signed service principal validation contract and required mTLS signal headers.
- Service-role authorization path for automated clients (release/ops tooling).

Consumes:
- Auth context + RBAC gates from S01.
