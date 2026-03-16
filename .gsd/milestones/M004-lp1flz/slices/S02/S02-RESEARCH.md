# S02 — Research

**Date:** 2026-03-15

## Summary
S02 owns **R011 (jurisdiction resolution)** and **R012 (requirements retrieval with provenance)**. The current codebase has intake wiring (INTAKE_PENDING → INTAKE_COMPLETE), but no JurisdictionResolution/RequirementSet models, migrations, fixtures, or workflow/activities to persist them. The workflow exits after intake and the guard only recognizes REVIEW_PENDING and INTAKE transitions, so new JURISDICTION/RESEARCH steps must be added without breaking determinism.

Key gaps: (1) no fixture datasets exist under the decided `specs/sps/build-approved/fixtures/phase4` path, (2) no DB tables or models for JurisdictionResolution/RequirementSet, (3) no activities or workflow branches to persist these artifacts and advance to JURISDICTION_COMPLETE / RESEARCH_COMPLETE, and (4) no API/DB read surfaces for these artifacts. The existing patterns (activities for I/O, guard-mediated transitions, JSONB provenance) provide a clear blueprint, but S02 must add schema + fixture load + workflow wiring to meet the milestone definition and proof strategy.

## Recommendation
Follow the existing authority boundary pattern: add new models + Alembic migration for JurisdictionResolution and RequirementSet (JSONB for provenance-style payloads where needed), implement activity functions to load fixtures and persist these artifacts (with evidence/provenance ids), and extend `apply_state_transition` + `PermitCaseWorkflow` to perform INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE transitions. Ensure activities perform DB I/O and the workflow remains deterministic; the workflow should fetch a case state snapshot, branch, and apply guarded transitions using deterministic request IDs in the same style as the intake path. Add API/DB read surfaces or runbook queries to inspect the persisted artifacts and their provenance.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Guarded state transitions | `apply_state_transition` activity + `StateTransitionRequest` | Keeps the deterministic workflow boundary and persists ledger events with denial metadata. |
| Temporal workflow orchestration | `PermitCaseWorkflow` + deterministic request IDs | Matches replay-safe patterns already proven in Phase 2/3/4. |
| Provenance/evidence persistence | `EvidenceArtifact` JSONB provenance pattern | Aligns with spec expectations for evidence IDs and provenance storage. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/workflow.py` — Deterministic orchestration, currently handles INTAKE and REVIEW flow; extend with JURISDICTION/RESEARCH branches using the same request-id pattern.
- `src/sps/workflows/permit_case/activities.py` — Guarded transitions + DB I/O; extend `apply_state_transition` with new transitions and add new activities for fixture-backed persistence.
- `src/sps/db/models.py` — Project, PermitCase, EvidenceArtifact, and guard-related tables exist; add JurisdictionResolution and RequirementSet models here.
- `src/sps/workflows/worker.py` — Worker activity registration; must add new jurisdiction/requirements activities.
- `src/sps/api/routes/cases.py` — Intake API entrypoint pattern; reuse logging/error handling for any new read surfaces.
- `model/sps/model.yaml` — Authoritative shape for JurisdictionResolution and RequirementSet fields (support_level, evidence_ids, freshness_state, contradiction_state, etc.).

## Constraints
- All authoritative state mutation must happen inside activities; workflow code remains deterministic and orchestration-only.
- Guarded transitions must be applied via `apply_state_transition`; new transitions must be encoded there to avoid fail-open behavior.
- Fixture datasets must live under `specs/sps/build-approved/fixtures/phase4` per decision #42; the directory is currently missing.

## Common Pitfalls
- **Forgetting to extend the guard** — add new transitions to `apply_state_transition` or the workflow will get UNKNOWN_TRANSITION denials.
- **Missing fixture provenance fields** — RequirementSet/JurisdictionResolution must include evidence IDs and rankings; incomplete fixtures will block downstream guard logic and proofs.

## Open Risks
- Fixture fidelity risk: no Phase 4 fixtures exist yet, so the schema/provenance contract may drift from the spec if not defined carefully.
- Workflow wiring risk: new activity calls must preserve determinism and use guard-mediated transitions; direct DB writes from workflow code would violate constraints.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |

## Sources
- JurisdictionResolution + RequirementSet schema fields and enums (source: [model/sps/model.yaml](model/sps/model.yaml))
- Deterministic workflow orchestration + intake branch (source: [src/sps/workflows/permit_case/workflow.py](src/sps/workflows/permit_case/workflow.py))
- Guarded transition and DB mutation pattern (source: [src/sps/workflows/permit_case/activities.py](src/sps/workflows/permit_case/activities.py))
- Existing DB models (source: [src/sps/db/models.py](src/sps/db/models.py))
- Worker activity registration (source: [src/sps/workflows/worker.py](src/sps/workflows/worker.py))
- Intake API persistence pattern (source: [src/sps/api/routes/cases.py](src/sps/api/routes/cases.py))
