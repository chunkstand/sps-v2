# S03: Redaction + read-only observability with end-to-end proof — UAT

**Milestone:** M010-w8n5cl
**Written:** 2026-03-16

## UAT Type
- UAT mode: live-runtime
- Why this mode is sufficient: The slice proves runtime redaction and read-only enforcement using a live API + service-principal JWT; manual inspection of runbook output validates the core requirement.

## Preconditions
- API server running locally on `http://localhost:8000` (e.g., `python -m uvicorn sps.api.main:app --port 8000`).
- `.venv` installed with repo dependencies.
- Default auth settings (service-principal JWT secret, mTLS signal header) match test helpers in `tests/helpers/auth_tokens.py`.

## Smoke Test
- Run `bash scripts/verify_m010_s03.sh` and confirm it exits 0 with `runbook.pass: redaction_confirmed` in output.

## Test Cases

### 1. Service-principal read-only access works
1. Run `bash scripts/verify_m010_s03.sh`.
2. Observe `runbook: ops_metrics_ok` and `runbook: release_blockers_ok` in stderr output.
3. **Expected:** Both GET requests succeed (HTTP 200) with no auth denials.

### 2. Mutation attempts are rejected
1. Run `bash scripts/verify_m010_s03.sh`.
2. Locate `runbook: ops_mutation_rejected status=405` in stderr output.
3. **Expected:** Mutation attempt returns 405 (read-only enforcement).

### 3. Redaction output scrubs secrets
1. Run `bash scripts/verify_m010_s03.sh`.
2. Inspect the `INFO runbook.redaction ...` log line.
3. **Expected:** Authorization token and reviewer API key are replaced with `[REDACTED]` and the raw token is not present in output.

## Edge Cases

### Missing mTLS signal
1. Run `curl -sS -o /tmp/m010_s03_missing_mtls -w "%{http_code}" \
  -H "Authorization: Bearer <service-principal-token>" \
  http://localhost:8000/api/v1/ops/dashboard/metrics`.
2. **Expected:** Request is rejected (non-200) with an auth/mTLS denial response.

## Failure Signals
- `runbook.fail:` lines from `scripts/verify_m010_s03.sh`.
- Any log output that includes an unredacted JWT, API key, or password substring.
- Mutation attempts returning 200/201 or any success status.

## Requirements Proved By This UAT
- R029 — Sensitive field redaction + read-only observability.

## Not Proven By This UAT
- Auth/RBAC/mTLS baseline enforcement on all routers beyond ops/release read surfaces (covered by earlier slices/tests).

## Notes for Tester
- The runbook expects the API server to already be running; it does not start or stop uvicorn.
- The service-principal token used in UAT is generated via repo test helpers and should not be reused outside local dev.
