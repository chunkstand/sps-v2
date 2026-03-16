---
id: T01
parent: S03
milestone: M009-ct4p0u
provides:
  - rollback rehearsal evidence endpoint with evidence registry persistence
key_files:
  - src/sps/api/routes/releases.py
  - src/sps/evidence/models.py
  - model/sps/model.yaml
  - model/sps/contracts/evidence-artifact.schema.json
  - tests/m009_s03_rollback_rehearsal_test.py
key_decisions:
  - Canonicalize rollback rehearsal payload JSON (sorted keys + compact separators) before checksum validation.
patterns_established:
  - EvidenceRegistry + EvidenceArtifact row persistence for release-scoped evidence endpoints.
observability_surfaces:
  - structured logs: rollback_rehearsal.created / rollback_rehearsal.checksum_mismatch / rollback_rehearsal.persistence_failed
  - GET /api/v1/evidence/artifacts/{artifact_id}
  - error responses with checksum_mismatch or invalid_artifact_class
duration: 1.6h
verification_result: partial
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Add rollback rehearsal evidence endpoint + integration test

**Added a rollback rehearsal evidence endpoint that writes evidence artifacts via the registry and validated persistence + failure paths in integration tests.**

## What Happened
- Added ArtifactClass.ROLLBACK_REHEARSAL to evidence enums and contract schemas.
- Implemented POST /api/v1/releases/rollbacks/rehearsals with checksum validation, registry storage, release provenance, and structured logging on success/failure.
- Added integration tests covering persistence, evidence API lookup, and checksum mismatch handling (including log invocation verification).

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py -k failure`
- `bash scripts/verify_m009_s03.sh` (fails: script not present yet — expected until T02)

## Diagnostics
- Query artifact metadata via `GET /api/v1/evidence/artifacts/{artifact_id}`.
- Inspect logs for rollback_rehearsal.* entries and error responses for checksum/class mismatches.

## Deviations
- None.

## Known Issues
- `scripts/verify_m009_s03.sh` is missing (T02 will add it), so the slice-level script verification currently fails.

## Files Created/Modified
- `src/sps/evidence/models.py` — added ROLLBACK_REHEARSAL artifact class.
- `model/sps/model.yaml` — extended ArtifactClass enum.
- `model/sps/contracts/evidence-artifact.schema.json` — added ROLLBACK_REHEARSAL to schema.
- `src/sps/api/routes/releases.py` — added rollback rehearsal endpoint with evidence registry persistence.
- `tests/m009_s03_rollback_rehearsal_test.py` — integration coverage for persistence and checksum failure handling.
- `.gsd/milestones/M009-ct4p0u/slices/S03/S03-PLAN.md` — marked T01 complete and added failure-path verification step.
- `.gsd/STATE.md` — advanced next action to T02.
