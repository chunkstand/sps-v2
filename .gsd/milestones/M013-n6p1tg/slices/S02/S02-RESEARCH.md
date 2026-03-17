# S02 — Research
**Date:** 2026-03-16

## Summary
S02 supports **R035** by extending the governed admin intent → review → apply workflow to **source rules** and **incentive programs** and proving it in a docker-compose runbook. The codebase already implements this workflow for portal support metadata with admin-only intent/apply, reviewer-only approvals, idempotency checks, and audit event emission in a single transaction. That pattern is ready to be replicated for two additional admin change types.

The blocking gap is that source rules and incentive programs are currently **fixture-backed** (phase4 requirements source_rankings and phase5 incentives fixtures), with no authoritative admin-managed tables or APIs. That means S02 must introduce new config tables and admin intent/review tables (mirroring portal support) and ensure apply endpoints are the *only* mutation path. The implementation should align to the existing service/router/test structure to avoid RBAC/audit drift and should include a runbook that validates intent → review → apply → audit for all three change types.

## Recommendation
Follow the established admin portal support pattern: create `admin_*_intents`, `admin_*_reviews`, and authoritative config tables for source rules and incentive programs; implement services that enforce intent existence, reviewer approval, and idempotency; wire routes with admin/reviewer RBAC and audit events; and add integration tests mirroring `tests/m013_s01_admin_portal_support_governance_test.py`. Replace fixture-only ownership by introducing these tables as the authoritative mutable store (fixtures can still seed data, but direct mutation must be denied outside the governed apply endpoint). Finish with a docker-compose runbook patterned after `scripts/verify_m012_s01.sh` to prove the end-to-end flow across portal support + source rules + incentives.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Durable audit trail for admin actions | `emit_audit_event` helper | Guarantees audit rows are written in the same DB transaction as the intent/review/apply operations. |
| RBAC enforcement for admin/reviewer boundaries | `require_roles(Role.ADMIN)` and reviewer-only helper in `admin_portal_support` routes | Keeps role separation consistent with portal support governance and avoids self-review. |
| Idempotent review recording | `admin_portal_support.load_review_by_idempotency_key` + conflict handling | Prevents double-recording reviews under retries and aligns with S01 pattern. |
| Alembic upgrade handling in tests | `command.upgrade(cfg, "heads")` pattern in S01 tests | Avoids multi-head migration failures as new admin tables are added. |

## Existing Code and Patterns
- `src/sps/services/admin_portal_support.py` — intent load, review lookup/idempotency, approved review gate, and upsert logic (pattern to replicate for source rules/incentive programs).
- `src/sps/api/routes/admin_portal_support.py` — admin intent/apply and reviewer-only approval endpoints with audit events and 409/403 handling.
- `src/sps/api/contracts/admin_portal_support.py` — request/response schema shapes for intent/review/apply.
- `src/sps/db/models.py` (PortalSupport + AdminPortalSupport* tables) — ORM shape, indexes, unique idempotency constraints.
- `alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py` — migration pattern for admin intent/review + authoritative config table.
- `tests/m013_s01_admin_portal_support_governance_test.py` — full end-to-end intent → review → apply assertions + audit event validation; reuse for S02 tests.
- `src/sps/fixtures/phase4.py` + `specs/sps/build-approved/fixtures/phase4/requirements.json` — source_rankings live only in fixtures; indicates source rules are not yet in an admin-managed store.
- `src/sps/fixtures/phase5.py` + `specs/sps/build-approved/fixtures/phase5/incentives.json` — incentive program data is embedded in fixtures only; no admin mutation surface exists.
- `scripts/verify_m012_s01.sh` — runbook structure for docker-compose + API + Postgres assertions (pattern for M013 S02 runbook).

## Constraints
- ReviewDecision requires `case_id` (non-null), so admin approvals must stay on dedicated admin review tables (Decision #111).
- Source rules and incentive programs are currently fixture-backed; S02 must introduce authoritative mutable tables or there is no governed mutation path.
- Admin governance applies fail-closed: apply must 409/deny without an approved review and emit audit events only on success.
- Alembic has multiple heads; new migrations must keep tests upgrading to `heads` (not `head`).

## Common Pitfalls
- **Reviewer role bypass** — reusing `require_roles(Role.REVIEWER)` without reviewer-only guard allows admin tokens; ensure reviewer-only enforcement mirrors S01.
- **Missing audit emissions** — forgetting `emit_audit_event` per step breaks the required audit trail and the runbook assertions.
- **Fixture drift** — leaving workflows dependent on fixtures without a migration path to new config tables can create silent divergence between admin updates and runtime behavior.

## Open Risks
- Precise schema for “source rules” and “incentive programs” is not yet encoded in the DB; mapping fixture structures to authoritative tables may require interpretation (source_rankings vs program catalog).

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates | available |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available |
| Alembic | wispbit-ai/skills@sqlalchemy-alembic-expert-best-practices-code-review | available |
| Postgres | wshobson/agents@postgresql-table-design | available |
| Docker Compose | manutej/luxor-claude-marketplace@docker-compose-orchestration | available (not installed) |
| Pydantic | bobmatnyc/claude-mpm-skills@pydantic | available (not installed) |

## Sources
- Admin intent/review/apply flow, RBAC, and audit event pattern (source: [src/sps/api/routes/admin_portal_support.py](src/sps/api/routes/admin_portal_support.py))
- Admin service helpers for intent/review requirements and upsert (source: [src/sps/services/admin_portal_support.py](src/sps/services/admin_portal_support.py))
- Admin portal support contracts and response shapes (source: [src/sps/api/contracts/admin_portal_support.py](src/sps/api/contracts/admin_portal_support.py))
- Portal support + admin intent/review ORM definitions (source: [src/sps/db/models.py](src/sps/db/models.py))
- Alembic migration pattern for admin governance tables (source: [alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py](alembic/versions/e3a9c4b7d2f1_admin_portal_support_governance.py))
- Source rankings fixture structure (source: [specs/sps/build-approved/fixtures/phase4/requirements.json](specs/sps/build-approved/fixtures/phase4/requirements.json))
- Incentive program fixture structure (source: [specs/sps/build-approved/fixtures/phase5/incentives.json](specs/sps/build-approved/fixtures/phase5/incentives.json))
- Runbook composition pattern for docker-compose + Postgres assertions (source: [scripts/verify_m012_s01.sh](scripts/verify_m012_s01.sh))
