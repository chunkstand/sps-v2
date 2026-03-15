from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from sps.db.models import EvidenceArtifact, LegalHold, LegalHoldBinding


@dataclass(frozen=True)
class DryRunPurgeResult:
    as_of: dt.datetime
    eligible_artifact_ids: list[str]


def dry_run_purge(*, db: Session, as_of: dt.datetime | None = None) -> DryRunPurgeResult:
    """List purge-eligible evidence artifacts without deleting anything.

    Phase 1 eligibility policy (intentionally conservative):
    - artifact has `expires_at` set and it is <= as_of
    - artifact is NOT bound by any ACTIVE legal hold (INV-004)

    This is a diagnostic surface and a safe planning primitive for future destructive purge.
    """

    if as_of is None:
        as_of = dt.datetime.now(tz=dt.UTC)

    # Active legal hold exists for this artifact_id
    active_hold_for_artifact = (
        select(LegalHoldBinding.binding_id)
        .join(LegalHold, LegalHold.hold_id == LegalHoldBinding.hold_id)
        .where(LegalHold.status == "ACTIVE")
        .where(LegalHoldBinding.artifact_id == EvidenceArtifact.artifact_id)
        .limit(1)
    )

    stmt = (
        select(EvidenceArtifact.artifact_id)
        .where(EvidenceArtifact.expires_at.is_not(None))
        .where(EvidenceArtifact.expires_at <= as_of)
        .where(~exists(active_hold_for_artifact))
        .order_by(EvidenceArtifact.artifact_id)
    )

    rows = db.execute(stmt).scalars().all()
    return DryRunPurgeResult(as_of=as_of, eligible_artifact_ids=list(rows))
