---
artifact_id: ART-SPS-PKG-ROOT-001
authoritative_or_informative: authoritative_index
authored_or_generated: authored
consumer_list:
- builders
- reviewers
- operators
- release_managers
- auditors
owner: Architecture Lead
freshness_expectation: must match spec version 2.0.1 package contents for release
failure_if_missing: operator_execution_degraded
---

# SPS full canonical spec package

This bundle materializes the uploaded SPS v2.0.1 canonical spec and runtime implementation profile into the Standing Framework canonical repository layout.

## What is included

- `/specs/sps/build-approved/spec.md` — authoritative SPS execution contract
- `/specs/sps/build-approved/runtime-implementation-profile.md` — normative runtime binding and implementation profile
- `/specs/sps/build-approved/plan.md` — implementation phase plan with gates and evidence
- `/specs/sps/build-approved/tasks.md` — build work breakdown with requirement/control mapping
- `/specs/sps/build-approved/clarifications.md` — closed clarifications plus package materialization notes
- `/specs/sps/build-approved/intent.md`, `/specs/sps/build-approved/lineage.yaml`, `/specs/sps/build-approved/artifact-obligations.yaml`
- `/model/sps/model.yaml` and `/model/sps/contracts/*.json`
- `/invariants/sps/*` including `/invariants/sps/guard-assertions.yaml`
- `/traceability/sps/traceability.yaml`
- `/runbooks/sps/*` including `legal-hold.md`
- `/observability/sps/*`
- `/releases/sps/templates/*`
- `/diagrams/sps/*.mmd` including entity-relationship and event-flow diagrams
- `/ci/sps/merge-authorization.yaml`

## Authority and precedence

Normative precedence for this package is:

1. signed machine-readable enforcement artifacts
2. signed release artifacts and bundle manifests
3. machine-readable schemas, invariants, policies, and model exports
4. normative prose in `spec.md` and `runtime-implementation-profile.md`
5. generated diagrams and reports
6. informative notes

## Build use

Start with:

1. `specs/sps/build-approved/spec.md`
2. `specs/sps/build-approved/runtime-implementation-profile.md`
3. `specs/sps/build-approved/plan.md`
4. `specs/sps/build-approved/tasks.md`
5. `traceability/sps/traceability.yaml`

Then implement contracts, runtime guards, workflows, reviewer service, release bundle validation, and runbooks in that order.

## Provenance

This package was materialized from the provided:
- SPS v2.0.1 Canonical Spec Package
- Implementation SPS v2.0.1 runtime profile
- Standing Framework canonical package instructions
- Standing Framework spec hardening addendum

No new product scope was introduced. Derived artifacts were added only to satisfy the canonical output shape and to make build execution discoverable and machine-checkable.

## Review hardening additions

This package also includes closure artifacts added during package review to eliminate internal inconsistencies and machine-coverage gaps:

- `/specs/sps/build-approved/package-review.md`
- `/specs/sps/build-approved/artifact-obligations.yaml`
- `/invariants/sps/guard-assertions.yaml`
- `/model/sps/contracts/state-transition-request.schema.json`
- `/overrides/sps/template-emergency.yaml`
- `/evidence/sps/manual-fallback/template-proof-bundle.yaml`
