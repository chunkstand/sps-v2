from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHASE6_FIXTURES_DIR = PROJECT_ROOT / "specs" / "sps" / "build-approved" / "fixtures" / "phase6"
DOCUMENTS_FIXTURE_PATH = PHASE6_FIXTURES_DIR / "documents.json"
PHASE6_FIXTURE_CASE_ID_OVERRIDE_ENV = "SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE"

FixtureModel = TypeVar("FixtureModel", bound=BaseModel)


class DocumentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: str
    template_name: str
    variables: dict[str, Any]
    provenance: dict[str, Any] | None = None


class ManifestReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: str
    artifact_id: str
    expected_digest: str


class DocumentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: str
    case_id: str
    package_version: str
    generated_at: datetime
    document_references: list[ManifestReference]
    required_attachments: list[str] = Field(default_factory=list)
    target_portal_family: str
    provenance: dict[str, Any] | None = None


class DocumentSetFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_set_id: str
    case_id: str
    schema_version: str
    generated_at: datetime
    documents: list[DocumentDefinition]
    manifest: DocumentManifest
    provenance: dict[str, Any] | None = None


class DocumentFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    generated_at: datetime
    document_sets: list[DocumentSetFixture]


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Fixture file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_document_fixtures(path: Path | None = None) -> DocumentFixtureDataset:
    fixture_path = path or DOCUMENTS_FIXTURE_PATH
    payload = _load_fixture(fixture_path)
    try:
        return DocumentFixtureDataset.model_validate(payload)
    except Exception as exc:  # pragma: no cover - rich error context
        raise ValueError(f"Document fixture validation failed for {fixture_path}") from exc


def load_phase6_fixtures() -> DocumentFixtureDataset:
    return load_document_fixtures()


def resolve_phase6_fixture_case_id(case_id: str) -> str:
    override = os.getenv(PHASE6_FIXTURE_CASE_ID_OVERRIDE_ENV)
    if override:
        override = override.strip()
    return override or case_id


def _rewrite_case_id(fixtures: list[FixtureModel], runtime_case_id: str) -> list[FixtureModel]:
    return [fixture.model_copy(update={"case_id": runtime_case_id}) for fixture in fixtures]


def select_document_fixtures(case_id: str) -> tuple[list[DocumentSetFixture], str]:
    fixture_case_id = resolve_phase6_fixture_case_id(case_id)
    dataset = load_document_fixtures()
    fixtures = [fixture for fixture in dataset.document_sets if fixture.case_id == fixture_case_id]
    return _rewrite_case_id(fixtures, case_id), fixture_case_id


def load_template(template_name: str) -> str:
    """Load a document template by name from the Phase 6 fixtures directory."""
    template_path = PHASE6_FIXTURES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")
