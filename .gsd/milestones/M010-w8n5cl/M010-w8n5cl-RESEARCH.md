# M010-w8n5cl — Research

**Date:** 2026-03-16

## Summary
The codebase already has a lightweight auth dependency pattern (`require_reviewer_api_key`) and consistent router wiring for reviewer-owned and ops/release surfaces, but most core APIs (cases, evidence) are unauthenticated. There is no shared identity model, RBAC enforcement, or request-level auth context beyond the reviewer API key, and logging is plain `logging.basicConfig` without structured redaction hooks. The current design is ready for a single, centralized auth+RBAC dependency/middleware inserted in `sps.api.main` and reused across routers, but this must be done carefully to avoid breaking existing tests and runbooks that assume the API-key-only path.

Primary recommendation: start by defining a minimal identity token format and role mapping that can be validated locally without external identity providers (e.g., signed service principal tokens for service-to-service and a dev user token for interactive use), then enforce it via a shared FastAPI dependency that gates all API routers. Prove fail-closed behavior first with integration tests covering missing/invalid identity and role mis-match, then layer baseline mTLS/signed-principal checks for service calls and log redaction filters. This sequencing aligns with existing dependency injection patterns and minimizes operational risk while tightening the boundary.

## Recommendation
Implement a single auth boundary in the FastAPI app (dependency or middleware) that validates identity, extracts roles, and attaches an auth context used by RBAC checks in each router. Start by gating all existing API routes (cases/evidence/reviews/releases/ops/contradictions/dissents) and converting the current reviewer API key into a dev-only identity provider for the reviewer role, then add service-principal validation for service-to-service calls. After this, add log redaction and read-only observability checks to ensure no sensitive fields or mutating actions leak through ops/obs surfaces.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Token parsing/verification | FastAPI `Security` utilities + standard JWT/HMAC libs (PyJWT/Authlib) | Avoids subtle verification bugs and keeps claims validation consistent across services. |
| mTLS validation | Termination + cert propagation via proxy (Envoy/Traefik) or ASGI middleware that validates client cert headers | Avoids ad-hoc parsing of TLS details and keeps local dev/prod parity. |
| Log redaction | Logging filters/formatters with explicit allowlists | Prevents accidental sensitive data leakage from ad-hoc `logger.info` calls. |

## Existing Code and Patterns
- `src/sps/api/routes/reviews.py` — `require_reviewer_api_key` dependency is the existing auth gating pattern; can be generalized to identity+role checks.
- `src/sps/api/routes/ops.py` — Ops API router already depends on reviewer auth; UI uses an API key input in JS (`ops.js`).
- `src/sps/api/routes/releases.py` — Release endpoints gated by reviewer API key; pattern to extend to RBAC roles.
- `src/sps/api/routes/contradictions.py` / `src/sps/api/routes/dissents.py` — Reviewer-key dependency reuse across governance endpoints.
- `src/sps/api/routes/cases.py` / `src/sps/api/routes/evidence.py` — Core read/write endpoints are currently unauthenticated.
- `src/sps/config.py` — Only redaction is DSN password masking; reviewer API key configured here.
- `src/sps/workflows/worker.py` — Basic logging config with no redaction filters.

## Constraints
- Security controls must fail closed (milestone constraint). Anything that can’t validate identity must deny by default.
- Current tests and runbooks expect `X-Reviewer-Api-Key` to work; migration must preserve a compatibility path or update all proofs.
- Logging is currently configured via `logging.basicConfig` without filters; redaction needs to integrate at this layer or use structured logging wrappers.

## Common Pitfalls
- **Partial auth rollout** — Gating only reviewer endpoints leaves core write APIs (cases/evidence) open. Avoid by applying a global dependency or router-level dependency for all API routers.
- **Role confusion** — Reusing the reviewer API key without explicit role scoping risks authorizing cross-role operations. Avoid by mapping identities to roles and enforcing per-router role requirements.
- **Redaction gaps** — Existing log statements embed identifiers and request context; without filters, sensitive fields can leak. Avoid by adding a redaction filter and using allowlisted log payloads.
- **Observability mutation** — Ops/obs surfaces should remain read-only; guard against introducing POST/PUT paths on ops routers and ensure auth context restricts mutation.

## Open Risks
- Identity provider/token format choice could constrain future deployment (spec risk). Decide early and document migration path.
- Baseline mTLS in local dev may be painful without proxy tooling; ensure a signed-principal fallback that still fails closed.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available |
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| SQLAlchemy/Alembic | wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review | available |

## Sources
- Auth dependency pattern and reviewer API key gating (source: [src/sps/api/routes/reviews.py](src/sps/api/routes/reviews.py))
- Ops auth + dashboard endpoints (source: [src/sps/api/routes/ops.py](src/sps/api/routes/ops.py))
- Release endpoints gated by reviewer API key (source: [src/sps/api/routes/releases.py](src/sps/api/routes/releases.py))
- Core unauthenticated APIs (source: [src/sps/api/routes/cases.py](src/sps/api/routes/cases.py))
- Evidence API unauthenticated (source: [src/sps/api/routes/evidence.py](src/sps/api/routes/evidence.py))
- Settings + DSN redaction and API key config (source: [src/sps/config.py](src/sps/config.py))
- Logging configuration (source: [src/sps/workflows/worker.py](src/sps/workflows/worker.py))
- Ops dashboard client-side key usage (source: [src/sps/api/static/ops.js](src/sps/api/static/ops.js))
