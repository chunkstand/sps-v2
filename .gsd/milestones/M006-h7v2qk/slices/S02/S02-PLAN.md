---
id: S02
milestone: M006-h7v2qk
depends_on: [S01]
---

# S02: Workflow document stage + end-to-end package runbook

**Goal**: Prove document package generation end-to-end with live infrastructure — workflow reaches DOCUMENT_COMPLETE, package/manifest persisted to Postgres/MinIO, and API endpoints return expected data.

## Why This Slice

S01 delivered all implementation (document generator, package persistence, workflow wiring, API endpoints) but couldn't prove full end-to-end behavior because integration tests lacked S3 infrastructure (MinIO). This slice provides operational proof by running the complete flow with docker-compose orchestrating Postgres, Temporal, and MinIO. The runbook follows the proven M005/S03 pattern: start services, apply migrations, drive workflow through fixture intake, assert final state via Postgres queries and API calls, and verify digest consistency between manifest and evidence registry.

## Narration

S02 is a single-task runbook slice. No new code is required — we're proving that S01's implementation works end-to-end with live infrastructure. The research identified that docker-compose.yml already provisions all necessary services (postgres, temporal, temporal-ui, minio with bucket initialization), and the M005/S03 runbook establishes the proven pattern for fixture override + workflow assertions + Postgres inspection. The critical additions for Phase 6 are: (1) Phase 6 fixture artifact cleanup before intake to prevent idempotent insert conflicts, (2) package/manifest API assertions after DOCUMENT_COMPLETE, and (3) manifest digest consistency check joining submission_packages to evidence_artifacts to prove sealed package integrity.

## Must-Haves

- Runbook script following M005/S03 pattern (docker-compose up, migrations, API server, worker with fixture override)
- MinIO TCP readiness check before worker starts (`_wait_for_tcp localhost 9000 30`)
- Phase 6 fixture artifact cleanup (delete by artifact IDs from documents.json)
- Workflow assertion: case reaches DOCUMENT_COMPLETE state
- Postgres assertion: submission_packages row exists with manifest_artifact_id
- Postgres assertion: evidence_artifacts rows exist for manifest + documents with sha256 checksums
- API assertion: GET /cases/{case_id}/package returns SubmissionPackageResponse
- API assertion: GET /cases/{case_id}/manifest returns SubmissionManifestResponse
- Digest consistency assertion: `submission_packages.manifest_sha256_digest = evidence_artifacts.checksum` (join on manifest_artifact_id)

## Slice-Level Verification

**Executable command**:
```bash
bash scripts/verify_m006_s02.sh
```

**Success criteria**:
- Script exits 0
- Workflow reaches DOCUMENT_COMPLETE (verified via permit_cases.case_state)
- SubmissionPackage row exists in DB
- Evidence artifacts exist for manifest + documents
- API endpoints return 200 with expected payloads
- Manifest digest matches evidence registry checksum

## Proof Level

**Operational verification**: Real docker-compose services, real workflow execution, real S3 operations (MinIO), real API responses. No mocks.

## Integration Closure

End-to-end from intake POST → workflow execution → DOCUMENT_COMPLETE → package/manifest persistence → API readback. Proves R015 fully validated.

## Tasks

### T01: Write and execute end-to-end package generation runbook

**Why**: Prove S01's document generation + package persistence implementation works end-to-end with live Postgres/Temporal/MinIO infrastructure and completes R015 validation.

**Files**:
- `scripts/verify_m006_s02.sh` (new)
- `scripts/lib/assert_postgres.sh` (reuse)
- `specs/sps/build-approved/fixtures/phase6/documents.json` (read for artifact IDs)

**Do**:
1. Create runbook script following M005/S03 pattern structure
2. Add docker-compose orchestration with postgres/temporal/minio services
3. Add MinIO TCP readiness check (`_wait_for_tcp localhost 9000 30`)
4. Extract fixture artifact IDs from documents.json and delete from evidence_artifacts before intake
5. Start API server (uvicorn) and worker with `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE` env var
6. POST intake to create case
7. Poll workflow until DOCUMENT_COMPLETE (timeout 60s)
8. Assert package row exists in submission_packages
9. Assert evidence artifacts exist for manifest + documents
10. Assert manifest digest consistency (join submission_packages to evidence_artifacts)
11. Call GET /api/v1/cases/{case_id}/package and assert 200 response
12. Call GET /api/v1/cases/{case_id}/manifest and assert 200 response

**Verify**:
```bash
bash scripts/verify_m006_s02.sh
# Should exit 0 with all assertions passing
```

**Done when**:
- Runbook script exists and is executable
- Script proves workflow reaches DOCUMENT_COMPLETE
- Package/manifest persistence verified via Postgres queries
- API endpoints return expected data
- Digest consistency proven
- R015 status can be updated to "validated"

**Task plan**: `.gsd/milestones/M006-h7v2qk/slices/S02/tasks/T01-PLAN.md`

## Owned Requirements

- **R015**: Submission package generation (F-006) — advance from "partial validation" to "validated" status

## Key Decisions

None (reuses established patterns from M005/S03).

## Risks

- **MinIO bucket initialization timing**: If worker starts before minio-init completes bucket creation, S3 put will fail with "bucket not found". Mitigation: add small sleep after MinIO TCP check, or verify bucket exists via `mc ls`.
- **Fixture artifact cleanup failure**: If cleanup query fails to match artifact IDs, reruns will hit IntegrityError. Mitigation: log deleted row count and fail early if zero when expecting fixture IDs.

## Notes

- Workflow stops at DOCUMENT_COMPLETE (does not continue to REVIEW_PENDING) — runbook should assert this as final state
- Fixture case_id is `CASE-EXAMPLE-001` from Phase 6 fixtures; runtime case_id will differ due to ULID generation
- Evidence artifacts are partitioned by ULID prefix in S3: `evidence/<ULID[:2]>/<artifact_id>`
