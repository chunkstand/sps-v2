# S02: Evidence registry API + MinIO content roundtrip

**Goal:** Implement the evidence registry API with stable IDs and real S3-compatible storage binding.
**Demo:** Register an evidence artifact, upload content to MinIO, then retrieve metadata and a download URL by stable ID.

## Must-Haves

- Stable ID generation for EvidenceArtifact and deterministic object key layout.
- Evidence registry endpoints: register, upload content, fetch metadata, fetch download link/stream.
- Integrity correlation: stored sha256/bytes in DB matches uploaded object (or upload is rejected).

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Postgres + MinIO)
- Human/UAT required: no

## Verification

- `docker compose up -d`
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`

## Observability / Diagnostics

- Runtime signals: structured error responses for missing artifact IDs, sha mismatch, S3 errors
- Inspection surfaces: API endpoints; Postgres `evidence_artifacts` table; MinIO bucket object listing
- Failure visibility: error includes artifact_id, operation, and underlying dependency class (db/s3)
- Redaction constraints: never return S3 secrets; presigned URLs are time-bounded

## Integration Closure

- Upstream surfaces consumed: DB models/migrations from S01; `model/sps/contracts/evidence-artifact.schema.json`
- New wiring introduced in this slice: boto3 S3 client; object storage adapter; FastAPI routes
- What remains before the milestone is truly usable end-to-end: retention/legal-hold and purge denial behavior

## Tasks

- [x] **T01: Implement evidence domain model + stable ID scheme** `est:1h`
  - Why: Stable IDs are required for audit and evidence retrieval across time.
  - Files: `src/sps/evidence/ids.py`, `src/sps/evidence/models.py`
  - Do: Choose stable ID format (ULID by default); define EvidenceArtifact typed model aligned to `evidence-artifact.schema.json` fields; define object key layout strategy and constraints.
  - Verify: `./.venv/bin/python -c "from sps.evidence.ids import new_evidence_id; print(new_evidence_id())"`
  - Done when: IDs are stable-format validated and object keys are derived without ambiguity.

- [x] **T02: Implement S3-compatible storage adapter (MinIO)** `est:1h`
  - Why: Evidence content must live in durable object storage, not only Postgres.
  - Files: `src/sps/storage/s3.py`, `src/sps/config.py`
  - Do: Create an adapter that uploads objects, fetches metadata, and generates presigned GET URLs; enforce sha256/bytes checks.
  - Verify: `docker compose up -d minio && ./.venv/bin/pytest -q tests/s02_storage_adapter_test.py`
  - Done when: adapter can upload and retrieve objects from MinIO locally.

- [x] **T03: Add evidence registry API routes and integration test** `est:2h`
  - Why: The system must retrieve evidence by stable ID via an explicit registry API.
  - Files: `src/sps/api/routes/evidence.py`, `src/sps/evidence/service.py`, `tests/s02_evidence_roundtrip_test.py`
  - Do: Implement endpoints:
    - POST `/evidence/artifacts` (register metadata)
    - PUT `/evidence/artifacts/{id}/content` (upload content)
    - GET `/evidence/artifacts/{id}` (metadata)
    - GET `/evidence/artifacts/{id}/download` (presigned URL or streaming)
    Ensure DB transaction consistency; reject sha mismatch.
  - Verify: `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`
  - Done when: end-to-end roundtrip passes against Postgres + MinIO.

## Files Likely Touched

- `src/sps/evidence/*`
- `src/sps/storage/s3.py`
- `src/sps/api/routes/evidence.py`
- `tests/s02_*`
