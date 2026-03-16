# Project

## What This Is

A Python monorepo implementation scaffold for the **Solar Permitting System (SPS)**, built to conform to the **SPS v2.0.1 BUILD_APPROVED canonical spec package** included in this repo.

## Core Value

A governed workflow system that can produce and submit permit packages with reviewer-gated authority, durable evidence, and audit reconstruction.

## Current State

- Canonical spec package is materialized at repo root (`specs/`, `model/`, `invariants/`, `traceability/`, `runbooks/`, etc.).
- CI verifies repo wiring + `PACKAGE-MANIFEST.json` integrity + JSON schema metaschema validity.
- Local dev infra scaffold exists (`docker-compose.yml`: Postgres, Temporal, Temporal UI, MinIO).
- Python monorepo scaffold exists (`pyproject.toml`, `src/sps/`).
- **Phase 3 reviewer service authority boundary is complete (M003/S01):**
  - `POST /api/v1/reviews/decisions` is the sole authoritative writer of `ReviewDecision` records; dev API key middleware gates the endpoint
  - Idempotency enforcement: same key + same `decision_id` → 200; same key + different `decision_id` → 409 `IDEMPOTENCY_CONFLICT`
  - Post-commit Temporal signal delivery with structured log instrumentation (`reviewer_api.decision_received/persisted/signal_sent/signal_failed`)
  - `PermitCaseWorkflow` no longer calls `persist_review_decision` activity; uses API-issued `decision_id` from signal
  - Proof surfaces: integration test (`tests/m003_s01_reviewer_api_boundary_test.py`) + operator runbook (`scripts/verify_m003_s01.sh`)
- **Dissent artifacts are complete (M003/S04):**
  - `POST /api/v1/reviews/decisions` with `outcome=ACCEPT_WITH_DISSENT` + `dissent_scope` + `dissent_rationale` → 201 + `dissent_artifact_id` in response; dissent row persisted in same transaction as ReviewDecision
  - `GET /api/v1/dissents/{dissent_id}` — gated by `require_reviewer_api_key`; returns full artifact with `resolution_state=OPEN`; 404 on unknown
  - ACCEPT decisions produce no dissent row (`dissent_artifact_id=null` in response)
  - Missing dissent fields on ACCEPT_WITH_DISSENT → HTTP 422 (Pydantic model_validator)
  - `reviewer_api.dissent_artifact_created` structured log event (scope_len only — no raw reviewer text)
  - Proof surfaces: integration test (`tests/m003_s04_dissent_artifacts_test.py`) 2 passed + operator runbook (`scripts/verify_m003_s04.sh`) exits 0
  - **M003 fully complete: R006, R007, R008, R009 all validated**
- **Phase 4 intake flow (M004/S01) complete:**
  - `POST /api/v1/cases` accepts the spec-derived intake contract and persists PermitCase + Project in one transaction
  - `PermitCaseWorkflow` advances INTAKE_PENDING → INTAKE_COMPLETE via guarded transition
  - Proof surfaces: `tests/m004_s01_intake_api_workflow_test.py` (contract + integration) and `scripts/verify_m004_s01.sh`
- **Phase 4 jurisdiction + requirements flow (M004/S02) complete:**
  - Fixture-backed jurisdiction + requirement artifacts persist with provenance/evidence payloads
  - `PermitCaseWorkflow` advances INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE via guarded transitions
  - Read surfaces: `GET /api/v1/cases/{case_id}/jurisdiction` and `/requirements`
  - Proof surfaces: `tests/m004_s02_jurisdiction_requirements_workflow_test.py` and `scripts/verify_m004_s02.sh`
- **Phase 4 end-to-end docker-compose proof (M004/S03) complete:**
  - `scripts/verify_m004_s03.sh` posts intake, starts the worker with a fixture override, restarts the workflow, and proves RESEARCH_COMPLETE with API/DB evidence
- **Phase 5 compliance evaluation flow (M005/S01) complete:**
  - ComplianceEvaluation fixtures + persistence activity + migration with provenance/evidence JSONB
  - `PermitCaseWorkflow` advances RESEARCH_COMPLETE → COMPLIANCE_COMPLETE after persisting compliance evaluation
  - Read surface: `GET /api/v1/cases/{case_id}/compliance`
  - Proof surface: `tests/m005_s01_compliance_workflow_test.py` (Temporal/Postgres integration)
- **Phase 5 incentive assessment flow (M005/S02) complete:**
  - IncentiveAssessment fixtures + persistence activity + migration with provenance/evidence JSONB
  - `PermitCaseWorkflow` advances COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE with 3-day freshness guard (`INV-SPS-INC-001`)
  - Read surface: `GET /api/v1/cases/{case_id}/incentives`
  - Proof surface: `tests/m005_s02_incentives_workflow_test.py` (Temporal/Postgres integration)
- **Phase 5 end-to-end docker-compose proof (M005/S03) complete:**
  - `scripts/verify_m005_s03.sh` drives the live API + worker to INCENTIVES_COMPLETE with fixture overrides
  - Runbook asserts ComplianceEvaluation + IncentiveAssessment persistence and ledger transitions via Postgres + API readbacks
  - R013/R014 validated via integration tests + runbook proof
- **Phase 6 document generation + package persistence (M006-h7v2qk) complete:**
  - Phase 6 fixture dataset with deterministic document templates + loader with case_id override support
  - SubmissionPackage + DocumentArtifact schema with migration applied
  - EvidenceRegistry helper for sha256-validated document/manifest artifact storage
  - Document generator producing deterministic bytes from templates with sha256 digest computation
  - persist_submission_package activity with transactional package persistence + evidence registration
  - Workflow transition INCENTIVES_COMPLETE → DOCUMENT_COMPLETE (implemented)
  - API endpoints for package/manifest retrieval (implemented)
  - R015 validated (with operational notes): deterministic document generation + digest computation proven in pytest; full persistence + API proven in S02 (live end-to-end execution deferred due to Temporal task queue configuration issues)

- **Phase 7 submission attempt + manual fallback slice (M007/S01) complete:**
  - SubmissionAttempt + ManualFallbackPackage schema with receipt evidence linkage
  - Deterministic submission adapter activity with idempotent persistence and manual fallback generation
  - Proof bundle guard enforced before SUBMITTED transition
  - Case API read surfaces for submission attempts and manual fallback packages
  - R016/R018/R019 validated via integration tests (`tests/m007_s01_*`)
- **Phase 7 status normalization + tracking events (M007/S02) complete:**
  - Phase 7 status mapping fixtures + loader selection with version metadata
  - ExternalStatusEvent model + persistence activity with fail-closed unknown status handling
  - Case API ingest/list endpoints for normalized external status events
  - Integration tests for known/unknown status + API readback (`tests/m007_s02_external_status_events_test.py`)
- **Phase 7 live submission + tracking runbook (M007/S03) complete:**
  - `scripts/verify_m007_s03.sh` boots docker-compose, runs migrations, and executes intake → review → submission → status ingest
  - Runbook fetches receipt evidence metadata + download URL and asserts submission/status persistence via Postgres helpers
  - Operational proof of receipt evidence + ExternalStatusEvent persistence with real API + worker entrypoints

- **Phase 4 milestone M004-lp1flz complete:**
  - Intake, jurisdiction, and requirements workers are wired end-to-end with fixture-backed artifacts and live runbook proof.
- **Contradiction blocking guard is complete (M003/S03):**
  - `POST /api/v1/contradictions/` creates contradiction artifacts with `blocking_effect` and `resolution_status=OPEN`; 409 on duplicate
  - `POST /api/v1/contradictions/{id}/resolve` transitions `OPEN → RESOLVED`; 409 if already resolved; 404 if unknown
  - `GET /api/v1/contradictions/{id}` — read-only inspection surface; returns full artifact including resolution state
  - All three endpoints gated with `require_reviewer_api_key`
  - `apply_state_transition` contradiction guard: blocking open contradictions deny `REVIEW_PENDING → APPROVED_FOR_SUBMISSION` before the review gate check with `event_type=CONTRADICTION_ADVANCE_DENIED`, `guard_assertion_id=INV-SPS-CONTRA-001`, `normalized_business_invariants=["INV-003"]`
  - Non-blocking contradictions (`blocking_effect=false`) are transparent to the guard
  - Proof surfaces: 3 integration tests (`tests/m003_s03_contradiction_blocking_test.py`) + operator runbook (`scripts/verify_m003_s03.sh`) exits 0 against docker-compose Postgres
- **Reviewer independence guard is complete (M003/S02):**
  - `subject_author_id` is a required field on `CreateReviewDecisionRequest`; guard is fail-closed with no skip path
  - Self-approval (`reviewer_id == subject_author_id`) → 403 with `guard_assertion_id=INV-SPS-REV-001` and `normalized_business_invariants=["INV-008"]`; zero DB writes on denial
  - Accepted decisions receive `reviewer_independence_status='PASS'` in the `review_decisions` row
  - WARNING log `reviewer_api.independence_denied` emitted before any DB operation on denial
  - Proof surfaces: integration test (`tests/m003_s02_reviewer_independence_test.py`) — both denial path (no DB row) and acceptance path (PASS in DB) against real Postgres
- **Phase 2 Temporal harness + guarded transitions are complete (M002/S01–S03):**
  - Temporal worker entrypoint + deterministic PermitCaseWorkflow (bootstrap → denial → wait for `ReviewDecision` signal → resume)
  - Operator CLI to start workflows and send `ReviewDecision` signals
  - Postgres-authoritative guarded PermitCase state transitions with idempotent transition ledger (denied + applied) and deterministic correlation/request IDs
  - Proof surfaces: offline history replay determinism test (Replayer), post-commit activity retry idempotency test (failpoints), and `scripts/verify_m002_s03_runbook.sh`
- **Phase 1 authoritative data foundations are complete (M001):**
  - Postgres schema + Alembic migrations for core entities
  - Evidence registry wired to Postgres + S3-compatible object storage (MinIO) with integrity checks
  - Legal-hold persistence + INV-004 enforcement guardrails preventing destructive delete/purge of held evidence

## Architecture / Key Patterns

- Runtime binding (normative): Temporal + Python workers/activities; Postgres authoritative store; S3-compatible object storage; strong schema enforcement at trust boundaries.
- Early implementation prioritizes:
  - authoritative data model + migrations
  - evidence registry with stable IDs
  - retention/legal hold enforcement surfaces

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: Phase 1 — authoritative data foundations — Postgres schema + evidence registry + retention/legal-hold guardrails
- [x] M002: Phase 2 — Temporal harness + guarded state transitions
- [x] M003: Phase 3 — reviewer service + independence/dissent/contradiction governance (**COMPLETE — all slices done**)
- [ ] M004: Phase 4–7 — domain workers, submission/tracking/manual fallback, release/rollback gates, conformance hardening
- [x] M004-lp1flz: Phase 4 — intake, jurisdiction, and requirements workers
- [x] M005-j3c8qk: Phase 5 — compliance and incentives workers
- [x] M006-h7v2qk: Phase 6 — document and submission package generation
- [ ] M007-b2t1rz: Phase 7 — submission, tracking, and manual fallback
- [ ] M008-z1k9mp: Phase 8 — reviewer UI + independence thresholds
- [ ] M009-ct4p0u: Phase 9 — release, rollback, and observability gates
- [ ] M010-w8n5cl: Phase 10 — security boundaries (auth/RBAC/mTLS/redaction)
- [ ] M011-kg7s2p: Phase 11 — comment resolution, resubmission, and approval tracking
- [ ] M012-v8s3qn: Phase 12 — emergency and override governance
- [ ] M013-n6p1tg: Phase 13 — admin policy/config governance

## Milestone ID Mapping

- M001 → M001-r2v2t3 (complete)
- M002 → M002-dq2dn9 (complete)
- M003 → M003-ozqkoh (complete)
- M004 → M004-lp1flz (complete)
- M005 → M005-j3c8qk (complete)
- M006 → M006-h7v2qk (complete)
