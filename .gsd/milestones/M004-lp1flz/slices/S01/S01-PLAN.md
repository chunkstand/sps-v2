# M004-lp1flz/S01: Intake contract + Project persistence + INTAKE_COMPLETE workflow step

**Goal:** Spec-derived intake payloads create a PermitCase + Project and the workflow advances to INTAKE_COMPLETE via guarded transition.

**Demo:** POST `/api/v1/cases` with a spec-derived intake payload returns `case_id` + `project_id`, persists the PermitCase/Project rows, and the workflow records a CASE_STATE_CHANGED ledger event to INTAKE_COMPLETE.

## Must-Haves
- Spec-derived intake contract enforced at the HTTP boundary, returning case_id/project_id.
- PermitCase + Project persistence from intake payload (normalized fields aligned to Project model).
- Workflow step that applies INTAKE_PENDING → INTAKE_COMPLETE through `apply_state_transition`.
- Integration proof that HTTP → Postgres → Temporal leads to INTAKE_COMPLETE.

## Requirement Coverage
- **R010 (F-001):** Intake normalization into Project (primary for this slice).

## Decomposition Notes
The slice spans three boundaries (HTTP intake, Postgres persistence, Temporal workflow), so the plan splits work to keep each task runnable in one context window and to separate contract/persistence changes from workflow/guard wiring and integration proof. The ordering front-loads the intake boundary and persistence, then wires the workflow guard transition, then proves the full path with Temporal + Postgres + HTTP.

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation` (exercise 4xx failure path)
- `pytest tests/m004_s01_intake_api_workflow_test.py`
- `bash scripts/verify_m004_s01.sh`

## Observability / Diagnostics
- Runtime signals: `intake_api.case_created`, `activity.start name=apply_state_transition`, `workflow.transition_applied` logs.
- Inspection surfaces: `permit_cases`, `projects`, and `case_transition_ledger` tables; `scripts/verify_m004_s01.sh` log tails.
- Failure visibility: ledger denial_reason/event_type, workflow_id/run_id from logs, HTTP 4xx responses on contract failures.
- Redaction constraints: do not log requester PII fields; log IDs and counts only.

## Integration Closure
- Upstream surfaces consumed: `model/sps/model.yaml` (Project fields), `specs/sps/build-approved/spec.md` CreateCase contract, `apply_state_transition` guard.
- New wiring introduced in this slice: `/api/v1/cases` endpoint, intake contract models, workflow intake step.
- What remains before the milestone is truly usable end-to-end: jurisdiction + requirements activities (S02) and docker-compose runbook proof (S03).

## Tasks
- [x] **T01: Define intake contract + create PermitCase/Project via API** `est:2h`
  - Why: establishes the HTTP intake boundary and durable persistence of core records.
  - Files: `src/sps/api/contracts/intake.py`, `src/sps/api/routes/cases.py`, `src/sps/api/main.py`, `src/sps/db/models.py`
  - Do: add spec-aligned CreateCase request/response models; map intake payload → Project fields; generate case_id/project_id; persist PermitCase + Project in a transaction; start PermitCaseWorkflow with the canonical workflow ID.
  - Verify: `pytest tests/m004_s01_intake_api_workflow_test.py -k contract_validation` (new test subcase)
  - Done when: POST `/api/v1/cases` returns 201 with case_id/project_id and rows exist in `permit_cases` + `projects`.
- [x] **T02: Wire INTAKE_PENDING → INTAKE_COMPLETE workflow transition** `est:2h`
  - Why: advances the workflow to INTAKE_COMPLETE via the guarded transition ledger.
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: add activity to load case state; extend `apply_state_transition` to allow INTAKE_PENDING → INTAKE_COMPLETE with Project-exists guard; branch workflow to run intake transition when case is INTAKE_PENDING and return a completion result.
  - Verify: `pytest tests/m004_s01_intake_api_workflow_test.py -k workflow_transition`
  - Done when: case_transition_ledger records CASE_STATE_CHANGED with `to_state=INTAKE_COMPLETE` for intake cases.
- [x] **T03: Add integration test + operator runbook for intake flow** `est:2h`
  - Why: proves HTTP → Postgres → Temporal integration with a real workflow run.
  - Files: `tests/m004_s01_intake_api_workflow_test.py`, `scripts/verify_m004_s01.sh`, `scripts/lib/assert_postgres.sh`
  - Do: add Temporal+Postgres integration test using httpx ASGI transport to call `/api/v1/cases`; assert PermitCase/Project rows and ledger transition; add runbook script mirroring test assertions against docker-compose.
  - Verify: `pytest tests/m004_s01_intake_api_workflow_test.py` and `bash scripts/verify_m004_s01.sh`
  - Done when: test + runbook pass and show INTAKE_COMPLETE in the ledger.

## Files Likely Touched
- `src/sps/api/contracts/intake.py`
- `src/sps/api/routes/cases.py`
- `src/sps/api/main.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `tests/m004_s01_intake_api_workflow_test.py`
- `scripts/verify_m004_s01.sh`
