---
estimated_steps: 6
estimated_files: 4
---

# T03: POST /api/v1/overrides endpoint with scope validation

**Slice:** S01 — Emergency/override artifacts + guard enforcement + lifecycle proof
**Milestone:** M012-v8s3qn

## Description

Create POST /api/v1/overrides endpoint gated by escalation-owner RBAC role, persisting OverrideArtifact rows with scope + time bounds. Enables explicit override artifact creation required for guard bypass enforcement.

## Steps

1. Create src/sps/api/contracts/overrides.py with CreateOverrideRequest (case_id str, scope str, justification str, duration_hours int, affected_surfaces list[str]) and OverrideResponse (override_id, expires_at, affected_surfaces)
2. Create src/sps/api/routes/overrides.py with POST / endpoint requiring escalation-owner role via require_role() dependency
3. Implement endpoint logic: compute start_at = now(), expires_at = start_at + duration_hours; generate override_id = f"OVR-{ulid.new().str}"; persist OverrideArtifact row (approver_id from JWT claims, cleanup_required=True); emit log override_api.override_created (INFO, fields: override_id, scope, expires_at, affected_surfaces); return 201 + OverrideResponse
4. Register overrides router in src/sps/api/main.py with prefix "/api/v1/overrides"
5. Write integration test: POST with valid escalation-owner JWT → 201 + override_id; POST without JWT → 401; POST with wrong role → 403; docker exec postgres psql shows override_artifacts row with affected_surfaces JSONB
6. Verify via docker compose: curl POST with escalation-owner JWT → 201, psql query shows override_artifacts row

## Must-Haves

- [ ] CreateOverrideRequest contract with case_id, scope, justification, duration_hours, affected_surfaces
- [ ] POST /overrides endpoint gated by escalation-owner role (403 without role)
- [ ] OverrideArtifact persistence with computed expires_at and affected_surfaces JSONB
- [ ] Structured log override_api.override_created emitted on success
- [ ] Router registered in main.py

## Verification

- `curl -X POST http://localhost:8000/api/v1/overrides -H "Authorization: Bearer <escalation-owner-jwt>" -d '{"case_id":"CASE-001","scope":"reviewer_independence","justification":"Emergency bypass","duration_hours":2,"affected_surfaces":["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]}' | jq .override_id` returns override_id
- `docker compose exec postgres psql -U sps -d sps -c "SELECT override_id, affected_surfaces FROM override_artifacts"` shows persisted row with JSONB affected_surfaces

## Observability Impact

- Signals added/changed: override_api.override_created (INFO, fields: override_id, scope, expires_at, affected_surfaces)
- How a future agent inspects this: GET /api/v1/overrides/{override_id} (to be added if needed) or docker exec postgres psql query
- Failure state exposed: 422 on missing required fields; override_api.override_creation_failed (WARNING) on persistence errors

## Inputs

- Phase 10 RBAC pattern (require_role() dependency)
- OverrideArtifact ORM model from T01
- JWT generation helper for escalation-owner role (Phase 10 test utils)

## Expected Output

- `src/sps/api/contracts/overrides.py` — CreateOverrideRequest and OverrideResponse contracts
- `src/sps/api/routes/overrides.py` — POST / endpoint with RBAC + persistence
- `src/sps/api/main.py` — overrides router registration
