---
id: T01
parent: S02
milestone: M001-r2v2t3
provides:
  - EvidenceArtifact typed model aligned to evidence-artifact.schema.json
  - Stable ID generator/validator for evidence artifacts (`ART-<ULID>`)
  - Deterministic evidence object key derivation (`evidence/<ULID[:2]>/<artifact_id>`)
key_files:
  - src/sps/evidence/ids.py
  - src/sps/evidence/models.py
  - pyproject.toml
key_decisions:
  - "Use `ART-<ULID>` for evidence stable IDs to match spec prefix examples while preserving uniqueness and sortability"
patterns_established:
  - "Evidence identifiers live in `sps.evidence.ids` with explicit validation + deterministic object key derivation"
observability_surfaces:
  - "./.venv/bin/python -c 'from sps.evidence.ids import new_evidence_id; print(new_evidence_id())'"
duration: 30m
verification_result: passed
completed_at: 2026-03-15T21:10:00Z
blocker_discovered: false
---

# T01: Implement evidence domain model + stable ID scheme

**Added EvidenceArtifact Pydantic model + evidence stable IDs and object key layout primitives.**

## What Happened
- Added `ulid-py` dependency for stable, sortable IDs.
- Implemented `sps.evidence.ids`:
  - `new_evidence_id()` → `ART-<ULID>`
  - `assert_valid_evidence_id()` / `is_valid_evidence_id()`
  - `evidence_object_key()` → `evidence/<ULID[:2]>/<artifact_id>`
- Implemented `sps.evidence.models.EvidenceArtifact` aligned to `model/sps/contracts/evidence-artifact.schema.json` with `extra='forbid'` and enums for `artifact_class` / `retention_class`.
- Appended decision D004 capturing the ID + key layout.

## Verification
- Ran: `./.venv/bin/python -c "from sps.evidence.ids import new_evidence_id, evidence_object_key; i=new_evidence_id(); print(i); print(evidence_object_key(i))"` → prints a valid `ART-...` id and its object key.

## Diagnostics
- Quick sanity: `./.venv/bin/python -c "from sps.evidence.models import EvidenceArtifact; print(EvidenceArtifact.model_json_schema()['title'])"`

## Deviations
- None.

## Known Issues
- None.

## Files Created/Modified
- `pyproject.toml` — added `ulid-py`.
- `src/sps/evidence/ids.py` — stable ID + object key helpers.
- `src/sps/evidence/models.py` — EvidenceArtifact typed model.
- `.gsd/DECISIONS.md` — appended evidence ID + object key layout decision.
