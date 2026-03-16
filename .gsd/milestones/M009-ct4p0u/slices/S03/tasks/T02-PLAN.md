---
estimated_steps: 3
estimated_files: 2
---

# T02: Add post-release validation runbook + verification script

**Slice:** S03 — Rollback Rehearsal and Post-Release Validation
**Milestone:** M009-ct4p0u

## Description
Ship the post-release validation runbook template and the verification script that exercises rollback rehearsal storage and confirms the template exists.

## Steps
1. Create `runbooks/sps/post-release-validation.md` using the established runbook header format and include stage-gated validation steps (canary → staged rollout) with required report fields.
2. Implement `scripts/verify_m009_s03.sh` to post a rollback rehearsal artifact, fetch it via the evidence API, and assert the runbook template is present.
3. Ensure the script exits non-zero on missing artifact/template or API failures.

## Must-Haves
- [ ] Runbook template exists with explicit staged validation gates and required report fields.
- [ ] Verification script exercises rollback rehearsal creation + retrieval and checks the template file.

## Verification
- `bash scripts/verify_m009_s03.sh`
- Script succeeds against a running API and fails closed on missing template or API errors.

## Inputs
- `.gsd/milestones/M009-ct4p0u/slices/S03/S03-PLAN.md` — demo/verification expectations.

## Expected Output
- `runbooks/sps/post-release-validation.md` — new template file.
- `scripts/verify_m009_s03.sh` — runbook verification script.

## Observability Impact
- Signals: `scripts/verify_m009_s03.sh` prints evidence artifact IDs, GET status, and runbook template presence; exit codes indicate failure class.
- Inspection: rerun the script or call `GET /api/v1/evidence/artifacts/{artifact_id}` to confirm persisted rollback rehearsal evidence; check runbook file path.
- Failure visibility: non-zero exit on API errors, missing artifact, or missing template ensures CI/ops catches regressions.
