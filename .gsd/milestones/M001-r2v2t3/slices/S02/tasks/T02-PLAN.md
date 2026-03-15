---
estimated_steps: 8
estimated_files: 2
---

# T02: Implement S3-compatible storage adapter (MinIO)

**Slice:** S02 — Evidence registry API + MinIO content roundtrip
**Milestone:** M001-r2v2t3

## Description
Implement an S3 adapter that can upload evidence content, fetch metadata, and generate presigned download URLs against local MinIO, enforcing sha256/bytes integrity checks.

## Steps
1. Extend config to include S3 endpoint, access key, secret key, bucket, region, and URL expiry.
2. Implement `src/sps/storage/s3.py` adapter (put/get/head + presign GET).
3. Enforce integrity: sha256 + bytes recorded/validated during upload and/or HEAD.
4. Ensure secrets are never logged; errors are classified (s3 vs validation).
5. Add focused adapter tests running against MinIO.
6. Confirm adapter works with docker-compose MinIO.
7. Add minimal docs/comments.
8. Verify presigned URLs are time-bounded.

## Must-Haves
- [ ] Adapter can upload and retrieve objects from local MinIO.
- [ ] Adapter can generate presigned GET URLs.
- [ ] Integrity checks (sha256/bytes) are enforced and mismatches are rejected.

## Verification
- `docker compose up -d minio`
- `./.venv/bin/pytest -q tests/s02_storage_adapter_test.py`

## Observability Impact
- Signals added/changed: structured error responses/classification for S3 operations.
- How a future agent inspects this: run adapter tests or list objects in MinIO.
- Failure state exposed: sha mismatch and S3 failures surface with operation + artifact_id context.

## Inputs
- `docker-compose.yml` — MinIO service wiring.

## Expected Output
- `src/sps/storage/s3.py` — S3 adapter.
- `src/sps/config.py` — S3 settings.
