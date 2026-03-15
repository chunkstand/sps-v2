---
estimated_steps: 7
estimated_files: 2
---

# T01: Implement evidence domain model + stable ID scheme

**Slice:** S02 — Evidence registry API + MinIO content roundtrip
**Milestone:** M001-r2v2t3

## Description
Define the EvidenceArtifact domain model and choose/enforce the stable ID format + object key layout, aligned to the canonical evidence artifact schema.

## Steps
1. Read `model/sps/contracts/evidence-artifact.schema.json` and map required fields.
2. Implement stable ID generation + validation (default ULID unless spec mandates otherwise).
3. Define deterministic object key layout derived from the stable ID (no ambiguity; supports future partitioning).
4. Implement Pydantic model(s) for EvidenceArtifact metadata.
5. Add unit tests for ID validation and key derivation.
6. Add a tiny smoke import + ID generation check.
7. Document the chosen ID/key scheme inline.

## Must-Haves
- [ ] Evidence IDs are generated and validated in one place (`new_evidence_id()` or equivalent).
- [ ] Object key layout is deterministic and derived from the stable ID.
- [ ] EvidenceArtifact typed model aligns to `evidence-artifact.schema.json`.

## Verification
- `./.venv/bin/python -c "from sps.evidence.ids import new_evidence_id; print(new_evidence_id())"`
- `./.venv/bin/pytest -q tests/s02_ids_test.py` (or equivalent)

## Inputs
- `model/sps/contracts/evidence-artifact.schema.json` — contract to align with.

## Expected Output
- `src/sps/evidence/ids.py` — ID generation + validation helpers.
- `src/sps/evidence/models.py` — EvidenceArtifact typed models.
