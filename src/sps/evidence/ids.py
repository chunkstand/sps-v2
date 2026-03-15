from __future__ import annotations

import re

import ulid

ARTIFACT_ID_PREFIX = "ART-"

# Crockford base32 ULID string (26 chars, uppercase, excludes I,L,O,U).
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_evidence_id() -> str:
    """Generate a new stable EvidenceArtifact ID.

    Spec examples use `ART-...` identifiers; Phase 1 uses `ART-<ULID>` to provide
    stable, sortable IDs without requiring a central sequence.
    """

    return f"{ARTIFACT_ID_PREFIX}{ulid.new()}"


def is_valid_evidence_id(value: str) -> bool:
    if not value.startswith(ARTIFACT_ID_PREFIX):
        return False
    suffix = value.removeprefix(ARTIFACT_ID_PREFIX)
    return bool(_ULID_RE.fullmatch(suffix))


def assert_valid_evidence_id(value: str) -> str:
    if not is_valid_evidence_id(value):
        raise ValueError(
            f"Invalid evidence artifact_id: {value!r}. Expected format: {ARTIFACT_ID_PREFIX}<ULID>."
        )
    return value


def evidence_object_key(artifact_id: str) -> str:
    """Deterministic object key for evidence content derived from stable ID."""

    assert_valid_evidence_id(artifact_id)
    ulid_part = artifact_id.removeprefix(ARTIFACT_ID_PREFIX)

    # Prefix partitioning prevents hot prefixes and keeps listings bounded.
    return f"evidence/{ulid_part[:2]}/{artifact_id}"
