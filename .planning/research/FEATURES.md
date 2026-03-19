# Feature Research

**Domain:** Permit case workflow and release bundle management (SPS V2)
**Researched:** 2026-03-17
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Permit case intake and structured data capture | Permitting starts with a complete application record | MEDIUM | Forms, required fields, validation, applicant identity; aligns with case lifecycle expectations. |
| Workflow stages with tasks, milestones, and conditional routing | Case work is stepwise and policy-driven | MEDIUM | BPMN/CMMN style tasks, milestones, and entry/exit criteria are standard workflow primitives. |
| Human task assignment and approvals | Permits require staff review and sign-off | MEDIUM | Role-based queues, reassignments, approvals, and escalation paths. |
| Evidence/document attachment to cases | Permits and releases require supporting artifacts | MEDIUM | Store and link files, evidence metadata, and references to external registries. |
| Audit trail and state history | Regulatory workflows must be traceable | MEDIUM | Immutable state changes, who/when/why, and decision rationale. |
| Release bundle manifest creation and retrieval | Bundles need a canonical manifest to be verifiable | MEDIUM | Content-addressable manifests, deterministic ordering, and retrieval API. |
| Artifact integrity verification (digests, signatures) | Users expect tamper detection for releases | MEDIUM | Validate digest match against manifest; signature checks as baseline. |
| Provenance/attestation capture and validation | Supply chain security expectations are now baseline | HIGH | SLSA provenance and in-toto style attestations required for verification. |
| Access control for cases and bundles | Sensitive data and releases require strict access | MEDIUM | RBAC, scoped tokens, and audit for access events. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| End-to-end verifiable release bundles | Proves integrity from build to permit release | HIGH | Tie manifest, signatures, and provenance to a single verification summary. |
| Evidence registry integration across workflow and releases | Creates a single source of truth for decision evidence | HIGH | Link workflow evidence events to release bundle attestations. |
| Policy-as-code gating for releases | Automatic enforcement reduces human error | HIGH | Gate on SLSA level, required attestations, and signature policy. |
| Immutable bundle lifecycle with transparency log | Strong auditability and non-repudiation | HIGH | Publish signatures/attestations to append-only log for verification. |
| Continuous reconciliation between manifests and storage | Detects drift and silent corruption | MEDIUM | Periodic re-verification and alerting on mismatch. |
| Cross-case-to-release traceability | Enables compliance and incident response | MEDIUM | Link permit case IDs to release bundle IDs and manifests. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Manual “override verification” without audit | Speed in urgent releases | Breaks trust, weakens compliance, hides errors | Require break-glass with full audit + post-incident review. |
| Mutable release bundles post-approval | Fix mistakes quickly | Destroys provenance and traceability | Versioned bundles with explicit supersedes/rollback. |
| Ad-hoc workflow edits in production | Flexibility for edge cases | Invalidates audits and makes policies unenforceable | Versioned workflows with controlled migration paths. |

## Feature Dependencies

```
Release bundle signing/verification
    └──requires──> Manifest creation and digest indexing
                       └──requires──> Artifact registry access

Policy-as-code gating
    └──requires──> Provenance/attestation capture
                       └──requires──> Evidence registry integration

Cross-case-to-release traceability ──enhances──> Audit trail and state history
```

### Dependency Notes

- **Release bundle signing/verification requires manifest creation and digest indexing:** signatures are computed over deterministic manifest content and digests.
- **Policy-as-code gating requires provenance/attestation capture:** enforcement depends on structured attestations and verified evidence.
- **Cross-case-to-release traceability enhances audit trail and state history:** linking IDs across systems makes audits complete and actionable.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Permit case intake + workflow stages with approvals — core permit processing.
- [ ] Release bundle manifest creation + retrieval — canonical source of truth.
- [ ] Artifact integrity verification (digests + baseline signatures) — trust foundation.
- [ ] Evidence registry linkage for workflow decisions — compliance-grade auditability.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Policy-as-code gating — add once provenance coverage is stable.
- [ ] Continuous reconciliation and alerting — add when scale increases.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Transparency-log publishing — valuable but higher operational overhead.
- [ ] Cross-case analytics and optimization — only after core reliability is proven.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Release bundle manifest creation + retrieval | HIGH | MEDIUM | P1 |
| Artifact integrity verification (digests + signatures) | HIGH | MEDIUM | P1 |
| Evidence registry linkage | HIGH | HIGH | P1 |
| Policy-as-code gating | HIGH | HIGH | P2 |
| Continuous reconciliation | MEDIUM | MEDIUM | P2 |
| Transparency-log publishing | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Workflow stages with tasks/milestones | Camunda BPMN/CMMN primitives | -- | Implement a domain-specific workflow with explicit permit stages and audit logging. |
| Artifact signing and verification | Sigstore/Cosign signing + verification | -- | Use signature verification as baseline and integrate with evidence registry. |
| Manifested bundles | OCI manifest model | -- | Use deterministic bundle manifests for retrieval and verification. |

## Sources

- https://docs.camunda.org/manual/latest/reference/bpmn20/
- https://docs.camunda.org/manual/latest/reference/cmmn11/concepts/
- https://slsa.dev/spec/v1.2/
- https://docs.sigstore.dev/about/overview/
- https://github.com/opencontainers/image-spec/blob/main/manifest.md?plain=1
- https://github.com/in-toto/specification/blob/master/in-toto-spec.md?plain=1

---
*Feature research for: permit case workflow + release bundle management*
*Researched: 2026-03-17*
