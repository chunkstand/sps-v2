# M005-j3c8qk — Research
**Date:** 2026-03-15

## Summary
Phase 5 will extend the Phase 4 domain-worker pattern into compliance and incentives, but the current codebase stops at RESEARCH_COMPLETE. There are no ComplianceEvaluation/IncentiveAssessment tables in `src/sps/db/models.py`, no fixture loaders beyond Phase 4, and no workflow branches or guards for COMPLIANCE/INCENTIVES yet. The strongest reuse path is the Phase 4 fixture + activity + guard + API pattern (fixture selection with case overrides, idempotent inserts, guarded transitions, and read-only case endpoints), which already encodes determinism and provenance rules.

Primary recommendation: implement compliance and incentive fixtures under `specs/sps/build-approved/fixtures/phase5`, add fixture loaders and deterministic evaluators as activity code similar to `persist_requirement_sets`, add DB models/migrations + API response contracts in the same shape as Phase 4, then wire workflow branches from RESEARCH_COMPLETE → COMPLIANCE_COMPLETE → INCENTIVES_COMPLETE and add guard assertions for stale/invalid rule freshness. Prove by mirroring the Phase 4 integration test/runbook shape so the first proof is a full Temporal + Postgres run that persists artifacts and advances state.

## Recommendation
Reuse the Phase 4 activity/fixture/guard approach end-to-end: add phase5 fixture loader + selector, persist artifacts in activities, then use `apply_state_transition` to enforce guard checks on stale rule sources and missing evaluations. Update `PermitCaseWorkflow` to branch on RESEARCH_COMPLETE and execute compliance/incentive activities with deterministic request IDs. Add read-only API endpoints mirroring `/cases/{case_id}/requirements` and re-run Temporal integration tests against docker-compose to prove persistence + progression. This minimizes new patterns and keeps determinism and idempotency guarantees consistent with earlier phases.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Deterministic, idempotent persistence in activities | Phase 4 `persist_jurisdiction_resolutions` / `persist_requirement_sets` | Uses fixture selection + idempotent insert + structured logging; proven in integration tests. |
| Guard invariant mapping for denials | `sps.guards.guard_assertions.get_normalized_business_invariants` | Standardizes denial payloads and invariant IDs; required for governance auditability. |
| Transition ledger + idempotency | `apply_state_transition` in activities | Centralized guard enforcement + retry-safe ledger pattern already proven. |

## Existing Code and Patterns
- `src/sps/workflows/permit_case/workflow.py` — Deterministic workflow branching; currently stops at RESEARCH_COMPLETE, needs compliance/incentive branches.
- `src/sps/workflows/permit_case/activities.py` — Activity pattern for fixture persistence and guard enforcement (`persist_requirement_sets`, `apply_state_transition`).
- `src/sps/fixtures/phase4.py` — Fixture loader + case_id override pattern to reuse for phase5.
- `src/sps/api/routes/cases.py` — Read-only case endpoints for jurisdiction/requirements; template for compliance/incentive GET endpoints.
- `src/sps/db/models.py` — No ComplianceEvaluation/IncentiveAssessment models yet; Phase 5 must add these + migration.
- `tests/m004_s02_jurisdiction_requirements_workflow_test.py` — Integration test/runbook shape for Temporal + Postgres progression.
- `invariants/sps/guard-assertions.yaml` — Guard assertion registry (currently missing a CTL-04 entry for compliance freshness).

## Constraints
- Workflow determinism: all I/O must remain in activities (`PermitCaseWorkflow` only orchestrates).
- Guard assertions must reference the registry in `invariants/sps/guard-assertions.yaml`.
- Fixture datasets are spec-sourced; Phase 4 fixtures live under `specs/sps/build-approved/fixtures/phase4` (pattern to follow).

## Common Pitfalls
- **Non-deterministic evaluation inside the workflow** — keep compliance/incentive evaluation and fixture loading inside activities, not workflow code.
- **Fixture ID collisions across runs** — follow Phase 4’s stable fixture IDs and optional case override to avoid idempotency conflicts.
- **Missing freshness guard IDs** — add guard assertion entries for compliance/incentive staleness so denials emit normalized invariants.

## Open Risks
- Fixture placement for phase5 is undecided; aligning with `specs/.../fixtures/phase4` is likely, but needs a decision.
- Guard assertion registry has no CTL-04 entry; missing ID will yield empty invariants until added.
- Rule evaluation determinism: any dynamic timestamps or external lookups in evaluators will break replay safety.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| FastAPI | wshobson/agents@fastapi-templates | available |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available |
| Pydantic | bobmatnyc/claude-mpm-skills@pydantic | available |

## Sources
- Workflow branching and current progression limits (source: `src/sps/workflows/permit_case/workflow.py`)
- Guard + idempotent activity patterns (source: `src/sps/workflows/permit_case/activities.py`)
- Fixture loader and case-id override pattern (source: `src/sps/fixtures/phase4.py`)
- Current absence of compliance/incentive DB models (source: `src/sps/db/models.py`)
- Guard assertion registry contents (source: `invariants/sps/guard-assertions.yaml`)
- Integration test structure for Temporal + Postgres (source: `tests/m004_s02_jurisdiction_requirements_workflow_test.py`)
- Compliance/Incentive model fields (source: `model/sps/model.yaml`)
