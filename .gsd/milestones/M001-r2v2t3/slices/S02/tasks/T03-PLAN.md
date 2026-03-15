---
estimated_steps: 9
estimated_files: 3
---

# T03: Add evidence registry API routes and integration test

**Slice:** S02 — Evidence registry API + MinIO content roundtrip
**Milestone:** M001-r2v2t3

## Description
Expose the evidence registry as FastAPI routes and prove end-to-end register → upload → fetch → download works against Postgres + MinIO.

## Steps
1. Implement evidence service layer that wraps DB + storage adapter with consistent error typing.
2. Implement routes:
   - POST `/evidence/artifacts` (register metadata)
   - PUT `/evidence/artifacts/{id}/content` (upload content)
   - GET `/evidence/artifacts/{id}` (metadata)
   - GET `/evidence/artifacts/{id}/download` (presigned URL or streaming)
3. Ensure DB transaction consistency between metadata writes and upload bookkeeping.
4. Enforce sha mismatch rejection.
5. Add request/response models and ensure contract stability.
6. Add integration test running against docker-compose Postgres + MinIO.
7. Run the test repeatedly to confirm determinism.
8. Ensure errors are redacted and diagnostic.
9. Confirm demo flow works via pytest.

## Must-Haves
- [ ] Evidence registry endpoints exist and are wired to real Postgres + MinIO.
- [ ] End-to-end roundtrip test passes.
- [ ] Sha/bytes integrity is enforced.

## Verification
- `docker compose up -d`
- `./.venv/bin/pytest -q tests/s02_evidence_roundtrip_test.py`

## Inputs
- S01 schema + DB session wiring
- `src/sps/storage/s3.py` adapter

## Expected Output
- `src/sps/api/routes/evidence.py` — evidence routes.
- `src/sps/evidence/service.py` — orchestration.
- `tests/s02_evidence_roundtrip_test.py` — integration test.
