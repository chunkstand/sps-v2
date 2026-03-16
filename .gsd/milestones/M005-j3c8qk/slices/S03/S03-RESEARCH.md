# M005-j3c8qk — S03 End-to-end docker-compose proof for compliance + incentives — Research

**Date:** 2026-03-15

## Summary
S03 doesn’t introduce new domain behavior; it proves the live docker-compose runtime path that already exists from S01/S02. The slice supports validated requirements R013 (ComplianceEvaluation) and R014 (IncentiveAssessment) by exercising the real entrypoints (uvicorn + worker), driving a workflow run to `INCENTIVES_COMPLETE`, and asserting persisted artifacts + ledger transitions via Postgres and the read-only case API endpoints. There is no S03 runbook script yet (only M004/M003 runbooks), so the missing work is to author a runbook patterned after `scripts/verify_m004_s03.sh` that covers compliance + incentives.

The existing patterns are strong: fixture override env vars for phase4 (`SPS_PHASE4_FIXTURE_CASE_ID_OVERRIDE`) and phase5 (`SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE`) ensure deterministic fixtures; the guard in `apply_state_transition` enforces freshness windows (30 days compliance, 3 days incentives); and `scripts/lib/assert_postgres.sh` already encodes containerized `psql` assertions. The runbook should reuse these pieces to avoid inventing new infra logic and to keep DB assertions inside docker compose (Decision #17).

## Recommendation
Create `scripts/verify_m005_s03.sh` by cloning the M004 S03 runbook structure and extending it to include compliance + incentives: start docker compose services, run migrations, start uvicorn, create a case via `/api/v1/cases`, enable both phase4 and phase5 fixture overrides, start the Temporal worker, run the workflow, then wait for `COMPLIANCE_COMPLETE` and `INCENTIVES_COMPLETE`. Assert artifact persistence via `compliance_evaluations` and `incentive_assessments` tables, and verify API readback via `GET /api/v1/cases/{case_id}/compliance` and `/incentives`. Clear fixture rows by fixture IDs (not only case_id) before reusing overrides, mirroring the M004 S03 cleanup pattern and Decision #70.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Docker-compose runbook scaffolding (start services, uvicorn/worker lifecycle, HTTP helpers) | `scripts/verify_m004_s03.sh` | Proven end-to-end runbook structure with safe cleanup, TCP readiness checks, and POST/GET helpers. |
| Postgres assertions without host psql | `scripts/lib/assert_postgres.sh` | Uses `docker compose exec` to run psql in-container and avoids exposing credentials (Decision #17). |
| Fixture override + case-id rewriting for deterministic artifacts | `src/sps/fixtures/phase4.py` + `src/sps/fixtures/phase5.py` | Guarantees deterministic fixture selection and safe runtime case_id mapping for runbook proofs. |

## Existing Code and Patterns
- `scripts/verify_m004_s03.sh` — Runbook template: docker compose up, migrations, uvicorn + worker, intake POST, workflow start, ledger polling, API GETs, and Postgres assertions.
- `scripts/lib/assert_postgres.sh` — Containerized psql assertion helpers; required for runbook DB checks (Decision #17).
- `src/sps/fixtures/phase5.py` — Phase 5 fixture selector + override (`SPS_PHASE5_FIXTURE_CASE_ID_OVERRIDE`) used for compliance/incentives.
- `specs/sps/build-approved/fixtures/phase5/compliance.json` — Fixture IDs and evaluated_at timestamp for compliance artifacts.
- `specs/sps/build-approved/fixtures/phase5/incentives.json` — Fixture IDs and assessed_at timestamp for incentives artifacts.
- `src/sps/workflows/permit_case/activities.py` — Guard enforcement for compliance (30-day freshness) and incentives (3-day freshness) in `apply_state_transition`.
- `src/sps/api/routes/cases.py` — Read-only endpoints `/api/v1/cases/{case_id}/compliance` and `/incentives` to verify persisted artifacts.

## Constraints
- Runbook DB assertions must use `docker compose exec` (see `scripts/lib/assert_postgres.sh`; Decision #17).
- Guard freshness windows are strict: compliance evaluated_at must be within 30 days; incentives assessed_at within 3 days (guards in `apply_state_transition`).
- Fixture override reuse must clear fixture rows by fixture IDs (Decision #70) to avoid idempotent insert conflicts.

## Common Pitfalls
- **Stale fixture timestamps** — If run after the freshness windows, the guard will deny advancement to COMPLIANCE/INCENTIVES; update fixtures or regenerate timestamps before running the runbook.
- **Forgetting fixture-id cleanup** — Clearing only by runtime case_id leaves fixture IDs in place and causes idempotent insert conflicts; delete by fixture IDs first.

## Open Risks
- The phase5 fixtures are static timestamps; if the runbook is executed long after fixture generation, the guard will fail (COMPLIANCE/INCENTIVES freshness denials) and the runbook will need to update fixtures.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available |
| FastAPI | wshobson/agents@fastapi-templates | available |
| PostgreSQL | wshobson/agents@postgresql-table-design | available |
| Docker Compose | manutej/luxor-claude-marketplace@docker-compose-orchestration | available |

## Sources
- Runbook template structure and lifecycle management (source: [scripts/verify_m004_s03.sh](scripts/verify_m004_s03.sh))
- Containerized Postgres assertions and docker-compose exec pattern (source: [scripts/lib/assert_postgres.sh](scripts/lib/assert_postgres.sh))
- Phase 5 fixture override env + selector helpers (source: [src/sps/fixtures/phase5.py](src/sps/fixtures/phase5.py))
- Compliance fixture IDs and evaluated_at timestamps (source: [specs/sps/build-approved/fixtures/phase5/compliance.json](specs/sps/build-approved/fixtures/phase5/compliance.json))
- Incentive fixture IDs and assessed_at timestamps (source: [specs/sps/build-approved/fixtures/phase5/incentives.json](specs/sps/build-approved/fixtures/phase5/incentives.json))
- Guard freshness windows for compliance and incentives (source: [src/sps/workflows/permit_case/activities.py](src/sps/workflows/permit_case/activities.py))
- API read surfaces for compliance/incentives (source: [src/sps/api/routes/cases.py](src/sps/api/routes/cases.py))
