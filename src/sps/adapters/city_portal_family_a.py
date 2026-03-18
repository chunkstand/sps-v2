from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sps.adapters.contracts import (
    AdapterResult,
    ComplianceEvaluationRecord,
    DocumentCompilationSpec,
    DocumentTemplateSpec,
    ExternalStatusMappingEntryRecord,
    ExternalStatusMappingSelectionRecord,
    JurisdictionResolutionRecord,
    RequirementSetRecord,
    RuntimeAdapterMetadata,
    SubmissionExecutionPlan,
)

DATA_DIR = Path(__file__).resolve().parent / "data" / "city_portal_family_a"
TEMPLATES_DIR = DATA_DIR / "templates"
SLICE_PATH = DATA_DIR / "slice.json"
SLICE_CASE_ID = "CASE-CITYA-MANUAL-001"
METADATA = RuntimeAdapterMetadata(
    adapter_key="city_portal_family_a",
    version="2026-03-17.1",
)


class _SliceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_type: str
    template_name: str
    variables: dict[str, Any]
    provenance: dict[str, Any] | None = None


class _SliceDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_set_id: str
    case_id: str
    package_version: str
    target_portal_family: str
    required_attachments: list[str] = Field(default_factory=list)
    documents: list[_SliceDocument]
    provenance: dict[str, Any] | None = None


class _SliceStatusMappings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_family: str
    mapping_version: str
    mappings: list[ExternalStatusMappingEntryRecord]


class _SliceDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slice_case_id: str
    target_portal_family: str
    jurisdiction: JurisdictionResolutionRecord
    requirements: RequirementSetRecord
    compliance: ComplianceEvaluationRecord
    documents: _SliceDocuments
    submission: SubmissionExecutionPlan
    status_mapping: _SliceStatusMappings


@lru_cache
def _load_dataset() -> _SliceDataset:
    payload = json.loads(SLICE_PATH.read_text(encoding="utf-8"))
    return _SliceDataset.model_validate(payload)


def supports_case(case_id: str) -> bool:
    return case_id == _load_dataset().slice_case_id


def load_jurisdiction(case_id: str) -> AdapterResult[list[JurisdictionResolutionRecord]]:
    dataset = _load_dataset()
    record = dataset.jurisdiction.model_copy(update={"case_id": case_id})
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, [record])


def load_requirements(case_id: str) -> AdapterResult[list[RequirementSetRecord]]:
    dataset = _load_dataset()
    record = dataset.requirements.model_copy(update={"case_id": case_id})
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, [record])


def load_compliance(case_id: str) -> AdapterResult[list[ComplianceEvaluationRecord]]:
    dataset = _load_dataset()
    record = dataset.compliance.model_copy(update={"case_id": case_id})
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, [record])


def load_documents(case_id: str) -> AdapterResult[DocumentCompilationSpec]:
    dataset = _load_dataset()
    spec = DocumentCompilationSpec(
        document_set_id=dataset.documents.document_set_id,
        case_id=case_id,
        package_version=dataset.documents.package_version,
        target_portal_family=dataset.documents.target_portal_family,
        required_attachments=dataset.documents.required_attachments,
        documents=[
            DocumentTemplateSpec(
                document_id=document.document_id,
                document_type=document.document_type,
                template_name=document.template_name,
                template_path=TEMPLATES_DIR / document.template_name,
                variables=document.variables,
                provenance=document.provenance,
            )
            for document in dataset.documents.documents
        ],
        provenance=dataset.documents.provenance,
    )
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, spec)


def load_submission(case_id: str, *, target_portal_family: str) -> AdapterResult[SubmissionExecutionPlan | None]:
    dataset = _load_dataset()
    if target_portal_family != dataset.submission.target_portal_family:
        return AdapterResult("city_portal_family_a", dataset.slice_case_id, None)
    plan = dataset.submission.model_copy(update={"case_id": case_id})
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, plan)


def load_status_mapping(case_id: str) -> AdapterResult[ExternalStatusMappingSelectionRecord]:
    dataset = _load_dataset()
    record = ExternalStatusMappingSelectionRecord(
        adapter_family=dataset.status_mapping.adapter_family,
        mapping_version=dataset.status_mapping.mapping_version,
        mappings={item.raw_status: item for item in dataset.status_mapping.mappings},
    )
    return AdapterResult("city_portal_family_a", dataset.slice_case_id, record)
