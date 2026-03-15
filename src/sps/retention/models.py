from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class LegalHoldStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class LegalHold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hold_id: str
    reason: str
    requested_by: str
    authorized_by: str

    created_at: dt.datetime
    released_at: dt.datetime | None = None

    status: LegalHoldStatus


class LegalHoldBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str
    hold_id: str

    artifact_id: str | None = None
    case_id: str | None = None

    created_at: dt.datetime

    def target_kind(self) -> str:
        if self.artifact_id and not self.case_id:
            return "artifact"
        if self.case_id and not self.artifact_id:
            return "case"
        return "invalid"
