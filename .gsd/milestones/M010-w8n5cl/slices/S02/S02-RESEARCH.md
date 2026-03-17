# M010-w8n5cl S02 — Research

**Date:** 2026-03-16

## Summary
S02 owns R031 (service-to-service mTLS + signed principals). The current auth stack only validates HMAC JWTs via `Authorization: Bearer` and enforces router-level RBAC with role claims; there is no service principal claim shape, no mTLS signal check, and no config for client-cert headers. This means the slice must introduce both a service principal validation contract and a baseline mTLS signal requirement while preserving the existing JWT validation path and fail-closed semantics.

The most practical approach is to extend the auth layer (not per-route) with a service-principal-specific dependency or policy helper that (1) validates JWTs for a `service_principal` identity type/claim, (2) requires an explicit mTLS signal header (e.g., forwarded client cert), and (3) maps service principals to the existing Role enum for downstream RBAC. This keeps the router-level `require_roles` dependencies unchanged while adding the additional gate only on service-to-service routes or callers. Local dev can use a deterministic header + token to pass the gate, but absence or malformed header must still deny.

## Recommendation
Add a service-principal validator alongside `validate_jwt_identity` that enforces a specific claim (e.g., `principal_type=service_principal` or `actor_type=service_principal`), then layer a `require_service_principal` dependency that checks both the JWT and a required mTLS signal header (likely `X-Forwarded-Client-Cert` or a configurable header) before returning an Identity. Wire this dependency into the service-to-service surfaces (ops/release automation endpoints, internal service callers) or into a dedicated route group for service APIs. Keep the RBAC role checks unchanged by mapping the validated service principal to existing `Role` values. Document and test the fail-closed behavior when the token is missing/invalid or the mTLS header is absent/empty.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| JWT verification | PyJWT decode + issuer/audience/exp checks already in `validate_jwt_identity` | Keeps token validation consistent and avoids subtle signature/claim bugs. |
| mTLS signal parsing | Proxy-injected client-cert header (Envoy/Traefik pattern) | Avoids direct TLS parsing in app code and preserves parity with production TLS termination. |
| RBAC enforcement | `require_roles` dependency in `sps.auth.rbac` | Centralized auth/role enforcement keeps router wiring uniform and auditable. |

## Existing Code and Patterns
- `src/sps/auth/identity.py` — HMAC JWT validation and Identity model; extend here for service principal claim shape.
- `src/sps/auth/rbac.py` — `require_identity` + `require_roles` dependency pattern and denied-log emission; add service-principal + mTLS checks adjacent to this dependency layer.
- `src/sps/config.py` — auth settings (issuer/audience/secret/algorithm) with no mTLS header config yet; add config for required mTLS signal header.
- `tests/helpers/auth_tokens.py` — JWT builder for tests; extend to emit service principal claim variants for S02 tests.

## Constraints
- Fail-closed behavior is mandatory for auth checks (missing/invalid token or missing mTLS signal must 401/403).
- No existing mTLS signal or service-principal claim format is defined in code; S02 must establish this contract and ensure local dev can exercise it.

## Common Pitfalls
- **Role confusion for service principals** — forgetting to map service principals to explicit roles leads to unintended access. Require explicit roles in the JWT claims and enforce via `require_roles`.
- **mTLS header optionality** — treating the header as optional (or allowing empty values) silently weakens SEC-005. Deny on missing/empty header.

## Open Risks
- Choosing the wrong mTLS header name could make local dev brittle if the proxy layer later differs; make it configurable via Settings and document the expected header.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available |
| mTLS | wshobson/agents@mtls-configuration | available (not installed) |
| PyJWT | none found | none found |

## Sources
- JWT validation and Identity model (source: [src/sps/auth/identity.py](src/sps/auth/identity.py))
- Auth dependency + RBAC enforcement pattern (source: [src/sps/auth/rbac.py](src/sps/auth/rbac.py))
- Auth settings (source: [src/sps/config.py](src/sps/config.py))
- JWT test helper (source: [tests/helpers/auth_tokens.py](tests/helpers/auth_tokens.py))
- Spec requirement for service principals + mTLS (source: [specs/sps/build-approved/spec.md](specs/sps/build-approved/spec.md))
