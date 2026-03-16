# M009-ct4p0u: Phase 9 — release, rollback, and observability gates — Roadmap

## Milestone Definition of Done

When this milestone is complete:
- Audit events are emitted for critical actions and queryable from Postgres
- A minimal `/ops` dashboard shows queue depth, contradiction backlog, and stalled reviews
- A release bundle CLI script generates manifests with artifact digests and compatibility checks
- Release gating fails closed on missing/stale artifacts or open blockers
- Rollback rehearsal evidence is captured and queryable from the evidence registry
- A post-release validation runbook template exists and is proven operational

## Slices

- [x] **S01: Audit Events and Minimal Dashboards** `risk:med` `depends:[]`
  - **Demo:** Operator visits `/ops` in a browser and sees live queue depth, contradiction backlog, and stalled review counts. Audit events for review decisions and state transitions are queryable from Postgres.
  - **Proof:** Integration tests prove `AuditEvent` persistence with correlation fields. `GET /api/v1/ops/dashboard/metrics` returns structured metrics. `/ops` Jinja page renders without errors.
  - **Verification:** `pytest tests/m009_s01_audit_events_test.py` + `pytest tests/m009_s01_dashboard_test.py`
  - **Requirements:** R022 (audit events), R023 (dashboards/alerts)

- [x] **S02: Release Bundle and Blocker Gates** `risk:med-high` `depends:[S01]`
  - **Demo:** Operator runs `python scripts/generate_release_bundle.py` and sees release bundle creation succeed with clean artifacts. Re-running with a modified artifact (hash mismatch) causes the script to exit 1 with a fail-closed error. Creating an open blocking contradiction causes the script to exit 1 citing the blocker.
  - **Proof:** `POST /api/v1/releases/bundles` persists a ReleaseBundle with artifact references. `GET /api/v1/ops/release-blockers` returns open blocking contradictions and unresolved dissents on high-risk surfaces. CLI script verifies hashes against `PACKAGE-MANIFEST.json` and queries the blocker endpoint.
  - **Verification:** `pytest tests/m009_s02_release_bundle_test.py` + `scripts/verify_m009_s02.sh` (live CLI execution with success/failure scenarios)
  - **Requirements:** R024 (release bundle manifest)

- [x] **S03: Rollback Rehearsal and Post-Release Validation** `risk:low` `depends:[S02]`
  - **Demo:** Operator runs `scripts/verify_m009_s03.sh` which records a rollback rehearsal artifact, retrieves it via the evidence API, and validates the post-release checklist template exists.
  - **Proof:** `POST /api/v1/releases/rollbacks/rehearsals` creates a `ROLLBACK_REHEARSAL` artifact in the evidence registry. `runbooks/sps/post-release-validation.md` template exists and references stage-gated validation steps.
  - **Verification:** `pytest tests/m009_s03_rollback_rehearsal_test.py` + `scripts/verify_m009_s03.sh` (end-to-end rollback rehearsal + validation template check)
  - **Requirements:** R025 (rollback rehearsal), R026 (post-release validation)

## Boundary Map

### Runtime Boundaries
- **Postgres** — audit_events table, release_bundles/release_artifacts tables, contradiction/dissent queries
- **Evidence Registry** — rollback rehearsal artifact storage
- **CLI** — release bundle generation script (fail-closed gating logic)
- **Browser** — `/ops` dashboard (Jinja2 + inline JS)

### Trust Boundaries
- `/api/v1/ops/*` endpoints — read-only observability surface (auth deferred to M010)
- `POST /api/v1/releases/bundles` — requires valid artifact references and blocker checks
- CLI script — validates artifact hashes locally before API submission

### Integration Points
- S01 → S02: Audit events provide structured logs for release gate checks
- S02 → S03: ReleaseBundle schema establishes the artifact reference pattern for rollback rehearsal
- All slices → Postgres: Single authoritative store for audit/release/rollback metadata

## Requirement Coverage

| Requirement | Status | Primary Owner | Supporting | Proof |
|-------------|--------|---------------|------------|-------|
| R022 — Audit event schema and sinks | validated | S01 | none | pytest + Postgres integration |
| R023 — Dashboards and alerts | validated | S01 | none | pytest + `/ops` page render |
| R024 — Release bundle manifest | validated | S02 | none | pytest + CLI script runbook |
| R025 — Rollback rehearsal evidence | validated | S03 | none | pytest + runbook |
| R026 — Post-release validation template | validated | S03 | none | runbook + template file check |

**Coverage summary:**
- Active requirements: 0
- Mapped to slices: 5
- Unmapped: 0

All requirements for this milestone are validated.

## Verification Classes

- **Contract:** Pydantic models for AuditEvent, ReleaseBundle, ReleaseBlocker responses
- **Integration:** Postgres-backed tests for audit event persistence, release bundle creation, rollback rehearsal artifact storage
- **Operational:** CLI script execution (S02), runbook proof (S03)
- **UI:** `/ops` dashboard page render and metrics API contract (S01)

## Notes

- Observability is intentionally minimal — queue depth, contradiction backlog, stalled reviews only per spec
- Release gating is fail-closed: missing/stale artifacts or open blockers deny release bundle creation
- Rollback rehearsal reuses existing evidence registry patterns (no new storage infrastructure)
- Post-release validation is a template/runbook only; actual staged rollout automation is deferred
