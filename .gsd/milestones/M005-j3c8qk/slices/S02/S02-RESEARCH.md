# S02: Incentive assessment artifacts + workflow advance — Research

**Date:** 2026-03-15

## Summary
S02 owns **R014 (Incentive assessment)**. The codebase currently implements compliance-only Phase 5 artifacts: fixture loading (`src/sps/fixtures/phase5.py`), persistence activity, workflow branching to `COMPLIANCE_COMPLETE`, and a read-only `/cases/{case_id}/compliance` endpoint. There is no IncentiveAssessment model, migration, fixtures, activity, workflow transition, guard assertion, or case API surface yet, so the slice must mirror the Phase 4/5 compliance pattern end-to-end to deliver the incentives artifact and advance the workflow to `INCENTIVES_COMPLETE`.

The spec/model define IncentiveAssessment shape and freshness rules: key fields include `assessment_id`, `candidate_programs`, `eligibility_status`, `stacking_conflicts`, `deadlines`, `source_ids`, `advisory_value_range`, and `authoritative_value_state`, and incentive sources must be revalidated within 3 days during active evaluation; stale incentive assessments must block auto-advance. The compliance slice already established the fixture override pattern, deterministic persistence, and guard enforcement with `INV-SPS-COMP-001`, so S02 should add an analogous incentive guard assertion and transition branch (`COMPLIANCE_COMPLETE -> INCENTIVES_COMPLETE`) with deterministic activity IDs and an idempotent persistence activity.

## Recommendation
Follow the compliance slice pattern precisely: add a Phase 5 incentive fixture dataset under `specs/sps/build-approved/fixtures/phase5`, extend `src/sps/fixtures/phase5.py` with Pydantic models + selector helpers, add an `IncentiveAssessment` ORM + Alembic migration, implement a `persist_incentive_assessment` activity mirroring `persist_compliance_evaluation`, and wire the workflow to persist incentives and attempt the guarded transition to `INCENTIVES_COMPLETE`. Add an incentives read endpoint and response models following the compliance/jurisdiction/requirements 404/409 conventions. Finally, add a guard assertion entry (likely `INV-SPS-INC-001`) to `invariants/sps/guard-assertions.yaml` and enforce a freshness window (spec calls for 3 days) during the `COMPLIANCE_COMPLETE -> INCENTIVES_COMPLETE` guard check.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Fixture selection + case override + deterministic load | `src/sps/fixtures/phase5.py` | Keeps incentives aligned with Phase 5 compliance fixture determinism and override semantics. |
| Idempotent, retry-safe persistence in activities | `persist_compliance_evaluation` in `src/sps/workflows/permit_case/activities.py` | Provides a proven pattern for idempotent inserts + logging + fixture override handling. |
| Guarded transition and ledgering | `apply_state_transition` in `src/sps/workflows/permit_case/activities.py` | Centralizes guard denial payloads and transition ledger writes; required for invariants. |
| Case read API shape + error conventions | `/cases/{case_id}/compliance` in `src/sps/api/routes/cases.py` | Ensures incentives endpoint follows established 404/409 patterns and logging. |

## Existing Code and Patterns
- `src/sps/fixtures/phase5.py` — compliance fixture schema and selector helpers; extend with incentives fixture models + selectors and reuse the override env var pattern.
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — only Phase 5 fixture present; incentives dataset must be added alongside.
- `src/sps/db/models.py` — includes `ComplianceEvaluation`; add `IncentiveAssessment` mapping with JSONB fields and timestamps.
- `alembic/versions/e1c2f4b5a6c7_compliance_evaluations.py` — migration pattern to mirror for incentives.
- `src/sps/workflows/permit_case/activities.py` — `persist_compliance_evaluation` shows idempotent persistence + fixture override; `apply_state_transition` contains compliance guard branch to mirror for incentives.
- `src/sps/workflows/permit_case/workflow.py` — current workflow stops at `COMPLIANCE_COMPLETE`; extend to persist incentives and attempt `INCENTIVES_COMPLETE` transition.
- `src/sps/api/contracts/cases.py` and `src/sps/api/routes/cases.py` — compliance response models and endpoint patterns to mirror for incentives.
- `invariants/sps/guard-assertions.yaml` — contains `INV-SPS-COMP-001` but no incentives guard; add new guard assertion ID for incentive freshness.
- `model/sps/model.yaml` — IncentiveAssessment fields and required attributes (source for schema shape).

## Constraints
- Workflow determinism: all fixture loading and DB I/O must occur in activities (workflow only orchestrates).
- Incentive freshness: spec requires official incentive sources to be revalidated within 3 days; stale assessments must block auto-advance.
- Guard assertion registry must include any new incentives guard assertion ID used by `apply_state_transition`.

## Common Pitfalls
- **Forgetting fixture override semantics** — use the Phase 5 override env var pattern so runbooks can use fixture data with runtime case IDs.
- **Missing guard assertion entry** — adding a guard in `apply_state_transition` without a registry entry yields empty invariant mappings.

## Open Risks
- Freshness window choice for incentives (spec says 3 days) must be encoded consistently in guard logic and test fixtures; inconsistent timestamps can stall advancement.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| FastAPI | wshobson/agents@fastapi-templates | available |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available |
| Pydantic | bobmatnyc/claude-mpm-skills@pydantic | available |

## Sources
- Phase 5 fixtures loader/selector and override env var (source: `src/sps/fixtures/phase5.py`).
- Compliance persistence activity + guard structure (source: `src/sps/workflows/permit_case/activities.py`).
- Workflow path ending at COMPLIANCE_COMPLETE (source: `src/sps/workflows/permit_case/workflow.py`).
- Compliance API response models and routes (source: `src/sps/api/contracts/cases.py`, `src/sps/api/routes/cases.py`).
- IncentiveAssessment model fields (source: `model/sps/model.yaml`).
- IncentiveAssessment purpose and freshness constraints (source: `specs/sps/build-approved/spec.md`, sections 8.2.6 and 18A.1).
- Guard assertion registry contents (source: `invariants/sps/guard-assertions.yaml`).
- Phase 5 fixture inventory (source: `specs/sps/build-approved/fixtures/phase5`).
