---
id: M003-ozqkoh
provides:
  - Reviewer API authority boundary for ReviewDecision writes + Temporal signal delivery
  - Reviewer independence guard (self-approval denial) on high-risk review surfaces
  - Contradiction artifacts with manual create/resolve and advancement blocking
  - Dissent artifacts persisted and queryable for ACCEPT_WITH_DISSENT decisions
key_decisions:
  - ReviewDecision writes are authoritative in HTTP API; workflows consume decision_id via signal
  - Reviewer independence guard runs before any DB operation and fails closed
  - Contradiction guard precedes review gate in REVIEW_PENDING → APPROVED_FOR_SUBMISSION
  - ACCEPT_WITH_DISSENT persists a dissent artifact in the same transaction
patterns_established:
  - Async reviewer endpoint with post-commit Temporal signal delivery and structured logs
  - Guard denials return stable guard_assertion_id + normalized_business_invariants
  - Router-level reviewer API key dependency reused across reviewer surfaces
  - Integration tests against real Postgres/Temporal + operator runbooks for end-to-end proof
observability_surfaces:
  - reviewer_api.decision_received/persisted/signal_sent/signal_failed logs
  - reviewer_api.independence_denied warning log
  - CONTRADICTION_ADVANCE_DENIED ledger events with guard_assertion_id
  - reviewer_api.dissent_artifact_created log + GET /api/v1/dissents/{dissent_id}
requirement_outcomes:
  - id: R006
    from_status: active
    to_status: validated
    proof: Temporal+Postgres integration test + verify_m003_s01.sh runbook (HTTP review → Postgres decision → Temporal signal → workflow resume)
  - id: R007
    from_status: active
    to_status: validated
    proof: tests/m003_s02_reviewer_independence_test.py (self-approval 403 + INV-SPS-REV-001 + INV-008, no DB row; distinct reviewer PASS)
  - id: R008
    from_status: active
    to_status: validated
    proof: tests/m003_s03_contradiction_blocking_test.py + verify_m003_s03.sh (blocking contradiction denies; resolve allows advance)
  - id: R009
    from_status: active
    to_status: validated
    proof: tests/m003_s04_dissent_artifacts_test.py + verify_m003_s04.sh (ACCEPT_WITH_DISSENT persists dissent artifact; ACCEPT does not)
duration: ~4h
verification_result: passed
completed_at: 2026-03-16
---

# M003-ozqkoh: Phase 3 — reviewer service + independence/dissent/contradiction governance

**Reviewer API authority boundary with independence, contradiction, and dissent governance enforced and proven end-to-end.**

## What Happened

M003 flipped the ReviewDecision authority boundary so the reviewer HTTP API is the sole writer, then layered governance policies on top. S01 delivered the core integration path (HTTP → Postgres → Temporal signal → workflow resume) with idempotency enforcement and durable logging. S02 added the independence guard with fail-closed self-approval denial before any DB write. S03 introduced contradiction artifacts and a new guard in the state transition activity that blocks advancement until blocking contradictions are resolved, plus full create/resolve/read endpoints. S04 completed the governance set by persisting dissent artifacts for ACCEPT_WITH_DISSENT decisions and exposing a read endpoint, including a transaction ordering fix to keep audit trail integrity. All slices were proven with Postgres-backed integration tests and operator runbooks against docker-compose services.

## Cross-Slice Verification

- **Workflow unblock by reviewer API:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s01_reviewer_api_boundary_test.py -v -s` and `bash scripts/verify_m003_s01.sh` prove HTTP review decision → Postgres row → Temporal signal → workflow `APPROVED_FOR_SUBMISSION`.
- **Idempotency conflict:** S01 integration test asserts 409 `IDEMPOTENCY_CONFLICT` on same key with different decision_id.
- **Reviewer independence denial:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s02_reviewer_independence_test.py -v -s` proves 403 with `guard_assertion_id=INV-SPS-REV-001` + `INV-008` and zero DB writes.
- **Contradiction blocking + resolve:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s03_contradiction_blocking_test.py -v -s` + `bash scripts/verify_m003_s03.sh` prove `CONTRADICTION_ADVANCE_DENIED` while open and successful advance after resolve.
- **Dissent artifacts:** `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m003_s04_dissent_artifacts_test.py -v -s` + `bash scripts/verify_m003_s04.sh` prove dissent artifacts are persisted and queryable for ACCEPT_WITH_DISSENT and absent for ACCEPT.

## Requirement Changes

- R006: active → validated — HTTP reviewer service is authoritative writer with Temporal signal resume, proven by integration test + runbook.
- R007: active → validated — independence self-approval denial proven with 403 guard IDs and no DB row.
- R008: active → validated — contradiction artifacts block advancement until resolved, proven via tests + runbook.
- R009: active → validated — dissent artifacts persisted and queryable, proven via tests + runbook.

## Forward Intelligence

### What the next milestone should know
- Review decision persistence is now fully HTTP-driven; legacy Temporal signal-only tests must use the reviewer API pattern or they will fail on missing decision_id.
- Contradiction and dissent APIs are gated by `require_reviewer_api_key` and follow the same router pattern; reuse this structure for future governance surfaces.
- Dissent artifact insertion depends on an explicit `db.flush()` before inserting the dissent row to avoid FK ordering issues.

### What's fragile
- Signal delivery remains best-effort; a failed signal leaves a review durable but the workflow paused — operators must re-signal via Temporal CLI.
- The `db.flush()` ordering workaround in ACCEPT_WITH_DISSENT is easy to regress if refactored without a relationship declaration.

### Authoritative diagnostics
- `docker compose logs api | grep reviewer_api` — shows decision lifecycle including signal failures.
- `SELECT event_type, payload FROM case_transition_ledger WHERE case_id='...' ORDER BY occurred_at;` — shows guard denials and approvals with stable identifiers.
- `GET /api/v1/contradictions/{id}` / `GET /api/v1/dissents/{id}` — API-level truth for artifacts without DB access.

### What assumptions changed
- SQLAlchemy did not order ReviewDecision/DissentArtifact inserts without a relationship; explicit `db.flush()` was required to avoid FK violations.

## Files Created/Modified

- `src/sps/api/routes/reviews.py` — reviewer API authority boundary, independence guard, dissent persistence
- `src/sps/api/routes/contradictions.py` — contradiction artifact endpoints
- `src/sps/api/routes/dissents.py` — dissent artifact read endpoint
- `src/sps/workflows/permit_case/activities.py` — contradiction guard in state transition
- `tests/m003_s01_reviewer_api_boundary_test.py` — S01 integration proof
- `tests/m003_s02_reviewer_independence_test.py` — S02 integration proof
- `tests/m003_s03_contradiction_blocking_test.py` — S03 integration proof
- `tests/m003_s04_dissent_artifacts_test.py` — S04 integration proof
- `scripts/verify_m003_s01.sh` — S01 operator runbook
- `scripts/verify_m003_s03.sh` — S03 operator runbook
- `scripts/verify_m003_s04.sh` — S04 operator runbook
