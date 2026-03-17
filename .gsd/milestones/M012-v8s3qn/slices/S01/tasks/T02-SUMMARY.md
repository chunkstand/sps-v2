---
id: T02
parent: S01
milestone: M012-v8s3qn
provides:
  - POST /api/v1/emergencies endpoint with escalation-owner RBAC enforcement and 24h duration cap
  - CreateEmergencyRequest and EmergencyResponse contracts
  - Integration tests proving 201 success, 422 duration validation, 401/403 auth failures
key_files:
  - src/sps/api/routes/emergencies.py
  - src/sps/api/contracts/emergencies.py
  - tests/m012_s01_emergency_api_test.py
key_decisions:
  - Emergency duration defaults to 24h if not specified; explicit duration_hours field allows caller to specify shorter durations
  - cleanup_due_at computed as expires_at + 24h to allow 24-hour cleanup window after emergency expires
  - ESCALATION_OWNER role added to Role enum with value "escalation-owner"
patterns_established:
  - Emergency API follows contradiction/dissent API pattern with RBAC router-level dependency and per-endpoint identity injection
  - ULID-based ID generation pattern (EMERG-<ULID>) mirrors evidence artifact ID pattern
observability_surfaces:
  - emergency_api.emergency_declared (INFO, fields: emergency_id, case_id, scope, expires_at)
  - emergency_api.emergency_creation_failed (WARNING, fields: case_id, reason, error context)
  - HTTP 422 response body includes detailed error message, requested_hours, max_hours on duration violations
duration: 45m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: POST /api/v1/emergencies endpoint with 24h max duration

**Created POST /api/v1/emergencies endpoint gated by escalation-owner RBAC role with fail-closed 24-hour max duration enforcement and idempotent emergency_id generation.**

## What Happened

1. Added ESCALATION_OWNER role to `src/sps/auth/rbac.py` Role enum
2. Created emergency contracts in `src/sps/api/contracts/emergencies.py`:
   - CreateEmergencyRequest with incident_id, case_id, scope, allowed_bypasses, forbidden_bypasses, optional duration_hours
   - EmergencyResponse with emergency_id, case_id, incident_id, scope, declared_by, started_at, expires_at, cleanup_due_at
3. Created emergencies router in `src/sps/api/routes/emergencies.py`:
   - Router-level RBAC dependency requiring escalation-owner role
   - POST / endpoint with duration validation (422 if duration_hours > 24)
   - ULID-based emergency_id generation (EMERG-<ULID> pattern)
   - EmergencyRecord persistence with time bounds and cleanup_due_at
   - Structured logging on success and failure
4. Registered emergencies router in `src/sps/api/main.py` with prefix "/api/v1/emergencies"
5. Created integration tests in `tests/m012_s01_emergency_api_test.py` proving:
   - 201 on valid request with escalation-owner JWT
   - 422 with detailed error on duration > 24h
   - 401 without JWT
   - 403 with wrong role
   - Database persistence with FK to permit_cases

## Verification

All must-haves verified:
- ✅ CreateEmergencyRequest contract with all required fields
- ✅ POST endpoint enforces 24h max duration (422 on violation)
- ✅ Endpoint gated by escalation-owner role (403 without role, 401 without JWT)
- ✅ EmergencyRecord persistence with idempotent emergency_id generation
- ✅ Structured log emergency_api.emergency_declared implemented
- ✅ Router registered in main.py

Test results:
```
$ SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m012_s01_emergency_api_test.py -v
======================== 4 passed, 6 warnings in 0.62s ========================
test_create_emergency_success PASSED
test_create_emergency_duration_exceeds_24h PASSED
test_create_emergency_no_jwt PASSED
test_create_emergency_wrong_role PASSED
```

Database verification:
- Emergency row persisted with correct time bounds (expires_at = started_at + duration_hours)
- Duration enforced <= 24 hours
- cleanup_due_at computed as expires_at + 24h
- FK constraint to permit_cases enforced

## Diagnostics

**Inspect emergency records:**
```bash
docker compose exec postgres psql -U sps -d sps -c \
  "SELECT emergency_id, case_id, scope, expires_at > NOW() as active FROM emergency_records ORDER BY created_at DESC LIMIT 5"
```

**Check active vs expired emergencies:**
```bash
docker compose exec postgres psql -U sps -d sps -c \
  "SELECT emergency_id, case_id, expires_at, expires_at > NOW() as active, cleanup_due_at FROM emergency_records WHERE case_id = 'CASE-XXX'"
```

**Structured log signals:**
- `emergency_api.emergency_declared` — fires on successful emergency creation (INFO level)
- `emergency_api.emergency_creation_failed` — fires on duration validation failure or persistence error (WARNING level)

**Error responses:**
- 422 response includes `{"error": "INVALID_DURATION", "message": "Emergency duration cannot exceed 24 hours", "requested_hours": N, "max_hours": 24}`
- 401 response includes `{"error": "auth_required", "auth_reason": "missing_or_invalid_authorization"}`
- 403 response includes `{"error_code": "role_denied", "required_roles": ["escalation-owner"]}`

## Deviations

None. Implementation followed task plan exactly.

## Known Issues

None discovered. All tests pass, RBAC enforcement works, duration validation is fail-closed.

## Files Created/Modified

- `src/sps/auth/rbac.py` — Added ESCALATION_OWNER role to Role enum
- `src/sps/api/contracts/emergencies.py` — Created CreateEmergencyRequest and EmergencyResponse contracts
- `src/sps/api/routes/emergencies.py` — Created emergencies router with POST / endpoint, 24h duration enforcement, RBAC gate, and persistence
- `src/sps/api/main.py` — Registered emergencies router with prefix "/api/v1/emergencies"
- `tests/m012_s01_emergency_api_test.py` — Created integration tests proving RBAC enforcement, duration validation, and persistence
