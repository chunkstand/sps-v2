---
id: T01
slice: S02
milestone: M006-h7v2qk
---

# T01: Write and execute end-to-end package generation runbook

## Description

Create an operator runbook script that proves document generation and package persistence work end-to-end with live infrastructure. Follow the M005/S03 pattern: orchestrate docker-compose services (postgres, temporal, minio), apply migrations, start API server and worker with Phase 6 fixture override enabled, drive workflow through intake to DOCUMENT_COMPLETE, and verify package/manifest persistence via Postgres queries and API calls. This completes R015 validation by proving the full path from fixture templates through document generation to sealed package storage and retrieval.

## Steps

1. **Create runbook script skeleton** following scripts/verify_m005_s03.sh structure:
   - Script header with strict error handling (`set -euo pipefail`)
   - Color output helpers (INFO/PASS/FAIL)
   - Cleanup trap for background processes
   - Docker-compose orchestration with readiness checks
   - Migration application
   - API server + worker startup

2. **Add MinIO readiness check** after docker-compose up:
   - `_wait_for_tcp localhost 9000 30` to ensure MinIO is listening
   - Optional: add small sleep (2-3s) or `mc ls minio/sps-evidence` check to ensure bucket exists

3. **Extract Phase 6 fixture artifact IDs** from documents.json and delete before intake:
   - Use Python heredoc to parse documents.json and extract artifact_ids
   - Delete from evidence_artifacts by artifact_id list (not just case_id)
   - Log deleted row count for diagnostics

4. **Start API server** with background process:
   - `uvicorn sps.api.main:app --host 0.0.0.0 --port 8080 & API_PID=$!`
   - Wait for API readiness (curl loop or _wait_for_tcp localhost 8080)

5. **POST intake** to create case:
   - Use curl to POST /api/v1/cases/intake with minimal payload
   - Extract case_id from response
   - Log case_id for operator visibility

6. **Start worker** with Phase 6 fixture override:
   - `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE="${CASE_ID}" python -m sps.worker & WORKER_PID=$!`
   - Log worker startup with fixture override env var

7. **Poll workflow until DOCUMENT_COMPLETE**:
   - Use pg_exec to query `permit_cases.case_state` in loop
   - Timeout after 60 seconds
   - Fail if workflow doesn't reach DOCUMENT_COMPLETE

8. **Assert package persistence** via Postgres queries:
   - Query: `SELECT COUNT(*) FROM submission_packages WHERE case_id = '...'`
   - Assert count = 1 using pg_assert_int_eq
   - Extract package_id and manifest_artifact_id

9. **Assert evidence artifacts exist**:
   - Query: `SELECT COUNT(*) FROM evidence_artifacts WHERE linked_case_id = '...' AND artifact_class IN ('MANIFEST', 'DOCUMENT')`
   - Assert count >= 3 (1 manifest + 2 documents from fixture)

10. **Assert manifest digest consistency**:
    - Query: `SELECT sp.manifest_sha256_digest, ea.checksum FROM submission_packages sp JOIN evidence_artifacts ea ON sp.manifest_artifact_id = ea.artifact_id WHERE sp.case_id = '...'`
    - Assert both values are non-empty and equal

11. **Call GET /api/v1/cases/{case_id}/package**:
    - Use curl with case_id
    - Assert HTTP 200 status
    - Log response for diagnostics (jq for readability)

12. **Call GET /api/v1/cases/{case_id}/manifest**:
    - Use curl with case_id
    - Assert HTTP 200 status
    - Assert response contains document references array

## Must-Haves

- Runbook script follows M005/S03 pattern structure
- MinIO TCP readiness check before worker starts
- Phase 6 fixture artifact cleanup by artifact_id before intake
- Workflow polling with 60s timeout
- Postgres assertions for package row + evidence artifacts + digest consistency
- API assertions for package and manifest endpoints (HTTP 200)
- Script exits 0 only if all assertions pass
- Cleanup trap kills API/worker processes on exit

## Verification

```bash
# Full runbook execution
bash scripts/verify_m006_s02.sh
# Should exit 0 with all assertions passing

# Check final state manually
docker compose exec postgres psql -U sps_user -d sps_db -c \
  "SELECT case_id, case_state, current_package_id FROM permit_cases WHERE case_state = 'DOCUMENT_COMPLETE';"
# Should show one row

docker compose exec postgres psql -U sps_user -d sps_db -c \
  "SELECT artifact_id, artifact_class, checksum FROM evidence_artifacts WHERE artifact_class IN ('MANIFEST', 'DOCUMENT');"
# Should show manifest + document artifacts with checksums

curl -s http://localhost:8080/api/v1/cases/{case_id}/package | jq
# Should return SubmissionPackageResponse with package_id, manifest reference
```

## Inputs

- S01 implementation: document generator, package persistence activity, workflow wiring, API endpoints
- docker-compose.yml: postgres, temporal, minio services
- scripts/lib/assert_postgres.sh: pg_exec, pg_assert_int_eq helpers
- specs/sps/build-approved/fixtures/phase6/documents.json: fixture artifact IDs

## Expected Output

- `scripts/verify_m006_s02.sh`: Executable runbook script (~400-500 lines following M005/S03 pattern)
- Script output logs showing:
  - Docker services started and ready
  - Migrations applied
  - API server ready
  - Phase 6 fixture artifacts deleted (log count)
  - Case created (log case_id)
  - Worker started with fixture override
  - Workflow reached DOCUMENT_COMPLETE
  - Package persistence assertions passed
  - Evidence artifact assertions passed
  - Digest consistency assertion passed
  - API endpoint assertions passed (HTTP 200)
- Exit code 0 on success

## Observability Impact

**New diagnostic surfaces**:
- Runbook log output with INFO/PASS/FAIL markers for each verification step
- Docker-compose logs available via `docker compose logs -f` for Temporal/worker/API debugging
- Postgres query results showing package/manifest/evidence state
- API response payloads (JSON) for package and manifest endpoints

**Operator diagnostics**:
- If workflow doesn't reach DOCUMENT_COMPLETE: check `docker compose logs worker` for activity failures
- If package assertions fail: query `submission_packages` table directly with case_id
- If evidence assertions fail: query `evidence_artifacts` table with linked_case_id
- If digest mismatch: compare `submission_packages.manifest_sha256_digest` to `evidence_artifacts.checksum` via JOIN query
- If API endpoints fail: check API logs for 404/500 errors and verify case_id exists

## Done When

- [ ] scripts/verify_m006_s02.sh exists and is executable
- [ ] Script brings up docker-compose services and waits for readiness
- [ ] Script applies migrations
- [ ] Script deletes Phase 6 fixture artifacts before intake
- [ ] Script starts API server and waits for readiness
- [ ] Script POSTs intake and extracts case_id
- [ ] Script starts worker with SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE
- [ ] Script polls workflow until DOCUMENT_COMPLETE (60s timeout)
- [ ] Script asserts package row exists via Postgres query
- [ ] Script asserts evidence artifacts exist (manifest + documents)
- [ ] Script asserts manifest digest consistency via JOIN query
- [ ] Script calls GET /api/v1/cases/{case_id}/package and asserts HTTP 200
- [ ] Script calls GET /api/v1/cases/{case_id}/manifest and asserts HTTP 200
- [ ] Script exits 0 when all assertions pass
- [ ] Script tested end-to-end and passes
