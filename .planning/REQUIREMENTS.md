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
| FLOW-01 | TBD | Pending |
| FLOW-02 | TBD | Pending |
| FLOW-03 | TBD | Pending |
| FLOW-04 | TBD | Pending |
| EVID-01 | TBD | Pending |
| EVID-02 | TBD | Pending |
| EVID-03 | TBD | Pending |
| BNDL-01 | TBD | Pending |
| BNDL-02 | TBD | Pending |
| BNDL-03 | TBD | Pending |
| BNDL-04 | TBD | Pending |
| SECR-01 | TBD | Pending |
| PERF-01 | TBD | Pending |
| PERF-02 | TBD | Pending |
| TEST-01 | TBD | Pending |
| TEST-02 | TBD | Pending |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 0
- Unmapped: 16 ⚠️

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after initial definition*
