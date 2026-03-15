---
artifact_id: ART-SPS-RUNBOOK-003
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [operators, compliance, reviewers]
owner: Compliance Lead
freshness_expectation: update when source freshness policy changes
failure_if_missing: operator_execution_degraded
---

# Stale rule or stale source

## Trigger
- rule freshness expired
- authoritative source unavailable
- freshness cannot be established

## Required diagnostics
- affected case_id values
- affected RequirementSet or ComplianceEvaluation ids
- source system identifier
- freshness window and last successful refresh timestamp
- contradiction status if multiple sources disagree

## Exact operator actions
1. Mark `RequirementSet` or `ComplianceEvaluation` stale.
2. Block advancement.
3. Notify domain owner.
4. Refresh source or escalate contradiction.
5. Re-run downstream validations only after freshness is restored and reviewer policy is satisfied where applicable.

## Forbidden actions
- allowing stale requirement sets to auto-advance
- substituting aggregator-only evidence for authoritative evidence
- clearing stale status without refreshed source evidence

## Escalation owner
- Compliance Lead
- Research Lead when source ranking or source availability is implicated

## Success criteria
- affected artifacts are visibly stale
- advancement is blocked until refresh or reviewer resolution
- refreshed or replacement evidence is linked before stale status is cleared

## Closure evidence
- stale flag audit event
- refreshed evidence artifact ids or contradiction artifact id
- reviewer decision when required for re-entry
