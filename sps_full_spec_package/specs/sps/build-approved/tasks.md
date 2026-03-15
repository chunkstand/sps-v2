---
artifact_id: ART-SPS-TASKS-001
authoritative_or_informative: authoritative_execution_backlog
authored_or_generated: authored
consumer_list:
- engineering
- ops
- security
- reviewers
owner: Engineering Lead
freshness_expectation: update with implementation status
failure_if_missing: operator_execution_degraded
---


# SPS build tasks

## Workstream A — repository and package wiring

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| A-001 | Create canonical repo layout from section 30 | Platform | spec.md | repo tree | VAL-001 | all canonical paths exist |
| A-002 | Check in materialized spec and runtime profile | Architecture | source uploads | spec docs | GOV-001 | docs versioned and discoverable |
| A-003 | Add schema lint and markdown validation | Platform | contracts, docs | CI step | VAL-001, REL-001 | CI blocks invalid artifacts |
| A-004 | Add artifact freshness checks for generated binding artifacts | Platform | lineage, traceability | CI step | REL-001 | stale generated artifacts fail |

## Workstream B — authoritative data and evidence

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| B-001 | Implement PermitCase, Project, review, contradiction, transition ledger tables | Platform | model.yaml | DB schema | F-001, GOV-001 | migrations applied and tested |
| B-002 | Implement evidence registry API with stable IDs | Platform | spec sections 10.4, 23 | service/API | F-010, CTL-10A | evidence resolves by stable ID |
| B-003 | Implement legal-hold-aware evidence retention controls | Compliance/Platform | SEC-004, INV-004 | storage policy | SEC-004 | purge denied under legal hold |
| B-004 | Persist release applicability and artifact metadata | Platform | 10A artifact matrix | metadata service | REL-001 | release gate can query current artifacts |

## Workstream C — model, schemas, and guards

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Implement model-derived enums and object validators | Platform | model.yaml | validation package | VAL-001 | runtime uses typed validation |
| C-001A | Add state transition payload schema and guard-boundary validation | Platform | state model, runtime profile | transition contract | VAL-001, VAL-002 | guarded mutation requests validate before execution |
| C-002 | Implement state transition guard service | Platform | sections 8, 9, 20A | guarded endpoint/service | GOV-001, CTL-01A, CTL-01B | direct unguarded mutation impossible |
| C-003 | Implement invariant checks INV-001 through INV-008 | Platform | invariants index | runtime guards | VAL-002 | all invariant tests pass |
| C-004 | Emit denial audit events for every failed protected transition | Platform/Ops | 20A matrix | audit events | OBS-001 | denial events queryable |

## Workstream D — Temporal harness and worker services

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| D-001 | Implement PermitCaseWorkflow top-level flow | Workflow team | runtime profile | Temporal workflow | F-001–F-010 | happy path runs end to end |
| D-002 | Implement child workflows and typed activities | Workflow team | runtime profile | worker services | F-002–F-009 | each activity uses typed contracts |
| D-003 | Add retry classes and replay-safe side-effect guards | Workflow team | section 13, runtime profile | retry config | VAL-002 | replay and retry tests pass |
| D-004 | Add safe-stop routing for unsupported, stale, blocked, contradictory cases | Workflow team | sections 13, 18, 18A, 28 | workflow branches | GOV-006, REL-001 | fail-closed paths covered |

## Workstream E — reviewer, dissent, override, and contradiction control

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| E-001 | Build reviewer queue, evidence view, and decision capture | App team | review contract | reviewer UI/API | GOV-002, F-006 | reviewer can decide guarded objects |
| E-002 | Enforce reviewer independence thresholds | Governance/App | section 17 | policy checks | GOV-003, CTL-11A | threshold breaches block as specified |
| E-003 | Implement dissent artifacts and second-review/escalation rules | Governance/App | section 17.6 | dissent flow | GOV-004, CTL-12 | unresolved high-risk dissent release-blocks |
| E-004 | Implement contradiction artifacts and reviewer resolution | Compliance/App | section 18 | contradiction flow | GOV-006, CTL-14A | same-rank contradiction blocks advance |

## Workstream F — research, compliance, incentive, and document generation

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| F-001 | Normalize intake into Project | Intake team | intake payloads | Project | F-001 | acceptance tests pass |
| F-002 | Resolve jurisdiction stack and support level | Research/Geo | Project | JurisdictionResolution | F-002 | authority stack complete |
| F-003 | Retrieve authoritative requirements with provenance and freshness | Research | jurisdiction data | RequirementSet | F-003, CTL-03A | freshness and contradiction tests pass |
| F-004 | Evaluate compliance rules and blockers | Compliance | Project, RequirementSet | ComplianceEvaluation | F-004 | stale rules block advance |
| F-005 | Assess incentives as evidence-backed advisory outputs | Incentives | Project, sources | IncentiveAssessment | F-004 | official sources outrank aggregators |
| F-006 | Generate submission package, documents, manifest, digests | Document service | reviewed outputs | SubmissionPackage | F-005, CTL-05A | package sealing tests pass |

## Workstream G — submission, tracking, and manual fallback

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| G-001 | Implement idempotent submission adapters | Integration team | SubmissionPackage | SubmissionAttempt | F-006, CTL-06A | duplicate side effects prevented |
| G-002 | Persist receipts and correlate tracking IDs | Integration team | adapter responses | receipt artifacts | F-007 | receipts queryable |
| G-003 | Implement status mapping files and normalization | Tracking team | adapter families | ExternalStatusEvent | F-007, CTL-07A, CTL-07B | unmapped statuses fail closed |
| G-004 | Implement manual fallback package generation | Integration/Ops | unsupported cases | ManualFallbackPackage | F-008, section 28.1 | unsupported path bounded |
| G-005 | Implement proof bundle validation and reviewer confirmation | Integration/App | proof artifacts | validated bundle | CTL-06A | no SUBMITTED without proof |

## Workstream H — observability, CI, release, and rollback

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| H-001 | Implement audit event schema and sinks | Ops/Platform | section 23 | structured audit logs | OBS-001 | required fields present |
| H-002 | Configure dashboards and alerts | Ops | section 23 | observability config | OBS-002, OBS-003 | alert drills pass |
| H-003 | Implement merge authorization artifact | Platform | section 25 | CI artifact | REL-001 | merge authorization issued only on pass |
| H-004 | Implement release bundle manifest generation | Release | section 10A, 26 | manifest.yaml | REL-001, REL-002 | digest and compatibility checks pass |
| H-005 | Implement rollback artifact, rehearsal capture, and verification | Release/Ops | section 26, 28.5 | rollback.yaml, evidence | REL-002 | rehearsal evidence current |
| H-006 | Implement post-release validation workflow | Release/Ops | section 26 | post-release-validation.yaml | REL-003 | next stage blocked until report complete |

## Workstream I — security and authority boundaries

| Task ID | Task | Primary owner | Inputs | Outputs | Linked requirements/controls | Done when |
| --- | --- | --- | --- | --- | --- | --- |
| I-001 | Enforce authenticated identities on interactive and service APIs | Security | SEC-001 | auth layer | SEC-001 | auth integration tests pass |
| I-002 | Implement RBAC separation for user, reviewer, operator, admin, release-manager, escalation-owner | Security | roles table | RBAC policy | SEC-002 | cross-role denial tests pass |
| I-003 | Enforce mTLS and signed service principals | Security | SEC-005 | network/auth config | SEC-005 | service auth verified |
| I-004 | Redact sensitive fields from logs and lower-trust views | Security/Ops | SEC-003 | redaction policy | SEC-003 | log inspection tests pass |
| I-005 | Ensure observability is read-only to authoritative surfaces | Security/Ops | section 14 | network policy | OBS-004, INV-005 | mutation attempts denied |

## Exit bundle for BUILD_CONFORMANT implementation

All of the following must exist before production release:
- current model export
- current contracts
- current invariants index
- current traceability export
- reviewer metrics export
- release bundle manifest
- rollback rehearsal evidence
- runbook updates
- post-release validation template and stage-gated execution
