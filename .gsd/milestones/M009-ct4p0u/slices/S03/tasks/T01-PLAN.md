---
estimated_steps: 4
estimated_files: 4
---

# T01: Add rollback rehearsal evidence endpoint + integration test

**Slice:** S03 — Rollback Rehearsal and Post-Release Validation
**Milestone:** M009-ct4p0u

## Description
Implement the rollback rehearsal API endpoint and evidence artifact class so rollback rehearsal evidence is stored in the evidence registry and queryable via existing evidence APIs.

## Steps
1. Extend `ArtifactClass` with `ROLLBACK_REHEARSAL` and ensure any schema validation accepts the new class.
2. Add `POST /api/v1/releases/rollbacks/rehearsals` in the releases router using reviewer API key auth and evidence registry storage with `RetentionClass.RELEASE_EVIDENCE` plus release provenance fields.
3. Wire response models and error handling consistent with existing release endpoints (fail closed on checksum/class issues).
4. Add `tests/m009_s03_rollback_rehearsal_test.py` to assert artifact persistence (DB row + class) and API response fields.

## Must-Haves
- [ ] Evidence artifacts created by the endpoint use `ArtifactClass.ROLLBACK_REHEARSAL` and `RetentionClass.RELEASE_EVIDENCE`.
- [ ] Integration test proves the artifact is persisted and retrievable via the evidence registry API.

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py`
- API response contains artifact id/class and evidence registry lookup returns the stored row.

## Observability Impact
- Signals added/changed: structured logs for rollback rehearsal creation + evidence registry artifact persistence failures.
- How a future agent inspects this: `GET /api/v1/evidence/artifacts/{artifact_id}` or DB query on `evidence_artifacts`.
- Failure state exposed: non-201 response with error detail and missing evidence row.

## Inputs
- `src/sps/documents/registry.py` — existing evidence registry write path and checksum enforcement.
- `src/sps/api/routes/releases.py` — reviewer-authenticated release router pattern.

## Expected Output
- `src/sps/evidence/models.py` — new `ROLLBACK_REHEARSAL` class.
- `src/sps/api/routes/releases.py` — rollback rehearsal endpoint implementation.
- `tests/m009_s03_rollback_rehearsal_test.py` — integration coverage for evidence persistence and retrieval.
