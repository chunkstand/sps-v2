from __future__ import annotations

"""Test-only failpoints.

These are used by Temporal/Postgres integration tests to simulate rare failure modes
(e.g. an activity crashing *after* a DB transaction has committed).

Hard requirements:
- Impossible to trigger in normal runtime unless explicitly enabled via env.
- Fires at most once per process per key.
- Safe to call from hot paths when disabled (cheap no-op).

Configuration (opt-in):
- SPS_ENABLE_TEST_FAILPOINTS=1
- SPS_TEST_FAILPOINT_KEYS=comma,separated,keys

Example key:
- apply_state_transition.after_commit/<request_id>
"""

import os
import threading
from collections import defaultdict
from dataclasses import dataclass


class FailpointFired(RuntimeError):
    """Raised when a failpoint is triggered."""


_LOCK = threading.Lock()
_FIRED_KEYS: set[str] = set()
_SEEN_COUNTS: dict[str, int] = defaultdict(int)


def _enabled() -> bool:
    return os.getenv("SPS_ENABLE_TEST_FAILPOINTS") == "1"


def _enabled_keys() -> set[str]:
    raw = os.getenv("SPS_TEST_FAILPOINT_KEYS", "")
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


@dataclass(frozen=True)
class FailpointState:
    fired_keys: set[str]
    seen_counts: dict[str, int]


def fail_once(key: str) -> None:
    """Fail once (per process) if the given key is enabled.

    Always increments an in-process "seen" counter when enabled and the key is
    configured. This lets tests assert that an activity reached a specific point
    multiple times (i.e. it was retried).
    """

    if not _enabled():
        return

    enabled = _enabled_keys()
    if key not in enabled:
        return

    with _LOCK:
        _SEEN_COUNTS[key] += 1
        if key in _FIRED_KEYS:
            return
        _FIRED_KEYS.add(key)

    raise FailpointFired(f"FAILPOINT_FIRED key={key}")


def get_seen_count(key: str) -> int:
    with _LOCK:
        return int(_SEEN_COUNTS.get(key, 0))


def was_fired(key: str) -> bool:
    with _LOCK:
        return key in _FIRED_KEYS


def snapshot_state() -> FailpointState:
    with _LOCK:
        return FailpointState(fired_keys=set(_FIRED_KEYS), seen_counts=dict(_SEEN_COUNTS))


def reset_for_tests() -> None:
    """Reset in-process failpoint state.

    Only intended for tests (since state is per-process and persists across test
    cases within the same pytest process).
    """

    with _LOCK:
        _FIRED_KEYS.clear()
        _SEEN_COUNTS.clear()
