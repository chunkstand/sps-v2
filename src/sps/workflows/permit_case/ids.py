from __future__ import annotations

WORKFLOW_ID_PREFIX = "permit-case/"


def permit_case_workflow_id(case_id: str) -> str:
    """Stable workflow ID for a permit case.

    Keeping this convention in one place prevents drift between operator tooling,
    tests, and any future API surface.
    """

    if not case_id or not case_id.strip():
        raise ValueError("case_id must be non-empty")
    return f"{WORKFLOW_ID_PREFIX}{case_id}"
