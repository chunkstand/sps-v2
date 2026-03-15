# Requirements

## Active

### R004 — Temporal harness runs PermitCaseWorkflow with replay-safe semantics
- Class: core-capability
- Status: active
- Description: Temporal worker can run a PermitCaseWorkflow (minimal end-to-end flow with stubbed activities) and is replay-safe and idempotent.
- Why it matters: Temporal is the authoritative harness; without a working workflow substrate, reviewer gates and authority controls can’t be enforced or audited.
- Source: spec (runtime-implementation-profile.md; tasks D-001–D-004)
- Primary owning slice: M002/S01
- Supporting slices: M002/S02
- Validation: mapped
- Notes: Prove at least one representative path + replay test before expanding to full domain tasks.

### R005 — State transition guard enforces protected transitions and emits denials
- Class: compliance/security
- Status: active
- Description: All authoritative PermitCase state mutations are mediated by a state transition guard enforcing the transition table + guard assertions + relevant invariants; denials include guard/invariant identifiers.
- Why it matters: Prevents authority drift and direct specialist mutation; provides the core governance enforcement point.
- Source: spec (sections 9, 13, 20A; invariants/guard-assertions; tasks C-002–C-004)
- Primary owning slice: M002/S02
- Supporting slices: M002/S03
- Validation: mapped
- Notes: Early proof should include denial of `REVIEW_PENDING -> APPROVED_FOR_SUBMISSION` without ReviewDecision.

## Validated

### R001 — Authoritative Postgres schema for core SPS entities
- Class: core-capability
- Status: validated
- Description: Postgres schema + migrations exist for PermitCase, Project, review records, contradiction records, transition ledger, and evidence metadata.
- Why it matters: Everything else (Temporal workflows, reviewer gates, release controls) depends on authoritative state being durable and queryable.
- Source: inferred (spec Phase 1 / tasks B-001)
- Primary owning slice: M001/S01
- Supporting slices: M001/S02, M001/S03
- Validation: proved (alembic upgrade + Postgres-backed integration tests)
- Notes: Schema is intentionally thin in some places (string enums, JSONB payloads) in Phase 1; tighten with constraints as guarded workflows land.

### R002 — Evidence registry with stable IDs and object storage binding
- Class: integration
- Status: validated
- Description: Evidence artifacts can be registered, stored, and retrieved by stable ID; content lives in S3-compatible storage and is correlated to metadata in Postgres.
- Why it matters: Review, audit, and release gates are evidence-driven; evidence must be queryable and durable.
- Source: inferred (spec tasks B-002, F-010, INV-SPS-EVID-001)
- Primary owning slice: M001/S02
- Supporting slices: M001/S03
- Validation: proved (MinIO-backed adapter tests + end-to-end roundtrip)
- Notes: Retrieval SLA enforcement is later; Phase 1 focuses on correctness and stable identifiers.

### R003 — Legal hold prevents purge or destructive delete of bound evidence (INV-004)
- Class: compliance/security
- Status: validated
- Description: Any purge/destructive delete of evidence is denied while a legal hold is active.
- Why it matters: Tier 3 compliance; audit reconstruction depends on evidence preservation.
- Source: spec (INV-004; SEC-004; runbook legal-hold.md)
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: proved (hold bindings + INV-004 guard + denial + purge exclusion tests)
- Notes: Phase 1 proves fail-closed denial semantics; destructive purge remains disabled.

## Deferred

(none)

## Out of Scope

### R900 — Payment processing
- Class: anti-feature
- Status: out-of-scope
- Description: SPS does not process permit fee payments in v1.
- Why it matters: Prevents scope creep and regulatory expansion; explicitly excluded in spec.
- Source: spec (Section 2.6; clarifications C-010B)
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: Any change requires new intent + major spec revision.

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| R001 | core-capability | validated | M001/S01 | M001/S02,M001/S03 | proved (alembic + pytest) |
| R002 | integration | validated | M001/S02 | M001/S03 | proved (minio + e2e pytest) |
| R003 | compliance/security | validated | M001/S03 | none | proved (deny + purge tests) |
| R004 | core-capability | active | M002/S01 | M002/S02 | mapped |
| R005 | compliance/security | active | M002/S02 | M002/S03 | mapped |
| R900 | anti-feature | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 2
- Mapped to slices: 5
- Validated: 3
- Unmapped active requirements: 0
