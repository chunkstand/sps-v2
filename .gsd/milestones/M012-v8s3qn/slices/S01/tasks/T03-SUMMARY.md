---
id: T03
parent: S01
milestone: M012-v8s3qn
provides:
  - POST /api/v1/overrides endpoint with escalation-owner RBAC enforcement
  - CreateOverrideRequest and OverrideResponse contracts
  - OverrideArtifact persistence with time bounds and JSONB affected_surfaces
  - override_api.override_created structured log signal
key_files:
  - src/sps/api/contracts/overrides.py
  - src/sps/api/routes/overrides.py
  - tests/m012_s01_override_api_test.py
key_decisions:
  - Override API follows emergency API pattern with RBAC router-level dependency and per-endpoint identity injection
  - ULID-based ID generation pattern (OVR-<ULID>) consistent with EMERG-<ULID> and evidence artifact patterns
patterns_established:
  - Override artifact creation API mirrors emergency artifact creation pattern from T02
  - Router-level RBAC dependency ensures all routes require escalation-owner role
observability_surfaces:
  - override_api.override_created (INFO, fields: override_id, scope, expires_at, affected_surfaces)
  - override_api.override_creation_failed (WARNING, fields: case_id, reason=persistence_error)
  - HTTP 401 on missing JWT (auth_required)
  - HTTP 403 on wrong role (role_denied, required_roles includes escalation-owner)
duration: 45m
verification_result: passed
completed_at: 2026-03-16T20:53:00-07:00
blocker_discovered: false
---

# T03: POST /api/v1/overrides endpoint with scope validation

**Created POST /api/v1/overrides endpoint gated by escalation-owner RBAC role with time-bounded OverrideArtifact persistence and JSONB affected_surfaces storage.**

## What Happened

Implemented the override artifact creation API following the established pattern from T02 (emergency API):

1. Created `src/sps/api/contracts/overrides.py` with CreateOverrideRequest (case_id, scope, justification, duration_hours, affected_surfaces) and OverrideResponse (override_id, expires_at, affected_surfaces, etc.)
2. Created `src/sps/api/routes/overrides.py` with POST / endpoint requiring escalation-owner role via `require_roles()` dependency
3. Implemented endpoint logic: compute start_at = now(), expires_at = start_at + duration_hours; generate override_id = f"OVR-{ulid.new().str}"; persist OverrideArtifact row (approver_id from JWT claims, cleanup_required=True); emit log override_api.override_created (INFO); return 201 + OverrideResponse
4. Registered overrides router in `src/sps/api/main.py` with prefix "/api/v1/overrides"
5. Wrote integration test `tests/m012_s01_override_api_test.py` proving RBAC enforcement, JSONB persistence, and structured logging

Fixed deprecation warning in contracts by changing `Field(min_items=1)` to `Field(min_length=1)` for affected_surfaces list validation.

## Verification

**Integration tests passed:**
```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 uv run pytest tests/m012_s01_override_api_test.py -v
# 3 passed: create_override_success, create_override_no_jwt, create_override_wrong_role
```

**cURL endpoint test:**
```bash
curl -X POST http://localhost:8000/api/v1/overrides/ \
  -H "Authorization: Bearer <escalation-owner-jwt>" \
  -d '{"case_id":"CASE-CURL-001","scope":"reviewer_independence","justification":"Emergency bypass","duration_hours":2,"affected_surfaces":["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]}'
# → 201 + {"override_id":"OVR-01KKWVC19QTEFKPB09ET628JH7", ...}
```

**Database persistence:**
```bash
docker compose exec postgres psql -U sps -d sps -c \
  "SELECT override_id, affected_surfaces::text FROM override_artifacts ORDER BY created_at DESC LIMIT 3;"
# → Shows override_id OVR-01KKWVC19QTEFKPB09ET628JH7 with JSONB affected_surfaces ["REVIEW_PENDING->APPROVED_FOR_SUBMISSION"]
```

**Structured logs:**
```
2026-03-16 20:53:01,659 INFO sps.api.routes.overrides override_api.override_created override_id=OVR-01KKWVC19QTEFKPB09ET628JH7 scope=reviewer_independence expires_at=2026-03-17T04:53:01.623460+00:00 affected_surfaces=['REVIEW_PENDING->APPROVED_FOR_SUBMISSION']
```

## Diagnostics

**Query active/expired overrides:**
```bash
docker compose exec postgres psql -U sps -d sps -c \
  "SELECT override_id, case_id, expires_at, expires_at > NOW() as active FROM override_artifacts ORDER BY created_at DESC LIMIT 5"
```

**Check override persistence:**
```bash
docker compose exec postgres psql -U sps -d sps -c \
  "SELECT override_id, affected_surfaces FROM override_artifacts WHERE case_id = 'CASE-XXX'"
```

**Structured log signals:**
- `override_api.override_created` — fires on successful override creation (INFO level)
- `override_api.override_creation_failed` — fires on persistence error (WARNING level)

**Error responses:**
- 401 response includes `{"error": "auth_required", "auth_reason": "missing_or_invalid_authorization"}`
- 403 response includes `{"error_code": "role_denied", "required_roles": ["escalation-owner"]}`
- 409 response includes `{"error": "OVERRIDE_CONFLICT", "override_id": "..."}`

## Deviations

None. Task plan was followed exactly as specified.

## Known Issues

None.

## Files Created/Modified

- `src/sps/api/contracts/overrides.py` — CreateOverrideRequest and OverrideResponse Pydantic contracts
- `src/sps/api/routes/overrides.py` — POST /api/v1/overrides endpoint with escalation-owner RBAC enforcement
- `src/sps/api/main.py` — registered overrides router with prefix "/api/v1/overrides"
- `tests/m012_s01_override_api_test.py` — integration tests for override API (RBAC, persistence, JSONB validation)
