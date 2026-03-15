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
- **Phase 2 Temporal substrate is in place (M002/S01):**
  - Temporal worker entrypoint + deterministic PermitCaseWorkflow (bootstrap activity → wait for `ReviewDecision` signal)
  - Operator CLI to start workflows and send `ReviewDecision` signals
  - Opt-in Temporal/Postgres integration test proving the wait→signal→resume path
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
- [ ] M002: Phase 2 — Temporal harness + guarded state transitions
- [ ] M003: Phase 3 — reviewer service + independence/dissent/contradiction governance
- [ ] M004: Phase 4–7 — domain workers, submission/tracking/manual fallback, release/rollback gates, conformance hardening

## Milestone ID Mapping

- M001 → M001-r2v2t3 (complete)
- M002 → M002-dq2dn9 (queued)
