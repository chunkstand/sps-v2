---
artifact_id: ART-SPS-RUNBOOK-004
authoritative_or_informative: authoritative
authored_or_generated: authored
consumer_list: [escalation_owners, operators, governance, audit]
owner: Escalation Owner
freshness_expectation: update when emergency policy changes
failure_if_missing: operator_execution_degraded
---

# Emergency declaration

## Trigger
- SEV1 or bounded SEV2 that meets emergency criteria

## Required diagnostics
- incident_id
- affected surfaces or case ids
- current blocker or unsafe condition
- proposed bypass scope
- proposed duration
- current override or renewal count for the same surface within 30 days

## Exact operator actions
1. Open incident.
2. Confirm emergency criteria.
3. Declare emergency with scope, owner, and duration.
4. Apply only allowed bypasses.
5. Maintain evidence and logging.
6. Exit and complete cleanup artifact.
7. Trigger redesign review if repeated-use thresholds are met.

## What may be skipped
- reviewer independence check in narrowly scoped cases
- staged rollout pacing for rollback or containment actions
- normal queue ordering

## What may never be skipped
- audit logging
- evidence capture
- explicit authorization for authority-bearing mutation
- incident linkage
- retroactive cleanup obligations

## Forbidden actions
- bypassing controls outside declared scope
- extending duration past policy maximum without renewed override
- reusing emergency state as a normal operating mode

## Escalation owner
- Escalation Owner
- Governance Lead
- Compliance Counsel for evidence or retention risk

## Success criteria
- emergency record exists
- duration does not exceed 24 hours without renewed override
- cleanup artifact is filed within 4 hours of emergency end

## Closure evidence
- emergency override artifact
- linked incident artifact
- cleanup completion record
- audit events for every bypassed step
