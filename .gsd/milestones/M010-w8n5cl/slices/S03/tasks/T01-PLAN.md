---
estimated_steps: 5
estimated_files: 5
---

# T01: Add centralized log redaction filter + tests

**Slice:** S03 — Redaction + read-only observability with end-to-end proof
**Milestone:** M010-w8n5cl

## Description
Implement a shared logging redaction filter that scrubs sensitive fields from log records and wire it into API/worker/CLI logging entrypoints, with pytest coverage that proves common secrets are redacted.

## Steps
1. Add a redaction filter/helper module that sanitizes log record messages and extra fields, using existing Settings helpers where applicable.
2. Attach the redaction filter to root logging handlers in API, worker, and CLI entrypoints.
3. Ensure the filter handles common secret patterns (Authorization header, API keys, JWT secrets, DSN passwords) in strings and dict-like payloads.
4. Add pytest coverage using caplog to assert redaction behavior for representative secrets.
5. Run the redaction test to confirm the filter is active and working.

## Must-Haves
- [ ] Redaction filter scrubs message + extra field payloads without leaking sensitive substrings.
- [ ] Logging entrypoints for API/worker/CLI attach the filter to root handlers.

## Verification
- `python -m pytest tests/m010_s03_redaction_test.py -v`

## Observability Impact
- Signals added/changed: log output includes `[REDACTED]` markers for sensitive fields.
- How a future agent inspects this: pytest caplog assertions in `tests/m010_s03_redaction_test.py`.
- Failure state exposed: unredacted secrets visible in log messages.

## Inputs
- `src/sps/config.py` — redacted DSN helper + guidance on secret handling.
- `src/sps/workflows/worker.py` — current logging configuration entrypoint.

## Expected Output
- `src/sps/logging/redaction.py` — shared redaction filter/helper.
- `src/sps/workflows/worker.py` and `src/sps/workflows/cli.py` — logging configuration updated with redaction filter.
- `src/sps/api/main.py` — logging wiring updated to include filter.
- `tests/m010_s03_redaction_test.py` — caplog tests for redaction behavior.
