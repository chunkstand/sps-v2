---
estimated_steps: 7
estimated_files: 4
---

# T02: POST /api/v1/emergencies endpoint with 24h max duration

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Create POST /api/v1/emergencies endpoint gated by escalation-owner RBAC role, enforcing 24-hour max emergency duration with fail-closed validation. Persists EmergencyRecord rows with idempotent emergency_id generation and emits structured log on successful declaration.

## Steps

1. Create src/sps/api/contracts/emergencies.py with CreateEmergencyRequest (incident_id str, scope str, allowed_bypasses list[str], forbidden_bypasses list[str]) and EmergencyResponse (emergency_id, case_id, expires_at, cleanup_due_at)
2. Create src/sps/api/routes/emergencies.py with POST / endpoint requiring escalation-owner role via require_role() dependency
3. Implement endpoint logic: compute expires_at = started_at + 24h; if request includes duration_hours > 24, return 422 with error message "Emergency duration cannot exceed 24 hours"; generate emergency_id = f"EMERG-{ulid.new().str}"; persist EmergencyRecord row; emit log emergency_api.emergency_declared (INFO, fields: emergency_id, case_id, scope, expires_at); return 201 + EmergencyResponse
4. Register emergencies router in src/sps/api/main.py with prefix "/api/v1/emergencies"
5. Add escalation-owner role to RBAC role map if not already present
6. Write integration test: POST with valid escalation-owner JWT → 201; POST with duration_hours=25 → 422; POST without JWT → 401; POST with wrong role → 403
7. Verify via docker compose: curl POST with escalation-owner JWT + case_id → 201, docker exec postgres psql shows emergency_records row

## Must-Haves

- [ ] CreateEmergencyRequest contract with incident_id, scope, allowed_bypasses, forbidden_bypasses
- [ ] POST /emergencies endpoint enforces 24h max duration (422 on violation)
- [ ] Endpoint gated by escalation-owner role (403 without role)
- [ ] EmergencyRecord persistence with idempotent emergency_id generation
- [ ] Structured log emergency_api.emergency_declared emitted on success
- [ ] Router registered in main.py

## Verification

- `curl -X POST http://localhost:8000/api/v1/emergencies -H "Authorization: Bearer <escalation-owner-jwt>" -d '{"incident_id":"INC-001","case_id":"CASE-001","scope":"high_risk","allowed_bypasses":[],"forbidden_bypasses":[]}' | jq .emergency_id` returns emergency_id
- `curl -X POST http://localhost:8000/api/v1/emergencies -H "Authorization: Bearer <escalation-owner-jwt>" -d '{"incident_id":"INC-001","case_id":"CASE-001","scope":"high_risk","duration_hours":25}' | jq .detail` returns error about 24h limit
- `docker compose exec postgres psql -U sps -d sps -c "SELECT * FROM emergency_records"` shows persisted row

## Observability Impact

- Signals added/changed: emergency_api.emergency_declared (INFO, fields: emergency_id, case_id, scope, expires_at)
- How a future agent inspects this: GET /api/v1/emergencies/{emergency_id} (to be added in T02 if needed) or docker exec postgres psql query
- Failure state exposed: 422 response body includes validation error message; emergency_api.emergency_creation_failed log (WARNING) on persistence errors

## Inputs

- Phase 10 RBAC pattern (require_role() dependency from src/sps/api/auth.py)
- EmergencyRecord ORM model from T01
- JWT generation helper for escalation-owner role (Phase 10 test utils)

## Expected Output

- `src/sps/api/contracts/emergencies.py` — CreateEmergencyRequest and EmergencyResponse contracts
- `src/sps/api/routes/emergencies.py` — POST / endpoint with RBAC + duration enforcement + persistence
- `src/sps/api/main.py` — emergencies router registration
