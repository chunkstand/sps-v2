---
artifact_id: ART-SPS-RUNBOOK-005
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [release_managers, ops, governance, audit]
owner: Release Manager
freshness_expectation: update when rollback rules change
failure_if_missing: operator_execution_degraded
---

# Release rollback

## Trigger
- invariant violation on critical path
- submission path ambiguity
- evidence retrieval failure impacting review, release, or audit
- schema compatibility failure
- sustained security/auth failure on privileged paths

## Required diagnostics
- release_id
- affected versions and surfaces
- trigger evidence
- rollback target versions
- current incident linkage
- evidence retrieval health
- current blocker contradiction or dissent state where applicable

## Exact operator actions
1. Freeze further rollout.
2. Execute rollback steps.
3. Verify service, model, and evidence retrieval health.
4. Record rollback artifact.
5. Decide replay or hold.

## Forbidden actions
- partial rollback without artifact capture
- forward rollout while rollback trigger remains active
- resuming rollout before post-rollback validation is complete

## Escalation owner
- Release Manager
- Operations Lead
- Governance Lead when authority-bearing paths were affected

## Success criteria
- prior stable version restored
- rollback artifact includes trigger, executed steps, affected versions, and verification evidence
- reviewer/governance validates no authority drift occurred

## Closure evidence
- rollback artifact
- post-rollback validation evidence
- replay-or-hold decision record
- linked incident closure or mitigation state
