# Requirements: SPS V2 Reliability Hardening

**Defined:** 2026-03-17
**Core Value:** Permit case releases and manifests are accurate, verifiable, and secure end to end.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Workflow

- [ ] **FLOW-01**: User can submit a case through staged workflow approvals
- [ ] **FLOW-02**: Workflow advances to `DOCUMENT_COMPLETE` when required evidence is registered
- [ ] **FLOW-03**: Workflow transition rules are modularized and unit-tested per state action
- [ ] **FLOW-04**: Override/contradiction checks are enforced and regression-tested

### Evidence & Audit

- [ ] **EVID-01**: User can attach evidence/documents to a case with an audit trail
- [ ] **EVID-02**: Evidence registry readback is verified and recorded for each document package
- [ ] **EVID-03**: Evidence is bound to workflow steps with signed attestations

### Release Bundles

- [ ] **BNDL-01**: Release bundle build fails with explicit errors for missing artifact paths
- [ ] **BNDL-02**: Release bundle build fails with explicit errors for missing artifact identifiers
- [ ] **BNDL-03**: Manifest retrieval returns the persisted manifest from the source of truth
- [ ] **BNDL-04**: Manifest retrieval verifies digest and mediaType before response

### Security

- [ ] **SECR-01**: Reviewer access requires JWT + mTLS; legacy API key access is removed or strictly scoped

### Performance

- [ ] **PERF-01**: Case list endpoints provide pagination with default limits and ordering
- [ ] **PERF-02**: Review list endpoints provide pagination with default limits and ordering

### Testing & Reliability

- [ ] **TEST-01**: Document package workflow integration tests validate `DOCUMENT_COMPLETE` progression
- [ ] **TEST-02**: Evidence registry readback tests are enabled and passing

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Governance & Insights

- **GOV-01**: Transparency-log publishing for manifests and attestations
- **GOV-02**: Cross-case analytics and operational optimization dashboards
- **GOV-03**: Policy-as-code gating for release approvals beyond baseline verification

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New end-user product features | Stabilization and correctness first |
| UI/UX redesigns | Backend reliability focus |
| Platform re-architecture | Keep existing stack and contracts |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FLOW-01 | Phase 2 | Pending |
| FLOW-02 | Phase 2 | Pending |
| FLOW-03 | Phase 2 | Pending |
| FLOW-04 | Phase 2 | Pending |
| EVID-01 | Phase 2 | Pending |
| EVID-02 | Phase 2 | Pending |
| EVID-03 | Phase 2 | Pending |
| BNDL-01 | Phase 1 | Pending |
| BNDL-02 | Phase 1 | Pending |
| BNDL-03 | Phase 1 | Pending |
| BNDL-04 | Phase 1 | Pending |
| SECR-01 | Phase 3 | Pending |
| PERF-01 | Phase 3 | Pending |
| PERF-02 | Phase 3 | Pending |
| TEST-01 | Phase 2 | Pending |
| TEST-02 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after initial definition*
