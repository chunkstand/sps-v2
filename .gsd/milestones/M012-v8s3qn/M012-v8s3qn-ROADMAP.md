# M012-v8s3qn: Phase 12 — emergency and override governance

**Vision:** Implement GOV-005 emergency declaration and override workflows with time-bounded artifacts, enforced in workflow/guard paths, enabling bounded exception handling without silent authority drift.

## Success Criteria

- Emergency can be declared with bounded scope and duration; PermitCase enters EMERGENCY_HOLD or uses override mode with durable artifacts
- Overrides are time-bounded; expiration is enforced and transitions are denied when override is missing or expired
- Workflow and guard behavior reflects declared emergency/override state without silent state mutation
- Emergency/override use is auditable via Postgres artifacts and transition ledger denials

## Key Risks / Unknowns

- **Guard enforcement integrity** — guards must fail closed when override is missing, expired, or out-of-scope; any silent bypass creates authority drift
- **Time-bound enforcement semantics** — must prove that expired overrides actually deny transitions in real workflow execution, not just in isolated tests

## Proof Strategy

- Guard enforcement integrity → retire in S01 by proving override guard denies transitions without valid override, allows with active override, denies with expired override (integration tests + docker-compose runbook)
- Time-bound enforcement semantics → retire in S01 by proving end-to-end lifecycle: declare emergency → attempt protected transition with override → expire override → transition denial (live docker-compose runbook)

## Verification Classes

- Contract verification: pytest integration tests for override artifact persistence, guard enforcement logic, EMERGENCY_HOLD transitions
- Integration verification: Temporal + Postgres integration proving override validation in apply_state_transition activity
- Operational verification: docker-compose runbook exercising full lifecycle (declare emergency → create override → protected transition → expiration → denial → cleanup)
- UAT / human verification: none

## Milestone Definition of Done

This milestone is complete only when all are true:

- S01 slice deliverables are complete (ORM models, migrations, API endpoints, guard enforcement, workflow transitions, integration tests, runbook)
- Emergency/override artifacts are wired into apply_state_transition guard validation
- EMERGENCY_HOLD state entry/exit transitions are proven via docker-compose
- Success criteria are re-checked against live docker-compose runbook behavior
- R034 is validated with integration tests + runbook proof

## Requirement Coverage

- Covers: R034 (Emergency and override workflows)
- Partially covers: none
- Leaves for later: R035 (Admin policy/config governance — deferred to M013)
- Orphan risks: none

## Slices

- [ ] **S01: Emergency/override artifacts + guard enforcement + lifecycle proof** `risk:high` `depends:[]`
  > After this: Emergency can be declared via API, overrides can be created with time bounds, protected transitions are denied without valid override and allowed with active override, expired overrides deny transitions, EMERGENCY_HOLD entry/exit proven via docker-compose, full lifecycle runbook exercises declare → bypass → expire → cleanup with real API + worker + Postgres

<!--
  Format rules (parsers depend on this exact structure):
  - Checkbox line: - [ ] **S01: Title** `risk:high|medium|low` `depends:[S01,S02]`
  - Demo line:     >  After this: one sentence showing what's demoable
  - Mark done:     change [ ] to [x]
  - Order slices by risk (highest first)
  - Each slice must be a vertical, demoable increment — not a layer
  - If all slices are completed exactly as written, the milestone's promised outcome should actually work at the stated proof level
  - depends:[X,Y] means X and Y must be done before this slice starts

  Planning quality rules:
  - Every slice must ship real, working, demoable code — no research-only or foundation-only slices
  - Early slices should prove the hardest thing works by building through the uncertain path
  - Each slice should establish a stable surface that downstream slices can depend on
  - Demo lines should describe concrete, verifiable evidence — not vague claims
  - In brownfield projects, ground slices in existing modules and patterns
  - If a slice doesn't produce something testable end-to-end, it's probably a layer — restructure it
  - If the milestone crosses multiple runtime boundaries (for example daemon + API + UI, bot + subprocess + service manager, or extension + RPC + filesystem), include an explicit final integration slice that proves the assembled system works end-to-end in a real environment
  - Contract or fixture proof does not replace final assembly proof when the user-visible outcome depends on live wiring
  - Each "After this" line must be truthful about proof level: if only fixtures or tests prove it, say so; do not imply the user can already perform the live end-to-end behavior unless that has actually been exercised
-->

## Boundary Map

### S01 (single slice milestone)

Produces:
- `EmergencyRecord` ORM model with `emergency_id, incident_id, scope, declared_by, started_at, expires_at, allowed_bypasses, forbidden_bypasses, cleanup_due_at` fields
- `OverrideArtifact` ORM model with `override_id, scope, justification, start_at, expires_at, affected_surfaces, approver_id, cleanup_required` fields
- Alembic migration creating `emergency_records` and `override_artifacts` tables with FK constraints to `permit_cases`
- `POST /api/v1/emergencies` endpoint (escalation-owner role RBAC) for declaring emergencies
- `POST /api/v1/overrides` endpoint (escalation-owner role RBAC) for creating override artifacts
- Override guard in `apply_state_transition` activity validating `StateTransitionRequest.override_id` existence, time bounds (`expires_at > NOW()`), and scope (`affected_surfaces` includes transition)
- EMERGENCY_HOLD state transitions: REVIEW_PENDING → EMERGENCY_HOLD (emergency declaration), EMERGENCY_HOLD → REVIEW_PENDING (cleanup with reviewer confirmation)
- Guard assertion `INV-SPS-EMERG-001` enforcement in transition ledger denials with `OVERRIDE_DENIED` event type
- Integration tests: override guard (deny without override, allow with valid override, deny with expired override)
- Integration tests: EMERGENCY_HOLD entry/exit transitions
- Docker-compose runbook `scripts/verify_m012_s01.sh`: declare emergency → create override → protected transition success → expire override → transition denial → cleanup exit

Consumes:
- Existing `StateTransitionRequest.override_id: str | None` field (src/sps/workflows/permit_case/contracts.py)
- Existing `CaseState.EMERGENCY_HOLD` enum value (src/sps/workflows/permit_case/contracts.py)
- Existing `ArtifactClass.OVERRIDE_RECORD` enum value (src/sps/evidence/models.py)
- Existing guard assertion `INV-SPS-EMERG-001` (invariants/sps/guard-assertions.yaml)
- Contradiction blocking guard template pattern (src/sps/workflows/permit_case/activities.py lines 983-1001)
- RBAC escalation-owner role pattern (Phase 10 M010/S01)
- Idempotent artifact persistence pattern (Phase 11 M011/S01)
