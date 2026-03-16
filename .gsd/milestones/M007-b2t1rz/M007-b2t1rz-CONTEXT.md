# M007-b2t1rz: Phase 7 — submission, tracking, and manual fallback — Context

**Gathered:** 2026-03-15
**Status:** Queued — pending auto-mode execution.

## Project Description

Implement Phase 7 submission, tracking, and manual fallback flows. This milestone introduces a single deterministic submission adapter family, fixture-based status normalization, receipt persistence, and manual fallback package generation for unsupported portals. All surfaces are wired into PermitCaseWorkflow with authoritative Postgres persistence and guarded transitions.

## Why This Milestone

With sealed packages produced in Phase 6, SPS still cannot submit, track, or handle unsupported portals. This milestone establishes the first governed submission attempt path, durable receipts, and a bounded manual fallback path, laying the groundwork for real adapter integrations later.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run a PermitCaseWorkflow that creates a SubmissionAttempt, persists a receipt artifact, and advances to SUBMITTED (or MANUAL_SUBMISSION_REQUIRED for unsupported cases).
- See normalized external status events persisted using fixture-based status maps.

### Entry point / environment

- Entry point: `./.venv/bin/uvicorn sps.api.main:app` + `./.venv/bin/python -m sps.workflows.worker`
- Environment: local dev (docker compose)
- Live dependencies involved: Postgres, Temporal, MinIO (receipt artifact storage)

## Completion Class

- Contract complete means: submission adapter contracts, receipt artifacts, and status normalization schema validate against spec/model.
- Integration complete means: a real workflow run executes a submission attempt, persists receipts, and records normalized status events.
- Operational complete means: tests and runbook prove end-to-end behavior against docker-compose Postgres/Temporal/MinIO.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A workflow run executes a submission attempt via the mock adapter, persists a receipt artifact, and records a SubmissionAttempt.
- Status events are normalized via fixture-based maps and persisted as ExternalStatusEvent records.
- Unsupported portal cases produce a ManualFallbackPackage and enter MANUAL_SUBMISSION_REQUIRED.

## Risks and Unknowns

- Adapter fidelity risk — mock adapter may diverge from real portal behaviors and require later reshaping.
- Status mapping completeness — fixture maps may be incomplete for real portal families.

## Existing Codebase / Prior Art

- `src/sps/workflows/permit_case/workflow.py` — orchestration to extend with submission/tracking paths.
- `src/sps/storage/s3.py` — evidence storage adapter for receipt artifacts.
- `model/sps/model.yaml` — SubmissionAttempt, ExternalStatusEvent, ManualFallbackPackage definitions.
- `specs/sps/build-approved/spec.md` — normative requirements F-006–F-008 and tracking policy.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R016 — Idempotent submission adapters (G-001) and receipt persistence (G-002).
- R017 — Status normalization and tracking events (G-003).
- R018 — Manual fallback package generation (G-004).
- R019 — Proof bundle validation and reviewer confirmation (G-005).

## Scope

### In Scope

- Single deterministic submission adapter family.
- Receipt artifact persistence and SubmissionAttempt records.
- Fixture-based status normalization maps + ExternalStatusEvent persistence.
- Manual fallback package generation for unsupported portals.
- Workflow wiring for submission, tracking, and manual fallback paths.
- Integration tests + operator runbook proving end-to-end workflow progression.

### Out of Scope / Non-Goals

- Multiple portal adapter families or live portal integrations.
- Full reviewer UI for proof bundle confirmation (API-only in Phase 7).
- Payment processing, residential permitting, or autonomous authority mutation (spec non-goals).

## Technical Constraints

- Workflow code remains deterministic; all I/O via activities.
- Authoritative state mutation remains orchestrator/guard mediated.
- Submission adapters must be idempotent and fail closed on unknown statuses.

## Integration Points

- Postgres — authoritative persistence for SubmissionAttempt/ExternalStatusEvent/ManualFallbackPackage.
- Temporal — workflow orchestration and activity execution.
- MinIO/S3 — receipt artifact storage via evidence registry.

## Open Questions

- Where should status mapping fixtures live to keep provenance and versioning clear? — decide during planning.
