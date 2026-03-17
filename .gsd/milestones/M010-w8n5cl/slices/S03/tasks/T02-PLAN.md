---
estimated_steps: 5
estimated_files: 4
---

# T02: Prove read-only observability + end-to-end runbook

**Slice:** S03 — Redaction + read-only observability with end-to-end proof
**Milestone:** M010-w8n5cl

## Description
Add negative tests proving ops/release endpoints reject mutation attempts and update the end-to-end runbook to use service-principal auth + mTLS while demonstrating redacted logs.

## Steps
1. Add pytest coverage to attempt POST/PUT/PATCH/DELETE against ops and release routes and assert the denials (405/403) with auth headers present.
2. Update the runbook script to call metrics with a service-principal JWT and required mTLS signal header.
3. Add a runbook mutation attempt that should be rejected and capture log output for redaction inspection.
4. Ensure the runbook uses Authorization bearer tokens (not legacy reviewer API keys).
5. Run the new tests and runbook to confirm read-only enforcement and log redaction.

## Must-Haves
- [ ] Ops/release mutation attempts are denied even with valid service-principal auth.
- [ ] Runbook demonstrates authenticated read-only access and redacted log output.

## Verification
- `python -m pytest tests/m010_s03_observability_readonly_test.py -v`
- `bash scripts/verify_m010_s03.sh`

## Observability Impact
- Signals added/changed: read-only denial responses for mutation attempts; runbook log output with redaction.
- How a future agent inspects this: pytest assertions + runbook stdout.
- Failure state exposed: mutation requests unexpectedly succeed or logs show unredacted secrets.

## Inputs
- `src/sps/api/routes/ops.py` — existing GET-only ops endpoints.
- `src/sps/api/routes/releases.py` — existing release status endpoints.

## Expected Output
- `tests/m010_s03_observability_readonly_test.py` — negative tests for mutation attempts.
- `scripts/verify_m010_s03.sh` — runbook updated for service-principal + mTLS and redaction proof.
