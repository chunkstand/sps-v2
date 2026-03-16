---
artifact_id: ART-SPS-RUNBOOK-007
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [release_managers, ops, governance, audit]
owner: Release Manager
freshness_expectation: update when validation gates or release policy changes
failure_if_missing: operator_execution_degraded
---

# Post-release validation

## Trigger
- release enters canary deployment stage
- staged rollout begins or expands
- governance requests post-release validation prior to full rollout

## Required diagnostics
- release_id
- rollout_stage (canary | staged | full)
- deployment version/build identifier
- validation window start/end timestamps
- rollback rehearsal artifact id
- monitoring dashboard links and alert status
- incident linkage (if any)

## Canary validation gate
1. Confirm canary traffic share and target cohort.
2. Review error rates, latency, and critical path SLOs.
3. Validate core workflows end-to-end for representative tenants.
4. Record rollback readiness and rehearsal outcome.

## Staged rollout gate
1. Expand traffic to staged cohort only after canary gate passes.
2. Compare metrics against baseline and canary period.
3. Validate operational alerts remain quiet and incident-free.
4. Confirm evidence registry ingestion and artifact retrieval health.

## Required report fields
- release_id
- rollout_stage and traffic share
- validation window (start/end)
- reviewer/operator name
- rollback rehearsal artifact id
- monitoring summary (key metrics + deltas)
- validation outcome (pass/hold/rollback)
- next action and owner

## Forbidden actions
- moving from canary to staged without recorded validation evidence
- proceeding to full rollout while rollback rehearsal evidence is missing
- closing validation without stakeholder sign-off

## Escalation owner
- Release Manager
- Operations Lead
- Governance Lead for authority-bearing paths

## Success criteria
- canary and staged gates recorded with passing evidence
- rollback rehearsal artifact verified and retrievable
- no critical alerts or incidents outstanding

## Closure evidence
- post-release validation report
- rollback rehearsal artifact reference
- monitoring snapshot or dashboard export
- approval or hold decision record
