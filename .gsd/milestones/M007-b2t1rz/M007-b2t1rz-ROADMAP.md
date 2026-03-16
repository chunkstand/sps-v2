# M007-b2t1rz: Phase 7 — submission, tracking, and manual fallback

**Vision:** Permit cases can be submitted through a deterministic adapter that persists receipts, normalized tracking events are recorded, and unsupported portals route to a governed manual fallback path.

## Success Criteria
- A PermitCaseWorkflow run creates a SubmissionAttempt with a persisted receipt EvidenceArtifact and advances to SUBMITTED (or MANUAL_SUBMISSION_REQUIRED for unsupported portals).
- External status inputs are normalized via fixture maps and persisted as ExternalStatusEvent records with fail-closed behavior on unknown statuses.
- Proof bundle validation + reviewer confirmation are enforced before submission is marked complete.
- A docker-compose runbook proves submission + tracking persistence across Postgres/Temporal/MinIO with real API/worker entrypoints.

## Key Risks / Unknowns
- Idempotent submission adapter behavior under Temporal retry must not double-submit or duplicate receipts.
- Fixture status maps may be incomplete; unmapped statuses must fail closed without silently mutating workflow state.
- Manual fallback packages must be generated deterministically without bypassing proof bundle validation.

## Proof Strategy
- Idempotent submission + receipt persistence → retire in S01 by proving retry-safe SubmissionAttempt + receipt evidence persistence via integration tests.
- Status normalization fail-closed behavior → retire in S02 by proving unknown statuses raise/deny and known statuses persist as ExternalStatusEvent.
- Cross-boundary wiring → retire in S03 by proving docker-compose runbook reaches SUBMITTED or MANUAL_SUBMISSION_REQUIRED with stored receipts + status events.

## Verification Classes
- Contract verification: pytest integration tests for submission attempt idempotency, receipt evidence persistence, proof bundle validation, and status normalization fixtures.
- Integration verification: Temporal workflow + Postgres + MinIO exercised through activities and API entrypoints.
- Operational verification: docker-compose runbook script that drives intake → submission → status ingest and inspects Postgres/MinIO.
- UAT / human verification: none.

## Milestone Definition of Done
This milestone is complete only when all are true:
- All slices are complete and their demo criteria hold.
- Submission, tracking, and manual fallback paths are wired through PermitCaseWorkflow and activities with evidence persistence.
- The real API + worker entrypoints execute a full submission attempt path in docker-compose.
- Success criteria are re-checked against live behavior (not just fixtures).
- Final integrated acceptance scenarios pass for both supported and unsupported portal cases.

## Requirement Coverage
- Covers: R016, R017, R018, R019
- Partially covers: none
- Leaves for later: R020, R021, R022, R023, R024, R025, R026, R027, R028, R029, R031, R032, R033, R034, R035
- Orphan risks: none

## Slices
- [x] **S01: Deterministic submission attempt + receipt + manual fallback** `risk:high` `depends:[]`
  > After this: a workflow run can create a SubmissionAttempt with receipt evidence or generate a ManualFallbackPackage, and proof bundle confirmation is enforced (verified by integration tests and API reads).
- [x] **S02: Status normalization + tracking events** `risk:medium` `depends:[S01]`
  > After this: external status inputs are normalized via fixtures and persisted as ExternalStatusEvent records, with fail-closed behavior for unknown statuses (verified by tests and API reads).
- [ ] **S03: Live submission + tracking runbook** `risk:low` `depends:[S01,S02]`
  > After this: a docker-compose runbook exercises intake → submission → status ingest with receipts in MinIO and tracking events in Postgres using the real API + worker entrypoints.

## Boundary Map
### S01 → S02
Produces:
- SubmissionAttempt, ManualFallbackPackage models + migrations with receipt EvidenceArtifact linkage.
- Deterministic submission adapter activity (idempotent) and proof bundle confirmation/validation logic.
- Workflow transitions to SUBMISSION_PENDING → SUBMITTED or MANUAL_SUBMISSION_REQUIRED with ledger entries.
- API read surfaces for submission attempts, receipts, and manual fallback package inspection.

Consumes:
- nothing (first slice)

### S02 → S03
Produces:
- Phase 7 status map fixtures + loader module.
- ExternalStatusEvent model + persistence activity with fail-closed normalization.
- API endpoint(s) for ingesting and reading normalized status events.

Consumes:
- SubmissionAttempt + manual fallback persistence and workflow wiring from S01.

### S01 → S03
Produces:
- Stable submission adapter contract + receipt evidence storage semantics.
- Proof bundle confirmation gate used by the workflow before submission completion.

Consumes:
- nothing (first slice)
