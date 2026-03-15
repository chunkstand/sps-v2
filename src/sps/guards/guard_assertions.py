from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# NOTE: This project keeps invariants under the repo root. Activities are long-lived
# and will call this repeatedly, so we load once per process.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_GUARD_ASSERTIONS_PATH = _PROJECT_ROOT / "invariants" / "sps" / "guard-assertions.yaml"


@lru_cache(maxsize=1)
def _load_guard_assertion_map(path: str | None = None) -> dict[str, list[str]]:
    p = Path(path) if path is not None else _DEFAULT_GUARD_ASSERTIONS_PATH
    if not p.exists():
        raise FileNotFoundError(f"guard assertions registry not found at {p}")

    raw = yaml.safe_load(p.read_text())
    assertions = raw.get("guard_assertions", []) if isinstance(raw, dict) else []

    out: dict[str, list[str]] = {}
    for a in assertions:
        if not isinstance(a, dict):
            continue
        guard_id = a.get("guard_assertion_id")
        invs = a.get("normalized_business_invariants")
        if isinstance(guard_id, str) and isinstance(invs, list) and all(isinstance(x, str) for x in invs):
            out[guard_id] = list(invs)

    return out


def get_normalized_business_invariants(guard_assertion_id: str) -> list[str]:
    """Resolve a guard assertion to its normalized invariant IDs.

    Returns an empty list when the guard assertion ID is unknown.
    """

    m = _load_guard_assertion_map()
    invs = m.get(guard_assertion_id)
    if invs is None:
        logger.warning("guard_assertion.unknown guard_assertion_id=%s", guard_assertion_id)
        return []
    return list(invs)
