from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from sps.db.models import EvidenceArtifact, LegalHold, LegalHoldBinding

INVARIANT_ID_INV_004 = "INV-004"


@dataclass(frozen=True)
class InvariantDenied(Exception):
    invariant_id: str
    operation: str
    reason: str
    artifact_id: str
    hold_id: str | None = None

    def to_dict(self) -> dict:
        d = {
            "error": "invariant_denied",
            "invariant_id": self.invariant_id,
            "operation": self.operation,
            "reason": self.reason,
            "artifact_id": self.artifact_id,
        }
        if self.hold_id:
            d["hold_id"] = self.hold_id
        return d


def assert_not_on_legal_hold(*, db: Session, artifact_id: str, operation: str) -> None:
    """Fail closed if any ACTIVE legal hold binds this artifact or its linked case.

    This is the runtime hook for INV-004.
    """

    artifact = db.get(EvidenceArtifact, artifact_id)
    if artifact is None:
        # Not this function's concern; callers should 404.
        return

    # 1) Artifact-scoped holds
    hold_stmt = (
        select(LegalHold.hold_id)
        .join(LegalHoldBinding, LegalHoldBinding.hold_id == LegalHold.hold_id)
        .where(LegalHold.status == "ACTIVE")
        .where(LegalHoldBinding.artifact_id == artifact_id)
        .limit(1)
    )
    hold_id = db.execute(hold_stmt).scalar_one_or_none()
    if hold_id:
        raise InvariantDenied(
            invariant_id=INVARIANT_ID_INV_004,
            operation=operation,
            reason="Artifact is under active legal hold",
            artifact_id=artifact_id,
            hold_id=hold_id,
        )

    # 2) Case-scoped holds (if artifact is linked to a case)
    if artifact.linked_case_id:
        case_hold_stmt = (
            select(LegalHold.hold_id)
            .join(LegalHoldBinding, LegalHoldBinding.hold_id == LegalHold.hold_id)
            .where(LegalHold.status == "ACTIVE")
            .where(LegalHoldBinding.case_id == artifact.linked_case_id)
            .limit(1)
        )
        hold_id = db.execute(case_hold_stmt).scalar_one_or_none()
        if hold_id:
            raise InvariantDenied(
                invariant_id=INVARIANT_ID_INV_004,
                operation=operation,
                reason="Artifact is linked to a case under active legal hold",
                artifact_id=artifact_id,
                hold_id=hold_id,
            )
