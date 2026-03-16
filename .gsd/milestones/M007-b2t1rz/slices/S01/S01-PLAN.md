# S01: Deterministic submission attempt + receipt + manual fallback

**Goal:** PermitCaseWorkflow creates a deterministic SubmissionAttempt with a persisted receipt EvidenceArtifact or generates a ManualFallbackPackage, and proof bundle confirmation is enforced before submission completion.
**Demo:** Integration tests show retry-safe submission attempt persistence (single receipt), manual fallback package creation for unsupported portals, and proof bundle validation gating SUBMITTED state.

## Decomposition Notes
- The slice is split into persistence schema, workflow/adapter wiring, and API/tests to keep idempotency-critical logic isolated and to ensure verification exercises the boundary contracts.
- Order is driven by retry/idempotency risk: schema first, then deterministic adapter + workflow wiring, then tests + API surfaces to validate the full behavior.
- Verification is pytest-based integration tests to prove deterministic behavior, receipt persistence, and proof bundle gating with real Postgres/MinIO.

## Must-Haves
- SubmissionAttempt persistence is idempotent and stores receipt EvidenceArtifact linkage with deterministic IDs. (R016)
- ManualFallbackPackage is generated for unsupported portals and persisted with evidence linkage. (R018)
- Proof bundle validation + reviewer confirmation is enforced before SUBMITTED. (R019)
- Workflow transitions to SUBMITTED or MANUAL_SUBMISSION_REQUIRED with persisted artifacts. (R016/R018)

## Proof Level
- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification
- `pytest tests/m007_s01_submission_attempts_test.py -v -s`
- `pytest tests/m007_s01_manual_fallback_test.py -v -s`
- `pytest tests/m007_s01_proof_bundle_gate_test.py -v -s`
- Inspect failure surface: `psql "$DATABASE_URL" -c "select status,last_error,updated_at from submission_attempts order by updated_at desc limit 1"`

## Observability / Diagnostics
- Runtime signals: activity logs with submission_attempt_id, receipt_artifact_id, manual_fallback_id, status, correlation_id; submission_attempts.last_error
- Inspection surfaces: DB tables `submission_attempts`, `manual_fallback_packages`, `evidence_artifacts`, `case_transition_ledger`; API GET endpoints for submission attempts and fallback packages
- Failure visibility: submission_attempts.status, attempt_number, last_error, updated_at
- Redaction constraints: no PII or evidence payloads in logs

## Integration Closure
- Upstream surfaces consumed: `persist_submission_package` activity, evidence registry storage, ReviewDecision records, state transition guard
- New wiring introduced in this slice: submission adapter activity + worker registration; PermitCaseWorkflow submission step; API read endpoints for attempts/receipts/manual fallback
- What remains before the milestone is truly usable end-to-end: status normalization + tracking events (S02) and docker-compose runbook (S03)

## Tasks
- [x] **T01: Add submission attempt + manual fallback persistence schema** `est:1h`
  - Why: Establish authoritative storage for submission attempts, receipts, and manual fallback before wiring workflow behavior.
  - Files: `src/sps/db/models.py`, `alembic/versions/<new>_submission_attempts_manual_fallback.py`
  - Do: Add SubmissionAttempt + ManualFallbackPackage tables with evidence artifact linkage, idempotency keys, status fields, and failure metadata; add indexes/FKs; generate Alembic migration.
  - Verify: `pytest tests/s01_db_schema_test.py -k submission -v -s`
  - Done when: migrations apply cleanly and schema test confirms new tables/columns.
- [x] **T02: Implement deterministic submission adapter + workflow wiring** `est:2.5h`
  - Why: Provide the idempotent submission attempt behavior, receipt persistence, and manual fallback path required for workflow progression.
  - Files: `src/sps/workflows/permit_case/contracts.py`, `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/worker.py`, `specs/sps/build-approved/fixtures/phase7/...`
  - Do: Define submission attempt request/response contracts; implement deterministic adapter activity that writes SubmissionAttempt + EvidenceArtifact receipt idempotently; generate ManualFallbackPackage for unsupported portals; enforce proof bundle confirmation gate before SUBMITTED; wire activity into workflow transitions and register in worker; add structured logs with correlation IDs.
  - Verify: `pytest tests/m007_s01_submission_attempts_test.py -v -s`
  - Done when: workflow can complete submission with receipt or manual fallback deterministically in tests and logs expose attempt IDs.
- [x] **T03: Expose submission attempt + receipt + fallback via API and add integration tests** `est:2h`
  - Why: Make persistence inspectable and prove the slice behavior via API + integration tests.
  - Files: `src/sps/api/contracts/cases.py`, `src/sps/api/routes/cases.py`, `tests/m007_s01_submission_attempts_test.py`, `tests/m007_s01_manual_fallback_test.py`, `tests/m007_s01_proof_bundle_gate_test.py`
  - Do: Add API response models + GET routes for submission attempts, receipt evidence metadata, and manual fallback package details; write integration tests covering idempotent submission, manual fallback, and proof bundle gating using Temporal/Postgres fixtures.
  - Verify: `pytest tests/m007_s01_manual_fallback_test.py -v -s`
  - Done when: API reads return persisted artifacts and all S01 integration tests pass.

## Files Likely Touched
- `src/sps/db/models.py`
- `alembic/versions/<new>_submission_attempts_manual_fallback.py`
- `src/sps/workflows/permit_case/contracts.py`
- `src/sps/workflows/permit_case/activities.py`
- `src/sps/workflows/permit_case/workflow.py`
- `src/sps/workflows/worker.py`
- `src/sps/api/contracts/cases.py`
- `src/sps/api/routes/cases.py`
- `tests/m007_s01_submission_attempts_test.py`
- `tests/m007_s01_manual_fallback_test.py`
- `tests/m007_s01_proof_bundle_gate_test.py`
- `specs/sps/build-approved/fixtures/phase7/`
