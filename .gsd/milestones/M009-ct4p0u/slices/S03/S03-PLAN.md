# S03: Rollback Rehearsal and Post-Release Validation

**Goal:** Provide a rollback rehearsal evidence endpoint that stores ROLLBACK_REHEARSAL artifacts via the evidence registry and ship a post-release validation runbook template.

**Demo:** Operator runs `scripts/verify_m009_s03.sh` which records a rollback rehearsal artifact, retrieves it via the evidence API, and validates the post-release checklist template exists.

## Must-Haves
- Rollback rehearsal endpoint persists evidence artifacts with `ArtifactClass.ROLLBACK_REHEARSAL` and release evidence retention.
- Post-release validation runbook template exists with stage-gated validation steps.
- Verification covers API persistence plus the runbook/script checks end-to-end.

## Proof Level
- This slice proves: integration + operational
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py`
- `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py -k failure`
- `bash scripts/verify_m009_s03.sh`

## Observability / Diagnostics
- Runtime signals: release rollback rehearsal logs + evidence registry artifact persistence logs
- Inspection surfaces: `evidence_artifacts` table, `GET /api/v1/evidence/artifacts/{artifact_id}`, `POST /api/v1/releases/rollbacks/rehearsals` responses
- Failure visibility: structured error responses with guard codes + DB row absence
- Redaction constraints: never log artifact contents or checksums beyond existing evidence registry redaction policy

## Integration Closure
- Upstream surfaces consumed: `src/sps/documents/registry.py`, `src/sps/evidence/models.py`, `src/sps/api/routes/releases.py`
- New wiring introduced in this slice: reviewer-authenticated rollback rehearsal endpoint
- What remains before the milestone is truly usable end-to-end: nothing

## Tasks
- [x] **T01: Add rollback rehearsal evidence endpoint + integration test** `est:2h`
  - Why: This is the core requirement for R025 — rollback rehearsal evidence must be stored and queryable.
  - Files: `src/sps/evidence/models.py`, `src/sps/api/routes/releases.py`, `src/sps/documents/registry.py`, `tests/m009_s03_rollback_rehearsal_test.py`
  - Do: Add `ROLLBACK_REHEARSAL` to `ArtifactClass`, implement `POST /api/v1/releases/rollbacks/rehearsals` using the evidence registry and reviewer API key auth, persist provenance fields, and add integration tests that assert the artifact row + API response.
  - Verify: `SPS_RUN_TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest tests/m009_s03_rollback_rehearsal_test.py`
  - Done when: the test passes and the endpoint stores evidence artifacts with the new class and retention.
- [x] **T02: Add post-release validation runbook + verification script** `est:1h`
  - Why: R026 requires a stage-gated post-release validation template and the slice demo depends on the runbook + script.
  - Files: `runbooks/sps/post-release-validation.md`, `scripts/verify_m009_s03.sh`
  - Do: Create the runbook with staged validation steps and required report fields, then add a verification script that posts a rollback rehearsal artifact, fetches it via evidence API, and checks the runbook file.
  - Verify: `bash scripts/verify_m009_s03.sh`
  - Done when: the script succeeds end-to-end and the runbook template exists with stage gates.

## Files Likely Touched
- `src/sps/evidence/models.py`
- `src/sps/api/routes/releases.py`
- `src/sps/documents/registry.py`
- `tests/m009_s03_rollback_rehearsal_test.py`
- `scripts/verify_m009_s03.sh`
- `runbooks/sps/post-release-validation.md`
