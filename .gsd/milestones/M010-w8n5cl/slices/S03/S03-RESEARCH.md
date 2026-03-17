# M010-w8n5cl S03 — Research

**Date:** 2026-03-16

## Summary
S03 owns R029 (Sensitive field redaction + read-only observability). The current codebase has no centralized redaction filter and relies on `logging.basicConfig` in worker/CLI, with FastAPI/uvicorn logging likely inheriting defaults. There is a DSN redaction helper in `Settings`, but it is not wired into logging, and no log filtering exists for auth headers or secrets. Ops/release observability endpoints are GET-only and already role-gated, but the ops dashboard client still sends the legacy `X-Reviewer-Api-Key`, which is now incompatible with service-principal + JWT auth; any runbook must use Authorization bearer + mTLS header.

Primary recommendation: add a logging Filter (or formatter wrapper) that redacts known sensitive fields from log records and apply it in all logging configuration entrypoints (API, worker, CLI, tests). Pair this with tests that assert redaction and an end-to-end runbook that exercises authenticated requests and verifies both redacted logs and read-only observability responses. This approach keeps redaction centralized and fail-closed without needing to audit every log call.

## Recommendation
Implement a centralized redaction layer that sanitizes log record messages and extra fields, then wire it into all places that call `logging.basicConfig` and into FastAPI startup (e.g., a shared logging configuration helper). Add tests that emit logs containing known secret fields (Authorization, reviewer API key, JWT secret, database password) and assert the redacted output, plus integration coverage that ops/release endpoints remain GET-only and reject mutation attempts. Update the runbook to call ops metrics with a service-principal JWT + mTLS signal header and verify logs do not leak secrets.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Logging configuration | `logging.basicConfig` entrypoints already in worker/CLI | Extend existing configuration points with filters instead of building a custom logging framework. |
| Redaction of DSN credentials | `Settings.redacted_postgres_dsn()` | Reuse the helper when logging DB config and avoid reimplementing DSN parsing. |

## Existing Code and Patterns
- `src/sps/config.py` — provides `redacted_postgres_dsn()` and documents that auth secrets must never be logged; use this as the canonical redaction helper.
- `src/sps/workflows/worker.py` — configures logging via `logging.basicConfig`; add redaction filters here.
- `src/sps/workflows/cli.py` — configures logging via `logging.basicConfig`; add redaction filters here.
- `src/sps/api/routes/ops.py` — ops metrics + release blockers are GET-only; keep read-only pattern and add negative tests for mutation attempts.
- `src/sps/api/static/ops.js` — still uses `X-Reviewer-Api-Key`; update runbooks/tests to use JWT + mTLS header for ops metrics.

## Constraints
- Security controls must fail closed; redaction must never allow raw secrets or tokens to be logged.
- Service principal access requires the mTLS signal header (`Settings.auth_mtls_signal_header`), so runbooks and tests must include it.

## Common Pitfalls
- **Partial redaction** — filtering only some loggers leaves uvicorn/default handlers leaking secrets; apply filters at the root handler level.
- **Observability mutation creep** — adding POST/PUT endpoints under `/api/v1/ops` or `/api/v1/releases` defeats read-only guarantees; enforce GET-only and add explicit negative tests.

## Open Risks
- The ops dashboard client still uses `X-Reviewer-Api-Key`; if not updated in tests/runbooks, ops metrics calls will fail under the service-principal auth gate.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available |
| Logging | terrylica/cc-skills@python-logging-best-practices | available |
| PyJWT | none found | none found |

## Sources
- Redaction helper and auth secret handling notes (source: [src/sps/config.py](src/sps/config.py))
- Logging configuration entrypoints (source: [src/sps/workflows/worker.py](src/sps/workflows/worker.py))
- CLI logging configuration (source: [src/sps/workflows/cli.py](src/sps/workflows/cli.py))
- Ops routes are GET-only and role/service-principal gated (source: [src/sps/api/routes/ops.py](src/sps/api/routes/ops.py))
- Ops dashboard still sends reviewer API key header (source: [src/sps/api/static/ops.js](src/sps/api/static/ops.js))
