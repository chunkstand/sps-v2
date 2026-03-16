# S03: Live submission + tracking runbook

**Goal:** Prove the real API + worker entrypoints can run intake → submission → status ingest with receipts persisted in MinIO and tracking events in Postgres via a docker-compose runbook.
**Demo:** `bash scripts/verify_m007_s03.sh` runs the end-to-end flow, exits 0, and prints successful receipt + external status assertions.

## Must-Haves
- New runbook script starts docker-compose stack, runs migrations, and boots API + worker against a unique Temporal task queue.
- Runbook drives intake, posts reviewer decision, waits for SUBMITTED or MANUAL_SUBMISSION_REQUIRED, and ingests a known raw external status.
- Runbook asserts receipt evidence metadata + presigned download URL and persists ExternalStatusEvent rows via Postgres assertions (without exposing DSNs).
- Phase 6 + Phase 7 fixture overrides are set and fixture rows are cleaned to keep deterministic IDs rerunnable.

## Proof Level
- This slice proves: operational
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `bash scripts/verify_m007_s03.sh`
- `rg "runbook.fail" scripts/verify_m007_s03.sh`

## Observability / Diagnostics
- Runtime signals: runbook log output + API response payloads (submission attempts, manual fallback, external status ingest) + Postgres assertions.
- Inspection surfaces: `scripts/verify_m007_s03.sh` output, `scripts/lib/assert_postgres.sh` queries, evidence metadata/download endpoints.
- Failure visibility: runbook non-zero exit + assertion error output + API error responses.
- Redaction constraints: do not echo DSNs or secret values; use docker compose exec for psql.

## Integration Closure
- Upstream surfaces consumed: `scripts/verify_m005_s03.sh`, `scripts/lib/assert_postgres.sh`, `src/sps/api/routes/cases.py`, `src/sps/api/routes/reviews.py`, `src/sps/api/routes/evidence.py`, `src/sps/fixtures/phase6.py`, `src/sps/fixtures/phase7.py`.
- New wiring introduced in this slice: `scripts/verify_m007_s03.sh` runbook driving API + worker entrypoints.
- What remains before the milestone is truly usable end-to-end: nothing for this slice; milestone completion requires this runbook to pass.

## Tasks
- [x] **T01: Build Phase 7 runbook for live submission + tracking** `est:2h`
  - Why: Provide the operational proof that real API + worker entrypoints persist receipts and status events across Postgres/MinIO.
  - Files: `scripts/verify_m007_s03.sh`, `scripts/verify_m005_s03.sh`, `scripts/lib/assert_postgres.sh`
  - Do: Clone the M005/S03 runbook structure, set Phase 6/7 fixture overrides + unique Temporal task queue, clean deterministic fixture rows, run intake + reviewer decision + submission attempt, wait for SUBMITTED or MANUAL_SUBMISSION_REQUIRED, ingest a known raw status, and assert evidence + status persistence via API + Postgres helpers.
  - Verify: `bash scripts/verify_m007_s03.sh`
  - Done when: runbook exits 0 and prints receipt evidence + external status assertions for the new case.

## Files Likely Touched
- `scripts/verify_m007_s03.sh`
- `scripts/verify_m005_s03.sh`
- `scripts/lib/assert_postgres.sh`
