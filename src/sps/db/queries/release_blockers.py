from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from sps.db.models import ContradictionArtifact, DissentArtifact

BLOCKING_DISSENT_SCOPE_SUFFIXES: tuple[str, ...] = ("HIGH_RISK", "AUTHORITY_BOUNDARY")


def get_open_blocking_contradictions(db: Session) -> list[ContradictionArtifact]:
    """Return open, blocking contradictions."""
    return (
        db.query(ContradictionArtifact)
        .filter(
            ContradictionArtifact.blocking_effect.is_(True),
            ContradictionArtifact.resolution_status == "OPEN",
        )
        .order_by(ContradictionArtifact.created_at.asc())
        .all()
    )


def get_open_blocking_dissents(
    db: Session,
    *,
    scope_suffixes: Sequence[str] | None = None,
) -> list[DissentArtifact]:
    """Return open dissents scoped to high-risk or authority-boundary domains."""
    suffixes = list(scope_suffixes or BLOCKING_DISSENT_SCOPE_SUFFIXES)
    if not suffixes:
        return []

    scope_filters = [DissentArtifact.scope.endswith(suffix) for suffix in suffixes]
    return (
        db.query(DissentArtifact)
        .filter(
            DissentArtifact.resolution_state == "OPEN",
            sa.or_(*scope_filters),
        )
        .order_by(DissentArtifact.created_at.asc())
        .all()
    )
