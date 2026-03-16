# S03 — Research

**Date:** 2026-03-15

## Summary
S03 is an operational proof slice: prove the real API + worker + Postgres + Temporal pipeline reaches RESEARCH_COMPLETE under docker-compose. The existing S01/S02 runbooks already start real processes and validate DB state, but they split the path: S01 exercises intake → INTAKE_COMPLETE and S02 seeds a fixture case_id to reach JURISDICTION/RESEARCH. There is no end-to-end runbook that uses the intake API and then proceeds through jurisdiction + requirements with live services under docker-compose.

The biggest constraint is fixture lookup: jurisdiction/requirements activities only match fixtures by `case_id`, while the intake API always generates a new ULID case_id and immediately starts the workflow. That means a naive “POST /api/v1/cases then wait for RESEARCH_COMPLETE” will fail with `LookupError` because fixtures are keyed to `CASE-EXAMPLE-001`. S03 will need a deliberate bridge (e.g., fixture override, fixture rewrite before workflow reaches the activities, or a deterministic case_id injection option) to keep the end-to-end runbook honest without breaking the spec-derived intake contract.

## Recommendation
Create a dedicated S03 runbook (likely `scripts/verify_m004_s03.sh`) that executes the intake API and verifies the workflow reaches RESEARCH_COMPLETE with persisted artifacts, but add a controlled mechanism to align the fixture case_id with the intake case_id. Options include: (a) add a test/runbook-only fixture override env var that maps the runtime case_id to fixtures, or (b) extend the runbook to pre-generate a case_id and pass it through a guarded API option (if allowed) before workflow start. Avoid ad-hoc DB seeding so the proof is truly “intake → jurisdiction → requirements” with live services. Also decide whether S03 requires docker-compose services for API/worker (current compose only provides infra); if so, add Dockerfile(s) + compose services and update runbook accordingly.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Postgres runbook assertions | `scripts/lib/assert_postgres.sh` helpers | Already enforces “psql inside docker compose” and safe-no-secret logging. |
| End-to-end infra boot + process lifecycle | `scripts/verify_m004_s01.sh` / `scripts/verify_m004_s02.sh` | Proven patterns for booting Temporal/Postgres, worker/API readiness, and ledger polling. |
| Fixture validation/shape | `src/sps/fixtures/phase4.py` | Enforces spec-aligned schema and evidence ID validation. |

## Existing Code and Patterns
- `scripts/verify_m004_s01.sh` — End-to-end intake runbook (API + worker + Temporal + Postgres) through INTAKE_COMPLETE; use as the base for API flow and logging/cleanup patterns.
- `scripts/verify_m004_s02.sh` — End-to-end workflow progression to RESEARCH_COMPLETE using fixture case_id seeding; reuse ledger polling and artifact assertions.
- `scripts/lib/assert_postgres.sh` — Postgres assertions via `docker compose exec` (matches decision #17); use for all runbook DB checks.
- `src/sps/fixtures/phase4.py` — Fixture loader keyed by `case_id`; currently requires exact match, no fallback.
- `src/sps/workflows/permit_case/activities.py` — `persist_jurisdiction_resolutions` / `persist_requirement_sets` raise on missing fixture case_id; this is the primary constraint for intake-based runs.
- `src/sps/api/routes/cases.py` — Intake API always generates case_id/project_id and auto-starts workflow; no override hook today.
- `docker-compose.yml` — Only infra services (postgres/temporal/minio); no API/worker containers yet.

## Constraints
- Workflow determinism: all I/O must remain in activities; workflow orchestration only (existing pattern in `permit_case/workflow.py`).
- Fixture lookup is `case_id`-exact; missing fixtures raise `LookupError` and will fail the run.
- Runbook DB assertions must use `docker compose exec` inside the postgres container (Decision #17).
- Intake API starts the workflow immediately; there is no hook to delay workflow until fixtures are adapted.

## Common Pitfalls
- **Intake case_id doesn’t match fixtures** — The workflow will fail during jurisdiction/requirements activities. Plan a deterministic mapping or override path.
- **Assuming docker-compose already runs API/worker** — Compose currently only provides infra; if S03 requires fully containerized API/worker, Dockerfiles and compose services are missing.
- **Forgetting unique Temporal task queue in runbooks** — Follow S01/S02’s task-queue randomization to avoid stale workflow polling conflicts.

## Open Risks
- The “intake → RESEARCH_COMPLETE” proof may require code changes (fixture override or case_id control) that could impact the intake contract if not carefully scoped.
- If S03 requires dockerized API/worker, building images and wiring env may expand scope beyond a runbook-only change.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (npx skills add wshobson/agents@temporal-python-testing) |
| Docker / docker-compose | sickn33/antigravity-awesome-skills@docker-expert | available (npx skills add sickn33/antigravity-awesome-skills@docker-expert) |
| Postgres | supabase/agent-skills@supabase-postgres-best-practices | available (npx skills add supabase/agent-skills@supabase-postgres-best-practices) |
| FastAPI | wshobson/agents@fastapi-templates | available (npx skills add wshobson/agents@fastapi-templates) |

## Sources
- Intake runbook flow + process orchestration (source: [scripts/verify_m004_s01.sh](../../../../scripts/verify_m004_s01.sh))
- Jurisdiction/requirements runbook + ledger assertions (source: [scripts/verify_m004_s02.sh](../../../../scripts/verify_m004_s02.sh))
- Fixture loader + case_id keyed datasets (source: [src/sps/fixtures/phase4.py](../../../../src/sps/fixtures/phase4.py))
- Jurisdiction/requirements activity lookup behavior (source: [src/sps/workflows/permit_case/activities.py](../../../../src/sps/workflows/permit_case/activities.py))
- Intake API auto-generates case_id + auto-starts workflow (source: [src/sps/api/routes/cases.py](../../../../src/sps/api/routes/cases.py))
- Docker-compose services limited to infra (source: [docker-compose.yml](../../../../docker-compose.yml))
