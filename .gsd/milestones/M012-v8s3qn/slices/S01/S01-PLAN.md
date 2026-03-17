# S01: Emergency/override artifacts + guard enforcement + lifecycle proof

**Goal:** Implement GOV-005 emergency declaration and override workflows with time-bounded artifacts enforced in workflow/guard paths

**Demo:** Emergency can be declared via API (escalation-owner role), overrides can be created with time bounds, protected transitions are denied without valid override and allowed with active override, expired overrides deny transitions, EMERGENCY_HOLD entry/exit proven via docker-compose, full lifecycle runbook exercises declare → bypass → expire → cleanup with real API + worker + Postgres

## Must-Haves

- EmergencyRecord and OverrideArtifact ORM models with time-bounded fields and FK constraints to permit_cases
- Alembic migration creating emergency_records and override_artifacts tables
- POST /api/v1/emergencies endpoint (escalation-owner RBAC) for declaring emergencies with 24h max duration enforcement
- POST /api/v1/overrides endpoint (escalation-owner RBAC) for creating override artifacts with scope + time bounds
- Override guard in apply_state_transition validating override_id existence, expires_at > NOW(), and affected_surfaces includes transition
- EMERGENCY_HOLD state transitions: REVIEW_PENDING → EMERGENCY_HOLD (emergency declaration), EMERGENCY_HOLD → REVIEW_PENDING (cleanup with reviewer confirmation)
- Guard assertion INV-SPS-EMERG-001 enforcement with OVERRIDE_DENIED event type in transition ledger
- Integration tests: override guard (deny without override, allow with valid override, deny with expired override)
- Integration tests: EMERGENCY_HOLD entry/exit transitions
- Docker-compose runbook proving full lifecycle with real API + worker + Postgres

## Proof Level

- This slice proves: final-assembly (integration + operational)
- Real runtime required: yes (docker-compose with Postgres + Temporal + worker + API)
- Human/UAT required: no

## Verification

- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_override_guard_test.py -v` — override guard enforcement (deny without override, allow with valid override, deny with expired override)
- `SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_emergency_hold_test.py -v` — EMERGENCY_HOLD entry/exit transitions
- `bash scripts/verify_m012_s01.sh` — docker-compose runbook (declare emergency → create override → protected transition → expire override → transition denial → cleanup)
- `docker compose exec postgres psql -U sps -d sps -c "SELECT override_id, expires_at < NOW() as expired FROM override_artifacts ORDER BY created_at DESC LIMIT 5"` — inspect override expiry state for recent artifacts
- `docker compose exec postgres psql -U sps -d sps -c "SELECT event_type, details->>'guard_assertion_id' as guard_id FROM transition_ledger WHERE event_type='OVERRIDE_DENIED' ORDER BY created_at DESC LIMIT 3"` — verify override denial events include guard assertion ID

## Observability / Diagnostics

- Runtime signals: `emergency_api.emergency_declared` (INFO, fields: emergency_id, case_id, scope, expires_at), `override_api.override_created` (INFO, fields: override_id, scope, expires_at, affected_surfaces), `workflow.override_denied` (WARNING, fields: workflow_id, case_id, transition, override_id=None|expired, guard_assertion_id=INV-SPS-EMERG-001)
- Inspection surfaces: GET /api/v1/emergencies/{emergency_id}, GET /api/v1/overrides/{override_id}, docker compose exec postgres psql queries for emergency_records/override_artifacts tables, transition ledger OVERRIDE_DENIED events
- Failure visibility: override denial includes guard_assertion_id=INV-SPS-EMERG-001 + normalized_business_invariants=[INV-006] in transition ledger
- Redaction constraints: none (emergency/override metadata is operational, not PII)

## Integration Closure

- Upstream surfaces consumed: StateTransitionRequest.override_id field (src/sps/workflows/permit_case/contracts.py), CaseState.EMERGENCY_HOLD enum (src/sps/workflows/permit_case/contracts.py), ArtifactClass.OVERRIDE_RECORD enum (src/sps/evidence/models.py), guard assertion INV-SPS-EMERG-001 (invariants/sps/guard-assertions.yaml), RBAC escalation-owner role (Phase 10)
- New wiring introduced in this slice: override validation in apply_state_transition activity before protected transitions, EMERGENCY_HOLD state transitions in PermitCaseWorkflow, emergency/override API endpoints with RBAC gates
- What remains before the milestone is truly usable end-to-end: nothing (S01 delivers complete emergency/override governance capability)

## Tasks

- [x] **T01: EmergencyRecord and OverrideArtifact ORM models + migration** `est:1h`
  - Why: Authoritative persistence for emergency/override artifacts with time bounds and scope constraints
  - Files: `src/sps/db/models.py`, `alembic/versions/*_emergency_override_artifacts.py`
  - Do: Add EmergencyRecord model (emergency_id PK, incident_id str, case_id FK, scope str, declared_by str, started_at timestamp, expires_at timestamp, allowed_bypasses JSONB, forbidden_bypasses JSONB, cleanup_due_at timestamp nullable); add OverrideArtifact model (override_id PK, case_id FK, scope str, justification str, start_at timestamp, expires_at timestamp, affected_surfaces JSONB, approver_id str, cleanup_required bool); generate migration with FK constraints and indexes on case_id + expires_at
  - Verify: alembic upgrade head runs cleanly, docker compose exec postgres psql shows emergency_records and override_artifacts tables with FK constraints
  - Done when: Migration applied, tables exist, FK constraints verified via \d emergency_records and \d override_artifacts

- [x] **T02: POST /api/v1/emergencies endpoint with 24h max duration** `est:1h`
  - Why: Bounded emergency declaration surface gated by escalation-owner role
  - Files: `src/sps/api/routes/emergencies.py`, `src/sps/api/contracts/emergencies.py`, `src/sps/api/main.py`
  - Do: Add CreateEmergencyRequest contract (incident_id required, scope str, allowed_bypasses list, forbidden_bypasses list); add EmergencyResponse contract (emergency_id, case_id, expires_at, cleanup_due_at); create emergencies router with POST / endpoint requiring escalation-owner role; enforce expires_at <= started_at + 24h with 422 on violation; persist EmergencyRecord row with idempotent emergency_id generation; emit emergency_api.emergency_declared log; include router in main.py app
  - Verify: curl POST with escalation-owner JWT returns 201 + emergency_id; curl POST with 25h duration returns 422; curl POST without escalation-owner JWT returns 403; docker exec postgres psql shows emergency_records row
  - Done when: API endpoint enforces 24h max, RBAC gate works, persistence proven via DB query

- [x] **T03: POST /api/v1/overrides endpoint with scope validation** `est:1h`
  - Why: Time-bounded override artifact creation gated by escalation-owner role
  - Files: `src/sps/api/routes/overrides.py`, `src/sps/api/contracts/overrides.py`, `src/sps/api/main.py`
  - Do: Add CreateOverrideRequest contract (case_id required, scope str, justification str, duration_hours int, affected_surfaces list required); add OverrideResponse contract (override_id, expires_at, affected_surfaces); create overrides router with POST / endpoint requiring escalation-owner role; compute expires_at = now + duration_hours; persist OverrideArtifact row with idempotent override_id generation; emit override_api.override_created log; include router in main.py app
  - Verify: curl POST with escalation-owner JWT returns 201 + override_id; curl POST without escalation-owner JWT returns 403; docker exec postgres psql shows override_artifacts row with affected_surfaces JSONB
  - Done when: API endpoint persists override with time bounds and scope, RBAC gate works

- [x] **T04: Override guard in apply_state_transition activity** `est:2h`
  - Why: Fail-closed enforcement of override validity before allowing protected transitions
  - Files: `src/sps/workflows/permit_case/activities.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: Add _validate_override() helper after _check_contradiction_blocking() in apply_state_transition; if StateTransitionRequest.override_id is not None: query OverrideArtifact by override_id, deny with OVERRIDE_DENIED if not found or expires_at <= now() or transition not in affected_surfaces, emit workflow.override_denied log with guard_assertion_id=INV-SPS-EMERG-001 + normalized_business_invariants=[INV-006]; insert OVERRIDE_DENIED transition ledger event on denial; allow transition if override is valid and active
  - Verify: Integration test: transition with override_id=None → allowed (no override required yet); transition with override_id='nonexistent' → OVERRIDE_DENIED + INV-SPS-EMERG-001; transition with expired override → OVERRIDE_DENIED; transition with valid override → allowed
  - Done when: Override guard enforces time bounds, scope, and existence; denials include guard assertion ID and normalized invariants

- [x] **T05: EMERGENCY_HOLD state transitions in workflow** `est:1.5h`
  - Why: Governed emergency state entry/exit with cleanup workflow
  - Files: `src/sps/workflows/permit_case/workflow.py`, `src/sps/workflows/permit_case/contracts.py`
  - Do: Add emergency_hold_entry signal handler that accepts EmergencyHoldRequest (emergency_id, target_state=EMERGENCY_HOLD); add emergency_hold_exit signal handler that accepts EmergencyHoldExitRequest (target_state required, reviewer_confirmation_id required); extend workflow to handle REVIEW_PENDING → EMERGENCY_HOLD transition (validate emergency_id exists and not expired); extend workflow to handle EMERGENCY_HOLD → target_state transition (validate reviewer_confirmation_id exists); emit workflow.emergency_hold_entered and workflow.emergency_hold_exited logs
  - Verify: Integration test: signal emergency_hold_entry with valid emergency_id → case enters EMERGENCY_HOLD; signal emergency_hold_exit with reviewer_confirmation_id → case exits to target_state; transition ledger shows both transitions
  - Done when: EMERGENCY_HOLD entry/exit transitions work, require valid artifacts, are proven via integration test

- [x] **T06: Integration tests for override guard enforcement** `est:1.5h`
  - Why: Prove override guard denies transitions without valid override and allows with active override
  - Files: `tests/m012_s01_override_guard_test.py`
  - Do: Seed PermitCase in REVIEW_PENDING state; test 1: attempt REVIEW_PENDING → APPROVED_FOR_SUBMISSION without override_id → success (no override required on this transition yet); test 2: seed blocking contradiction, attempt transition with override_id='nonexistent' → OVERRIDE_DENIED + guard_assertion_id=INV-SPS-EMERG-001; test 3: seed valid override with expires_at in past, attempt transition → OVERRIDE_DENIED; test 4: seed valid override with expires_at in future and affected_surfaces includes transition → success; assert transition ledger events include guard_assertion_id and normalized_business_invariants
  - Verify: SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_override_guard_test.py -v passes all 4 test cases
  - Done when: Override guard enforcement proven via Temporal+Postgres integration tests

- [x] **T07: Integration tests for EMERGENCY_HOLD transitions** `est:1h`
  - Why: Prove EMERGENCY_HOLD entry/exit transitions require valid artifacts
  - Files: `tests/m012_s01_emergency_hold_test.py`
  - Do: Seed PermitCase in REVIEW_PENDING state; test 1: POST /emergencies creates EmergencyRecord, signal emergency_hold_entry → case enters EMERGENCY_HOLD, transition ledger shows entry event; test 2: attempt EMERGENCY_HOLD → SUBMITTED without exit signal → denied (forbidden transition per spec); test 3: signal emergency_hold_exit with reviewer_confirmation_id → case exits EMERGENCY_HOLD to REVIEW_PENDING, transition ledger shows exit event; assert all state changes are in ledger with correlation IDs
  - Verify: SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_emergency_hold_test.py -v passes all 3 test cases
  - Done when: EMERGENCY_HOLD lifecycle proven via Temporal+Postgres integration tests

- [x] **T08: Docker-compose runbook for full emergency/override lifecycle** `est:2h`
  - Why: Operational proof of end-to-end emergency/override governance with real API + worker + Postgres
  - Files: `scripts/verify_m012_s01.sh`
  - Do: Provision docker-compose stack (scripts/start_temporal_dev.sh), start worker + API; STEP 1: POST /cases to create case in REVIEW_PENDING; STEP 2: POST /emergencies with case_id → 201 + emergency_id; STEP 3: POST /overrides with case_id + affected_surfaces=[REVIEW_PENDING→APPROVED_FOR_SUBMISSION] → 201 + override_id; STEP 4: seed blocking contradiction, POST /reviews/decisions with override_id → 201 (transition allowed with override); STEP 5: UPDATE override_artifacts SET expires_at=NOW()-'1 hour'::interval WHERE override_id=...; STEP 6: POST /reviews/decisions with expired override_id → 403 + OVERRIDE_DENIED; STEP 7: signal emergency_hold_exit with reviewer_confirmation → case exits EMERGENCY_HOLD; assert all transitions in ledger; cleanup docker compose down -v
  - Verify: bash scripts/verify_m012_s01.sh exits 0, all 7 steps pass with expected HTTP status codes and DB state
  - Done when: Runbook proves declare → bypass → expire → cleanup lifecycle with real entrypoints

## Files Likely Touched

- `src/sps/db/models.py` — EmergencyRecord and OverrideArtifact ORM models
- `alembic/versions/*_emergency_override_artifacts.py` — migration
- `src/sps/api/routes/emergencies.py` — emergency declaration endpoint
- `src/sps/api/routes/overrides.py` — override creation endpoint
- `src/sps/api/contracts/emergencies.py` — emergency request/response contracts
- `src/sps/api/contracts/overrides.py` — override request/response contracts
- `src/sps/api/main.py` — router registration
- `src/sps/workflows/permit_case/activities.py` — override guard in apply_state_transition
- `src/sps/workflows/permit_case/workflow.py` — EMERGENCY_HOLD transitions
- `src/sps/workflows/permit_case/contracts.py` — emergency hold signal contracts
- `tests/m012_s01_override_guard_test.py` — override guard integration tests
- `tests/m012_s01_emergency_hold_test.py` — EMERGENCY_HOLD transition integration tests
- `scripts/verify_m012_s01.sh` — docker-compose runbook
