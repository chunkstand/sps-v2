from __future__ import annotations

from sps.adapters.contracts import (
    AdapterResult,
    ComplianceEvaluationRecord,
    DocumentCompilationSpec,
    DocumentTemplateSpec,
    ExternalStatusMappingEntryRecord,
    ExternalStatusMappingSelectionRecord,
    JurisdictionResolutionRecord,
    RequirementSetRecord,
    SubmissionExecutionPlan,
)
from sps.fixtures.phase4 import select_jurisdiction_fixtures, select_requirement_fixtures
from sps.fixtures.phase5 import select_compliance_fixtures
from sps.fixtures.phase6 import PHASE6_FIXTURES_DIR, select_document_fixtures
from sps.fixtures.phase7 import select_status_mapping_for_case, select_submission_adapter_fixtures


def load_jurisdiction(case_id: str) -> AdapterResult[list[JurisdictionResolutionRecord]]:
    fixtures, fixture_case_id = select_jurisdiction_fixtures(case_id)
    return AdapterResult(
        source_kind="fixture",
        source_key=fixture_case_id,
        value=[JurisdictionResolutionRecord.model_validate(item.model_dump(mode="json")) for item in fixtures],
    )


def load_requirements(case_id: str) -> AdapterResult[list[RequirementSetRecord]]:
    fixtures, fixture_case_id = select_requirement_fixtures(case_id)
    return AdapterResult(
        source_kind="fixture",
        source_key=fixture_case_id,
        value=[RequirementSetRecord.model_validate(item.model_dump(mode="json")) for item in fixtures],
    )


def load_compliance(case_id: str) -> AdapterResult[list[ComplianceEvaluationRecord]]:
    fixtures, fixture_case_id = select_compliance_fixtures(case_id)
    return AdapterResult(
        source_kind="fixture",
        source_key=fixture_case_id,
        value=[ComplianceEvaluationRecord.model_validate(item.model_dump(mode="json")) for item in fixtures],
    )


def load_documents(case_id: str) -> AdapterResult[DocumentCompilationSpec]:
    fixtures, fixture_case_id = select_document_fixtures(case_id)
    if not fixtures:
        return AdapterResult(
            source_kind="fixture",
            source_key=fixture_case_id,
            value=DocumentCompilationSpec(
                document_set_id="",
                case_id=case_id,
                package_version="",
                target_portal_family="",
                documents=[],
            ),
        )

    doc_set = fixtures[0]
    spec = DocumentCompilationSpec(
        document_set_id=doc_set.document_set_id,
        case_id=doc_set.case_id,
        package_version=doc_set.manifest.package_version,
        target_portal_family=doc_set.manifest.target_portal_family,
        required_attachments=doc_set.manifest.required_attachments,
        documents=[
            DocumentTemplateSpec(
                document_id=document.document_id,
                document_type=document.document_type,
                template_name=document.template_name,
                template_path=PHASE6_FIXTURES_DIR / document.template_name,
                variables=document.variables,
                provenance=document.provenance,
            )
            for document in doc_set.documents
        ],
        provenance=doc_set.provenance,
    )
    return AdapterResult(source_kind="fixture", source_key=fixture_case_id, value=spec)


def load_submission(case_id: str, *, target_portal_family: str) -> AdapterResult[SubmissionExecutionPlan | None]:
    fixtures, fixture_case_id = select_submission_adapter_fixtures(case_id)
    fixture = next(
        (item for item in fixtures if item.target_portal_family == target_portal_family),
        fixtures[0] if fixtures else None,
    )
    plan = (
        SubmissionExecutionPlan(
            case_id=case_id,
            target_portal_family=fixture.target_portal_family,
            channel_type=fixture.channel_type,
            reason=fixture.reason,
            operator_instructions=fixture.operator_instructions,
            required_proof_types=fixture.required_proof_types,
            required_attachment_sources=fixture.required_attachment_sources,
            escalation_owner=fixture.escalation_owner,
        )
        if fixture is not None
        else None
    )
    return AdapterResult(source_kind="fixture", source_key=fixture_case_id, value=plan)


def load_status_mapping(case_id: str) -> AdapterResult[ExternalStatusMappingSelectionRecord]:
    selection, fixture_case_id = select_status_mapping_for_case(case_id)
    record = ExternalStatusMappingSelectionRecord(
        adapter_family=selection.adapter_family,
        mapping_version=selection.mapping_version,
        mappings={
            raw_status: ExternalStatusMappingEntryRecord.model_validate(entry.model_dump(mode="json"))
            for raw_status, entry in selection.mappings.items()
        },
    )
    return AdapterResult(source_kind="fixture", source_key=fixture_case_id, value=record)
