---
artifact_id: ART-SPS-PLAN-001
authoritative_or_informative: authoritative_build_plan
authored_or_generated: authored
consumer_list:
- engineering
- operations
- security
- reviewers
- release_managers
owner: Engineering Lead
freshness_expectation: update when work breakdown or gating changes
failure_if_missing: operator_execution_degraded
---


# SPS implementation plan

This plan decomposes the BUILD_APPROVED SPS package into implementation phases. It does not change the spec. It sequences build work, verification, and release-readiness evidence.

## Phase 0 — package wiring and source-of-truth setup

### Objective
Materialize the canonical package into the repository and make binding artifacts discoverable.

### Deliverables
- canonical repository layout present
- spec and runtime profile checked in
- model export and contract schema directories created
- invariant index, traceability export, diagrams, runbooks, and release template locations wired
- merge authorization workflow scaffolded

### Exit criteria
- repository paths match `spec.md` section 30
- spec validation and schema lint pass
- all binding artifact paths resolve
- no unresolved package-shape gaps remain

## Phase 1 — authority model and data foundations

### Objective
Implement authoritative stores, keys, state model, and evidence registry before workflow logic.

### Deliverables
- Postgres schema for PermitCase, Project, review records, contradiction records, transition ledger
- object storage layout for evidence and release artifacts
- evidence registry API with stable IDs
- model-derived enum and validation package
- typed schemas enforced at trust boundaries

### Exit criteria
- all mandatory model objects exist in code
- evidence retrieval by stable ID works for seeded test fixtures
- authoritative vs non-authoritative write paths are mechanically separated
- invariant hooks exist for INV-001 through INV-008

## Phase 2 — durable workflow harness

### Objective
Bind the logical SPS model to Temporal and guarded mutation paths.

### Deliverables
- PermitCaseWorkflow
- child workflows and activities for intake, jurisdiction, research, compliance, incentives, documents, submission, tracking, comment resolution, evidence assembly
- state transition guard service
- retry classification and idempotency keys
- workflow replay testing harness

### Exit criteria
- no specialist worker can advance case state directly
- protected transitions fail closed when review, evidence, contradiction, or freshness checks fail
- workflow replay and compensation tests pass
- denial audit events are emitted for all guard denials

## Phase 3 — reviewer service and governance controls

### Objective
Implement the human gate, independence checks, dissent handling, overrides, and contradiction workflows.

### Deliverables
- reviewer UI and API
- review artifact generation
- reviewer independence metrics computation
- dissent and override artifact support
- contradiction queue and reviewer resolution flow

### Exit criteria
- reviewer can ACCEPT, ACCEPT_WITH_DISSENT, or BLOCK
- self-approval on high-risk surfaces is denied absent explicit override
- same-rank contradictions block advancement
- dissent on high-risk surfaces tightens release

## Phase 4 — domain execution services

### Objective
Implement domain-specific worker services and evidence-backed outputs.

### Deliverables
- intake normalization service
- jurisdiction resolution service
- research and source ranking service
- compliance evaluation service
- incentive assessment service
- document generation and package sealing service

### Exit criteria
- each specialist emits typed outputs plus evidence references
- freshness and source-ranking rules are enforced
- package sealing produces manifest and artifact digests
- reviewed upstream outputs are required before downstream protected actions

## Phase 5 — submission, tracking, and manual fallback

### Objective
Implement external adapters, status normalization, and bounded unsupported-case behavior.

### Deliverables
- submission adapter(s) with idempotency protection
- receipt persistence and proof verification
- external status normalization maps
- manual fallback package generation
- manual fallback proof bundle validation path

### Exit criteria
- no SUBMITTED state without verified receipt or reviewer-validated proof bundle
- unsupported workflows enter MANUAL_SUBMISSION_REQUIRED
- UNKNOWN_EXTERNAL_STATUS and CONTRADICTORY_EXTERNAL_STATUS fail closed
- approval-reported statuses do not auto-advance without required proof

## Phase 6 — observability, runbooks, release gates, and rollback

### Objective
Close operator and release-bearing obligations.

### Deliverables
- dashboards and alerts
- incident linkage integration
- release bundle generator
- rollback artifact generation and rehearsal evidence capture
- post-release validation workflow
- emergency path timers and cleanup tracking

### Exit criteria
- evidence retrieval SLA monitors exist
- release prerequisites are machine-checkable
- rollback rehearsal evidence exists for critical paths
- emergency cleanup and redesign-review triggers are enforced

## Phase 7 — conformance hardening and release readiness

### Objective
Prove the implementation conforms to the BUILD_APPROVED package.

### Deliverables
- traceability export with zero blocker gaps
- control-failure and negative-path tests
- release candidate manifest
- reviewer independence metrics export
- post-release validation template populated for staging and canary
- conformance dossier

### Exit criteria
- CI and merge authorization pass
- release bundle is complete
- no unresolved blocker contradiction or unresolved high-risk dissent
- no unresolved spec-authority mismatch on release-relevant paths

## Sequencing rules

- Phase 1 must finish before Phase 2 protected transitions are considered conformant.
- Phase 2 guard services must exist before Phase 5 external submission is enabled.
- Phase 3 reviewer service must exist before production-authoritative submission is enabled.
- Phase 6 rollback and emergency artifacts must exist before canary rollout.
- Phase 7 evidence must be regenerated for each release candidate.

## Evidence required per phase

| Phase | Required evidence |
| --- | --- |
| 0 | repo tree, artifact path checks, spec validation output |
| 1 | schema migration proof, evidence retrieval tests, authority boundary negative tests |
| 2 | replay tests, guard denial events, protected-transition test results |
| 3 | review artifact fixtures, independence metrics export, dissent resolution tests |
| 4 | source freshness tests, contradiction tests, package digest tests |
| 5 | idempotency tests, manual fallback proof sufficiency tests, external status normalization tests |
| 6 | dashboard screenshots or config exports, alert drills, rollback rehearsal evidence |
| 7 | traceability export, release manifest, post-release validation plan, conformance report |
