# M007-b2t1rz / S02 — Research
**Date:** 2026-03-16

## Summary
S02 is responsible for R017 (status normalization + tracking events). The codebase currently lacks any `ExternalStatusEvent` DB model, migration, API surface, or workflow/activity logic for ingesting and normalizing external statuses. Phase 7 fixtures only contain submission adapter data; there is no status mapping fixture dataset yet. The authoritative contract exists in `model/sps/contracts/external-status-event.schema.json`, and the spec mandates fail-closed normalization into a fixed enum set, so this slice needs to build the storage + normalization path from scratch while reusing the fixture loader pattern and idempotent activity approach established in earlier phases.

Primary recommendation: implement Phase 7 status mapping fixtures under `specs/sps/build-approved/fixtures/phase7`, add a loader mirroring `src/sps/fixtures/phase6.py`/`phase7.py`, define `ExternalStatusEvent` model + migration + API contracts, and add a deterministic activity that normalizes raw status via the fixture map and persists `ExternalStatusEvent` rows. Unknown raw statuses must map to `UNKNOWN_EXTERNAL_STATUS` and raise/deny before any workflow state transition is attempted; the activity should fail closed and log enough context for operators.

## Recommendation
Follow the existing fixture-loading and idempotent activity patterns. Add a Phase 7 status map fixture file (versioned, with adapter family + mapping version metadata), then implement a loader in `src/sps/fixtures/phase7.py` that selects mapping entries for the case/portal family (mirroring the Phase 6/7 fixture override behavior). Implement a new activity (in `src/sps/workflows/permit_case/activities.py`) to normalize and persist `ExternalStatusEvent` with strict validation against the contract enum. Add DB model + migration and API read/write endpoints (likely under `/cases/{case_id}/external-status-events` and an ingest endpoint). Keep workflow deterministic by keeping all normalization/persistence in activities and ensuring failures are explicit and fail closed.

## Don't Hand-Roll
| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Fixture loading + case_id overrides | `src/sps/fixtures/phase6.py`, `src/sps/fixtures/phase7.py` | Keeps fixture provenance tied to spec package and maintains a consistent override pattern (`SPS_PHASE7_FIXTURE_CASE_ID_OVERRIDE`). |
| Idempotent persistence for activities | `deterministic_submission_adapter` in `src/sps/workflows/permit_case/activities.py` | Demonstrates retry-safe insert + IntegrityError recovery and logging conventions. |
| ExternalStatusEvent contract shape | `model/sps/contracts/external-status-event.schema.json` | Defines normalized status enum and required fields; ensures API + DB schema align to spec. |

## Existing Code and Patterns
- `src/sps/fixtures/phase7.py` — Phase 7 fixture loader (currently only submission adapter). Extend with status mapping dataset loader and case_id override reuse.
- `src/sps/fixtures/phase6.py` — Example fixture selection + override pattern; reuse for status mappings.
- `src/sps/workflows/permit_case/activities.py` — Idempotent submission adapter activity with retry-safe DB insert and logging; mirror for status persistence.
- `src/sps/api/routes/cases.py` — Pattern for case-scoped read endpoints (submission attempts/manual fallback); follow for external status events list.
- `model/sps/contracts/external-status-event.schema.json` — Authoritative contract for normalized status events.
- `model/sps/model.yaml` — Canonical ExternalStatusEvent field list and required fields.

## Constraints
- Workflow code must remain deterministic: all normalization and persistence must happen in activities.
- Unmapped statuses must normalize to `UNKNOWN_EXTERNAL_STATUS` and fail closed (spec Section 18A).
- Phase 7 fixtures must live under `specs/sps/build-approved/fixtures/phase7` (Decision #77).
- External status events must not directly mutate PermitCase state without guard checks (spec Section 18A).

## Common Pitfalls
- **Fail-open status mapping** — Avoid defaulting to a generic “OK” status; unknowns must map to `UNKNOWN_EXTERNAL_STATUS` and halt advancement.
- **Missing mapping version metadata** — Status maps must be versioned; without a version field, auditability is lost.
- **Not correlating to submission_attempt_id** — ExternalStatusEvent requires `submission_attempt_id`; missing this breaks audit linkage to submissions.

## Open Risks
- Status mapping fixtures are absent today; if they land without strict validation (schema or required fields), normalization will be brittle.
- Adding ExternalStatusEvent DB schema touches core persistence and may require test cleanup patterns similar to S01’s deterministic IDs.

## Skills Discovered
| Technology | Skill | Status |
|------------|-------|--------|
| Temporal (Python) | wshobson/agents@temporal-python-testing | available (not installed) |
| FastAPI | wshobson/agents@fastapi-templates | available (not installed) |
| SQLAlchemy | bobmatnyc/claude-mpm-skills@sqlalchemy-orm | available (not installed) |

## Sources
- ExternalStatusEvent contract enum + required fields (source: [model/sps/contracts/external-status-event.schema.json](model/sps/contracts/external-status-event.schema.json))
- Canonical ExternalStatusEvent model fields (source: [model/sps/model.yaml](model/sps/model.yaml))
- Phase 7 fixture loader + override pattern (source: [src/sps/fixtures/phase7.py](src/sps/fixtures/phase7.py))
- Phase 6 fixture loader example (source: [src/sps/fixtures/phase6.py](src/sps/fixtures/phase6.py))
- Submission adapter activity pattern for idempotent persistence (source: [src/sps/workflows/permit_case/activities.py](src/sps/workflows/permit_case/activities.py))
- Spec normalization rules and fail-closed requirement (source: [specs/sps/build-approved/spec.md](specs/sps/build-approved/spec.md))
