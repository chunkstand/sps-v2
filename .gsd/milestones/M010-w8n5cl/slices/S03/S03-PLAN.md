# S03: Redaction + read-only observability with end-to-end proof

**Goal:** Centralize sensitive-field redaction across API/worker/CLI logging and prove observability surfaces remain read-only while authenticated service-principal access still works.
**Demo:** `scripts/verify_m010_s03.sh` shows service-principal + mTLS requests can read ops/release metrics, mutation attempts are rejected, and logs emitted during the runbook show redacted secrets.

## Must-Haves
- Central redaction filter sanitizes auth headers, JWTs, API keys, and DSN passwords across API/worker/CLI logging entrypoints.
- Observability endpoints under `/api/v1/ops` and `/api/v1/releases` stay GET-only and reject mutation attempts.
- End-to-end runbook proves auth/RBAC/mTLS + redaction together using real requests.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `tests/m010_s03_redaction_test.py`
- `python -m pytest tests/m010_s03_redaction_test.py -k redaction_failure_surface -v`
- `tests/m010_s03_observability_readonly_test.py`
- `bash scripts/verify_m010_s03.sh`

## Observability / Diagnostics
- Runtime signals: redaction filter applied to root logging handlers (log output contains `[REDACTED]` markers).
- Inspection surfaces: pytest caplog assertions + runbook log output.
- Failure visibility: unredacted token/secret substrings in captured log messages.
- Redaction constraints: Authorization headers, reviewer API keys, JWT secrets, database DSN passwords.

## Integration Closure
- Upstream surfaces consumed: `src/sps/auth/*` (identity + RBAC), `src/sps/workflows/worker.py`, `src/sps/workflows/cli.py`, `src/sps/api/main.py` logging setup.
- New wiring introduced in this slice: redaction filter attached to root logging handlers in API/worker/CLI entrypoints.
- What remains before the milestone is truly usable end-to-end: nothing.

## Tasks
- [x] **T01: Add centralized log redaction filter + tests** `est:1.5h`
  - Why: Ensures sensitive fields are consistently scrubbed across all runtime entrypoints.
  - Files: `src/sps/logging/redaction.py`, `src/sps/workflows/worker.py`, `src/sps/workflows/cli.py`, `src/sps/api/main.py`, `tests/m010_s03_redaction_test.py`
  - Do: Implement a redaction filter that scrubs message + extra fields, wire it into root logging configuration for API/worker/CLI, and add pytest coverage for common secrets (Authorization, API key, JWT secret, DSN password).
  - Verify: `python -m pytest tests/m010_s03_redaction_test.py -v`
  - Done when: Redaction tests pass and all entrypoints attach the filter to their handlers.
- [x] **T02: Prove read-only observability + end-to-end runbook** `est:1h`
  - Why: Confirms ops/release routes remain read-only under the new auth/mTLS boundaries and redaction is visible in real logs.
  - Files: `src/sps/api/routes/ops.py`, `src/sps/api/routes/releases.py`, `tests/m010_s03_observability_readonly_test.py`, `scripts/verify_m010_s03.sh`
  - Do: Add negative tests that POST/PUT/PATCH/DELETE on ops/release endpoints are rejected, update runbook to call metrics with service-principal JWT + mTLS header and attempt mutation, and ensure runbook log output demonstrates redaction.
  - Verify: `python -m pytest tests/m010_s03_observability_readonly_test.py -v` and `bash scripts/verify_m010_s03.sh`
  - Done when: Mutation attempts are denied in tests and the runbook passes with redacted log output.

## Files Likely Touched
- `src/sps/logging/redaction.py`
- `src/sps/workflows/worker.py`
- `src/sps/workflows/cli.py`
- `src/sps/api/main.py`
- `src/sps/api/routes/ops.py`
- `src/sps/api/routes/releases.py`
- `tests/m010_s03_redaction_test.py`
- `tests/m010_s03_observability_readonly_test.py`
- `scripts/verify_m010_s03.sh`
