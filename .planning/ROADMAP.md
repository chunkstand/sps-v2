# Roadmap: SPS V2 Reliability Hardening

## Phases
- [ ] **Phase 1: Bundle Integrity** - Release bundles and manifests are validated, persisted, and verified.
- [ ] **Phase 2: Workflow Evidence Reliability** - Case workflows advance with evidence-bound steps and reliable transition rules.
- [ ] **Phase 3: Access & Pagination Hardening** - Reviewer access is secured and list endpoints are bounded and ordered.

## Phase Details

### Phase 1: Bundle Integrity
**Goal**: Release bundles and manifest retrieval are correct, verifiable, and fail fast on missing inputs.
**Depends on**: Nothing (first phase)
**Requirements**: BNDL-01, BNDL-02, BNDL-03, BNDL-04
**Success Criteria** (what must be TRUE):
  1. Release bundle builds fail with explicit, user-visible errors when artifact paths are missing.
  2. Release bundle builds fail with explicit, user-visible errors when artifact identifiers are missing.
  3. Manifest retrieval returns the persisted manifest and verifies digest and mediaType before responding.
**Plans**: TBD

### Phase 2: Workflow Evidence Reliability
**Goal**: Users can move permit cases through approvals with evidence bound to workflow steps and transitions that are reliable.
**Depends on**: Phase 1
**Requirements**: FLOW-01, FLOW-02, FLOW-03, FLOW-04, EVID-01, EVID-02, EVID-03, TEST-01, TEST-02
**Success Criteria** (what must be TRUE):
  1. A user can submit a case and progress it through the staged approval workflow without manual overrides.
  2. Workflow reaches `DOCUMENT_COMPLETE` only after required evidence is registered and readback is recorded.
  3. Users can attach evidence with an audit trail, and evidence is bound to workflow steps with signed attestations.
  4. QA can run document package workflow tests and evidence readback tests and see them pass.
**Plans**: TBD

### Phase 3: Access & Pagination Hardening
**Goal**: Reviewer access is secure and list endpoints are safe and predictable at scale.
**Depends on**: Phase 2
**Requirements**: SECR-01, PERF-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. Reviewer access requires JWT + mTLS and legacy API key access is blocked or strictly scoped.
  2. Case and review list endpoints enforce pagination with default limits and deterministic ordering.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bundle Integrity | 0/0 | Not started | - |
| 2. Workflow Evidence Reliability | 0/0 | Not started | - |
| 3. Access & Pagination Hardening | 0/0 | Not started | - |
