---
artifact_id: ART-SPS-CLAR-001
authoritative_or_informative: authoritative
authored_or_generated: authored_materialized
consumer_list:
- builders
- reviewers
- operators
- release_managers
owner: Architecture Lead
freshness_expectation: update only through approved clarification workflow
failure_if_missing: review_invalid
---


# SPS clarifications and materialization notes

## Closed clarifications carried forward from the BUILD_APPROVED package

| ID | Final decision |
| --- | --- |
| C-001 | Incentive sources use official federal, state, utility, and local program sources as authority. Approved aggregators are advisory only. |
| C-002 | Initial adapter scope supports two portal families plus bounded unsupported-case handling. |
| C-003 | Reviewer independence required on high-risk surfaces. Small-team exceptions require explicit emergency or override artifact and second-look follow-up. |
| C-004 | Emergency requires incident linkage, authorized declaration, bounded scope, and 24-hour maximum active duration absent renewed override. |
| C-005 | Rule ingestion cadence is nightly for configured jurisdictions. Freshness-window breach immediately marks affected outputs stale. |
| C-006 | Native auth only in v1 with an OIDC-ready boundary for later federation. |
| C-007 | Default retention is seven years, with jurisdictional override support and legal-hold supersession. |
| C-008 | Production prompts are versioned, reviewed, redaction-controlled, and cannot silently mutate authority rules. |
| C-009 | This package is US-only. Internationalization is out of scope. |
| C-010A | SPS outputs estimated fees as advisory until authoritative portal or official schedule confirmation is captured. |
| C-010B | Payment processing is out of scope in v1. |
| C-011 | SPS compliance profile is Tier 3 in this package. |
| C-012 | Same-rank contradictions block advancement. Source ranking is explicit. |
| C-013 | Unsupported workflows enter `MANUAL_SUBMISSION_REQUIRED` with `ManualFallbackPackage`. |
| C-014 | Binding evidence uses stable IDs and evidence retrieval SLA is 99% <= 5 seconds for non-archived artifacts. |

## Package materialization notes

These notes explain how the uploaded source documents were turned into the canonical repository layout.

### M-001 — spec file materialization
The uploaded SPS canonical package was normalized from escaped markdown into repository-ready markdown. No normative meaning was changed.

### M-002 — runtime binding placement
The uploaded implementation docx is preserved as a separate normative markdown document at `runtime-implementation-profile.md` rather than being merged into the main spec body. This avoids duplicated normative prose while keeping runtime binding explicit and discoverable.

### M-003 — derived artifact policy
The following files are derived to satisfy the canonical output shape and to make the package machine-consumable:
- `model/sps/model.yaml`
- `model/sps/contracts/*.json`
- `invariants/sps/*`
- `traceability/sps/traceability.yaml`
- `diagrams/sps/*.mmd`
- release templates and CI wiring

These files do not add product scope. They encode controls already required by the BUILD_APPROVED package.

### M-004 — no silent scope expansion
No new subsystem, actor class, authority path, or external dependency was introduced during package materialization. Where file-level structure had to be chosen, the lower-maintenance design was used.

### M-005 — unresolved external implementation detail boundaries
This package remains buildable, but the following are intentionally left for implementation within the spec boundary rather than invented here:
- exact adapter family names beyond the bounded initial scope
- exact jurisdiction corpus breadth and rollout order
- exact vendor choices for observability and object-storage providers
- exact UI component structure inside reviewer workflows

These are implementation choices only if they do not weaken authority boundaries, reviewer gates, runtime guards, or release controls.
