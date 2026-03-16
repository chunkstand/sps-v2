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
- [ ] M003: Phase 3 — reviewer service + independence/dissent/contradiction governance
- [ ] M004: Phase 4–7 — domain workers, submission/tracking/manual fallback, release/rollback gates, conformance hardening

## Milestone ID Mapping

- M001 → M001-r2v2t3 (complete)
- M002 → M002-dq2dn9 (complete)
- M003 → M003-ozqkoh (queued)
