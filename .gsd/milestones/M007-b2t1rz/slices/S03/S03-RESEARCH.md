# S03 — Research
**Date:** 2026-03-16

## Summary
S03 doesn’t own any *active* requirements directly; it provides the operational proof for previously validated R016–R019 by running a docker-compose runbook that drives intake → workflow submission → status ingest and confirms Postgres + MinIO persistence. The repo already contains robust runbook scaffolding (notably `scripts/verify_m005_s03.sh`) that handles API/worker lifecycle, Temporal task queue overrides, and Postgres assertions via containerized `psql`. Reusing that structure will keep S03 aligned with prior operational proofs and avoid new surface area.

The critical gaps are: (1) no Phase 7 runbook exists yet, (2) the submission flow requires reviewer approval before reaching `APPROVED_FOR_SUBMISSION`, so the runbook must post a ReviewDecision (use the M003/S01 runbook pattern), and (3) Phase 6 + Phase 7 fixture overrides must be set so document generation and submission adapters select deterministic fixtures. Receipt storage verification should use existing evidence endpoints to fetch metadata and a presigned download URL (proving MinIO storage without direct bucket access). Status ingest must use a raw status that appears in `specs/.../phase7/status-maps.json` and include the submission_attempt_id returned by the submission attempt read API.

## Recommendation
Implement S03 as a new `scripts/verify_m007_s03.sh` that copies the M005/S03 runbook structure: ensure docker compose services up, apply migrations, start API + worker with a unique `SPS_TEMPORAL_TASK_QUEUE`, run intake, post reviewer decision to advance to `APPROVED_FOR_SUBMISSION`, wait for submission states (`SUBMITTED` or `MANUAL_SUBMISSION_REQUIRED`), ingest a normalized status event, and then assert Postgres + evidence storage. Use fixture overrides (`SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE`, `SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`) and clean fixture rows like earlier runbooks to avoid idempotency conflicts.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Runbook lifecycle (docker compose, API/worker start, cleanup) | `scripts/verify_m005_s03.sh` | Established pattern with robust failure/cleanup diagnostics; consistent with prior runbooks. |
| Postgres assertions without exposing DSNs | `scripts/lib/assert_postgres.sh` | Uses docker compose exec; complies with decision #17 and avoids credential leakage. |
| Reviewer decision API + idempotency handling | `scripts/verify_m003_s01.sh` | Canonical reviewer API + Temporal signal path already proven. |
| Receipt artifact storage validation | `/evidence/artifacts/{artifact_id}` + `/download` in `src/sps/api/routes/evidence.py` | Proves MinIO-backed storage through presigned URL without direct S3 tooling. |

## Existing Code and Patterns
- `scripts/verify_m005_s03.sh` — End-to-end runbook template: API/worker boot, fixture override, workflow start, ledger polling, Postgres assertions.
- `scripts/lib/assert_postgres.sh` — Postgres assertions via docker compose exec; required for runbook proofs.
- `src/sps/workflows/permit_case/workflow.py` — Submission step occurs after `DOCUMENT_COMPLETE`; workflow requires reviewer approval to reach `APPROVED_FOR_SUBMISSION`.
- `src/sps/fixtures/phase6.py` — `SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE` used to select document fixtures.
- `src/sps/fixtures/phase7.py` — `SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE` selects submission adapter + status mapping fixtures.
- `src/sps/api/routes/cases.py` — Submission attempt + external status ingest/list + manual fallback endpoints used by runbook.
- `src/sps/api/routes/evidence.py` — Evidence metadata + presigned download URLs for receipt verification.

## Constraints
- Runbook Postgres assertions must use `docker compose exec` (decision #17); do not use host `psql` or echo DSNs.
- Workflow transitions are deterministic; all I/O must happen through activities, so the runbook should only use API/worker/Temporal entrypoints.
- Submission adapters depend on Phase 7 fixture selection; missing overrides will fail closed when no fixture exists.

## Common Pitfalls
- **Missing reviewer decision** — workflow never reaches `APPROVED_FOR_SUBMISSION`, so submission attempt never fires; post a ReviewDecision via reviewer API.
- **Fixture conflicts in persistent DBs** — deterministic IDs collide; clear fixture rows by fixture IDs (pattern from M004/M005 runbooks) before starting.
- **Unknown raw status** — status ingest fails closed with 409; select a raw status present in `status-maps.json` for the adapter family.

## Open Risks
- Task queue configuration drift (similar to M006 notes) could prevent the worker from polling the intended queue; runbook should set a unique `SPS_TEMPORAL_TASK_QUEUE` and ensure worker and workflow start use it.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |
| Docker Compose | manutej/luxor-claude-marketplace@docker-compose-orchestration | available (not installed) |
| MinIO | vm0-ai/vm0-skills@minio | available (not installed) |

## Sources
- Runbook scaffolding + fixture override pattern (source: [scripts/verify_m005_s03.sh](scripts/verify_m005_s03.sh))
- Postgres runbook assertion helpers (source: [scripts/lib/assert_postgres.sh](scripts/lib/assert_postgres.sh))
- Submission + status API endpoints (source: [src/sps/api/routes/cases.py](src/sps/api/routes/cases.py))
- Evidence metadata + presigned download endpoints (source: [src/sps/api/routes/evidence.py](src/sps/api/routes/evidence.py))
- Phase 6 fixture override env var (source: [src/sps/fixtures/phase6.py](src/sps/fixtures/phase6.py))
- Phase 7 fixture selection + override env var (source: [src/sps/fixtures/phase7.py](src/sps/fixtures/phase7.py))
- Workflow submission step placement (source: [src/sps/workflows/permit_case/workflow.py](src/sps/workflows/permit_case/workflow.py))
