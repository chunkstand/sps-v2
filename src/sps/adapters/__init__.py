from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sps.adapters import city_portal_family_a, fixtures, phaniville_manual
from sps.adapters.contracts import (
    AdapterResult,
    ComplianceEvaluationRecord,
    DocumentCompilationSpec,
    ExternalStatusMappingSelectionRecord,
    JurisdictionResolutionRecord,
    RequirementSetRecord,
    RuntimeAdapterSlice,
    SubmissionExecutionPlan,
)

RUNTIME_SLICES: tuple[RuntimeAdapterSlice, ...] = (
    city_portal_family_a,
    phaniville_manual,
)


def _select_runtime_slice(case_id: str) -> RuntimeAdapterSlice | None:
    for runtime_slice in RUNTIME_SLICES:
        if runtime_slice.supports_case(case_id):
            return runtime_slice
    return None


@dataclass(frozen=True)
class RuntimeAdapters:
    def load_jurisdiction(self, case_id: str) -> AdapterResult[list[JurisdictionResolutionRecord]]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            return runtime_slice.load_jurisdiction(case_id)
        return fixtures.load_jurisdiction(case_id)

    def load_requirements(self, case_id: str) -> AdapterResult[list[RequirementSetRecord]]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            return runtime_slice.load_requirements(case_id)
        return fixtures.load_requirements(case_id)

    def load_compliance(self, case_id: str) -> AdapterResult[list[ComplianceEvaluationRecord]]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            return runtime_slice.load_compliance(case_id)
        return fixtures.load_compliance(case_id)

    def load_documents(self, case_id: str) -> AdapterResult[DocumentCompilationSpec]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            return runtime_slice.load_documents(case_id)
        return fixtures.load_documents(case_id)

    def load_submission_plan(
        self,
        case_id: str,
        *,
        target_portal_family: str,
    ) -> AdapterResult[SubmissionExecutionPlan | None]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            result = runtime_slice.load_submission(
                case_id,
                target_portal_family=target_portal_family,
            )
            if result.value is not None:
                return result
        return fixtures.load_submission(case_id, target_portal_family=target_portal_family)

    def load_status_mapping(self, case_id: str) -> AdapterResult[ExternalStatusMappingSelectionRecord]:
        runtime_slice = _select_runtime_slice(case_id)
        if runtime_slice is not None:
            return runtime_slice.load_status_mapping(case_id)
        return fixtures.load_status_mapping(case_id)


@lru_cache
def get_runtime_adapters() -> RuntimeAdapters:
    return RuntimeAdapters()


def get_runtime_adapter_versions() -> dict[str, str]:
    return {
        runtime_slice.METADATA.adapter_key: runtime_slice.METADATA.version
        for runtime_slice in RUNTIME_SLICES
    }
