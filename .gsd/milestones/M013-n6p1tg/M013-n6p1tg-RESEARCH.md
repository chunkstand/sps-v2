# M013-n6p1tg — Research
**Date:** 2026-03-16

## Summary
Phase 13 needs a net-new governed admin change workflow; there is no existing admin policy/config mutation surface. The codebase already has patterns for governed authority changes (review decisions, overrides, contradictions) and audit sinks, but ReviewDecision rows are case-bound (case_id is non-null) which constrains reusing the existing reviewer API for admin-only changes without introducing a synthetic case or a new review artifact type. The most direct implementation is to introduce dedicated admin intent/change artifacts (with explicit change types for portal support metadata, source rules, and incentive programs), a reviewer approval record, and a governed apply endpoint that refuses to mutate authoritative config unless a valid approval exists. This aligns with spec §5.5 and the R035 requirement while preserving fail-closed governance.

The practical recommendation is to model admin change intent and review as first-class artifacts with audit events emitted in the same transaction as each state change. Reuse existing patterns: RBAC Role.ADMIN + reviewer approvals via Role.REVIEWER, idempotent keys on writes, and audit_events emissions. Avoid coupling to the PermitCase workflow unless there is a strong need for Temporal orchestration; admin mutations can be governed through API paths + Postgres enforcement, similar to overrides/emergencies.

## Recommendation
Define an **admin intent → review → apply** pipeline with its own data model and endpoints, and make the apply endpoint the sole mutation path for portal support metadata, source rules, and incentive program sources. Store intent, review decision, and applied change records in Postgres; emit audit_events for each step. Gate intent creation by Role.ADMIN, gate review decisions by Role.REVIEWER, and make apply fail closed if no approved review is linked. Use the existing idempotency + structured log patterns from review/override routes and follow audit/event patterns in `sps.audit.events` for durable audit trails.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Durable audit trail for authority actions | `sps.audit.events.emit_audit_event` + `audit_events` table | Already used for critical actions and aligns with OBS-001; reuse to keep audit semantics consistent. |
| High-risk mutation gating | `require_roles(Role.…)` + fail-closed HTTPException patterns in reviewer/override routes | Standardized denial logging + consistent authorization behavior. |
| Idempotent mutation writes | Review/override endpoints with unique keys and IntegrityError handling | Avoid double-apply and keep retries safe under concurrency. |

## Existing Code and Patterns
- `src/sps/api/routes/reviews.py` — authoritative reviewer decision creation + idempotency + independence guard; useful pattern for reviewer-gated admin approvals and audit emission.
- `src/sps/api/routes/overrides.py` / `src/sps/api/routes/emergencies.py` — governed artifact creation with RBAC gating and structured logs; shows API-side persistence + fail-closed behavior.
- `src/sps/audit/events.py` — centralized audit event persistence; should wrap admin intent/review/apply steps.
- `src/sps/auth/rbac.py` — Role.ADMIN exists with override behavior; use to gate admin intent creation and apply endpoints.
- `src/sps/db/models.py` — ReviewDecision requires `case_id` (non-null) and indexes by object_type/object_id, so admin change approvals should likely use a new table rather than reusing ReviewDecision.
- `src/sps/fixtures/phase5.py` / `src/sps/fixtures/phase7.py` — current source rule/incentive and portal support metadata are fixture-backed; admin governance will need a new authoritative store or versioning strategy beyond fixtures.
- `scripts/verify_m012_s01.sh` — runbook structure with docker-compose + API interactions + Postgres assertions; reuse format for M013 operational proof.

## Constraints
- ReviewDecision rows require a non-null `case_id`, which limits reuse for admin-only approvals without creating synthetic cases.
- Fixtures currently source portal support metadata and incentive program data; direct admin mutation must avoid silently diverging from fixture provenance without explicit versioning.

## Common Pitfalls
- **Silent authority drift via direct config writes** — enforce a single governed apply endpoint and refuse direct DB writes in code paths.
- **Using ReviewDecision for admin approvals without a case** — either create a new admin review table or introduce a dedicated “admin change” case type; otherwise schema constraints will break or semantics will be unclear.

## Open Risks
- Admin change types are not explicitly enumerated in the codebase; scope creep is likely unless a minimal, spec-aligned set is defined up front (portal support metadata, source rules, incentive programs).

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available |
| FastAPI | mindrally/skills@fastapi-python | available |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available |
| Alembic | wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review | available |
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| Postgres | wshobson/agents@postgresql-table-design | available |

Promising skills (install commands):
- `npx skills add wshobson/agents@fastapi-templates`
- `npx skills add mindrally/skills@fastapi-python`
- `npx skills add bobmatnyc/claude-mpm-skills@sqlalchemy-orm`
- `npx skills add wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review`
- `npx skills add wshobson/agents@temporal-python-testing`
- `npx skills add wshobson/agents@postgresql-table-design`

## Sources
- Admin governance requirements and acceptance criteria (source: [spec.md](specs/sps/build-approved/spec.md))
- Reviewer decision authority and idempotency patterns (source: [reviews.py](src/sps/api/routes/reviews.py))
- Audit event sink helper (source: [events.py](src/sps/audit/events.py))
- Override/emergency governed mutation patterns (source: [overrides.py](src/sps/api/routes/overrides.py), [emergencies.py](src/sps/api/routes/emergencies.py))
- ReviewDecision schema constraints (source: [models.py](src/sps/db/models.py))
- Fixture-backed policy/config data (source: [phase5.py](src/sps/fixtures/phase5.py), [phase7.py](src/sps/fixtures/phase7.py))
- Runbook structure for operational proof (source: [verify_m012_s01.sh](scripts/verify_m012_s01.sh))
