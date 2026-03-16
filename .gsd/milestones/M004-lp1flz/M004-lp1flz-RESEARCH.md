# M004-lp1flz — Research

**Date:** 2026-03-15

## Summary
Phase 4 needs to extend the current Temporal + Postgres authority boundary into the intake → jurisdiction → research pipeline, but the codebase only contains the Phase 2/3 guard and review flow. The workflow already enforces deterministic behavior and DB-side governance via `apply_state_transition`, and the `Project` table exists, yet there is no intake API, no intake contract, and no JurisdictionResolution/RequirementSet persistence (models, migrations, activities, or fixtures). The highest-risk gap is wiring new domain activities into the workflow while preserving deterministic state transitions and the “all I/O in activities” constraint.

Primary recommendation: implement and prove the intake/jurisdiction/requirements pipeline in the same pattern as Phase 2/3: spec-derived Pydantic contracts at boundaries, new Postgres models/migrations with JSONB for provenance, new activities that persist durable artifacts, and workflow wiring that only orchestrates and uses the existing transition guard. Start proof with a single end-to-end workflow run against docker-compose Postgres/Temporal (runbook + integration test), then harden with fixture-based datasets and provenance/evidence validations.

## Recommendation
Reuse the existing guard/activity patterns: introduce activities to (1) normalize intake into a `Project`, (2) resolve jurisdiction using fixture data, and (3) retrieve requirements with provenance/evidence. Wire them into `PermitCaseWorkflow` as deterministic orchestration steps with guarded transitions (INTAKE_PENDING → INTAKE_COMPLETE → JURISDICTION_COMPLETE → RESEARCH_COMPLETE). Update the worker registration, add migrations/models for JurisdictionResolution/RequirementSet, and add runbook/test surfaces that validate live Postgres rows and state transitions.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Deterministic workflow orchestration | `PermitCaseWorkflow` + `apply_state_transition` activity | Proven deterministic orchestration + guarded DB writes; consistent audit trail and idempotency. |
| Postgres session + activity logging | `get_sessionmaker()` + activity logging in `activities.py` | Already wired for Temporal activity context and audit-friendly logs. |
| Evidence/provenance persistence | `EvidenceArtifact` model + JSONB payload pattern | Existing schema pattern for provenance and evidence IDs; aligns with spec. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/workflow.py` — deterministic orchestration that delegates all I/O to activities and uses state transition guard results.
- `src/sps/workflows/permit_case/activities.py` — authoritative DB mutation pattern (guarded transitions, idempotency, failpoints).
- `src/sps/workflows/permit_case/contracts.py` — Pydantic contract pattern aligned to model schemas and Temporal data converter.
- `src/sps/workflows/worker.py` — worker registration; will need to add new activities.
- `src/sps/db/models.py` — Project model exists; JurisdictionResolution/RequirementSet do not (must add).
- `scripts/verify_m003_s01.sh` — runbook pattern for end-to-end verification against docker-compose Postgres/Temporal.
- `specs/sps/build-approved/spec.md` — F-001/F-002/F-003 and entity definitions for Project/JurisdictionResolution/RequirementSet.

## Constraints
- All authoritative state mutation must occur inside activities (workflow code is deterministic and orchestration-only).
- Guarded transitions are enforced via `apply_state_transition`; new transitions must remain fail-closed and audit all attempts.
- Phase 4 uses spec-sourced fixtures only (no external integrations).

## Common Pitfalls
- **Skipping workflow determinism** — keep all DB/network work in activities; do not import DB clients in workflow code.
- **Missing schema/migration alignment** — add JurisdictionResolution/RequirementSet tables plus JSONB provenance fields before wiring activities to avoid runtime FK/missing table errors.
- **Fixture provenance drift** — ensure fixture payloads include evidence IDs and source rankings required by the RequirementSet schema.

## Open Risks
- Fixture fidelity vs. spec: incomplete fixture datasets could force later migrations or refactors when compliance/document phases arrive.
- Transition table growth: `apply_state_transition` currently only handles REVIEW_PENDING → APPROVED_FOR_SUBMISSION; new intake/jurisdiction/research transitions need guard rules or must be explicitly scoped for Phase 4.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (`npx skills add wshobson/agents@temporal-python-testing`) |
| FastAPI | wshobson/agents@fastapi-templates | available (`npx skills add wshobson/agents@fastapi-templates`) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (`npx skills add bobmatnyc/claude-mpm-skills@sqlalchemy-orm`) |

## Sources
- Project/Jurisdiction/Requirement definitions and F-001–F-003 requirements (source: [spec.md](specs/sps/build-approved/spec.md))
- Domain model shapes for JurisdictionResolution/RequirementSet (source: [model.yaml](model/sps/model.yaml))
- Workflow orchestration and guard pattern (source: [workflow.py](src/sps/workflows/permit_case/workflow.py))
- Activity/guard implementation pattern (source: [activities.py](src/sps/workflows/permit_case/activities.py))
- End-to-end runbook pattern (source: [verify_m003_s01.sh](scripts/verify_m003_s01.sh))
