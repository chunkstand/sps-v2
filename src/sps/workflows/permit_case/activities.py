from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.exc import IntegrityError
from temporalio import activity

from sps.db.models import (
    CaseTransitionLedger,
    ComplianceEvaluation,
    ContradictionArtifact,
    DocumentArtifact,
    IncentiveAssessment,
    JurisdictionResolution,
    PermitCase,
    Project,
    RequirementSet,
    ReviewDecision,
    SubmissionPackage,
)
from sps.db.session import get_sessionmaker
from sps.failpoints import FailpointFired, fail_once
from sps.fixtures.phase4 import select_jurisdiction_fixtures, select_requirement_fixtures
from sps.fixtures.phase5 import select_compliance_fixtures, select_incentive_fixtures
from sps.guards.guard_assertions import get_normalized_business_invariants
from sps.workflows.permit_case.contracts import (
    AppliedStateTransitionResult,
    CaseState,
    DeniedStateTransitionResult,
    PermitCaseStateSnapshot,
    PersistComplianceEvaluationRequest,
    PersistIncentiveAssessmentRequest,
    PersistJurisdictionResolutionRequest,
    PersistRequirementSetRequest,
    PersistReviewDecisionRequest,
    PersistSubmissionPackageRequest,
    StateTransitionRequest,
    StateTransitionResult,
    parse_state_transition_result,
)

logger = logging.getLogger(__name__)


@activity.defn
def ensure_permit_case_exists(case_id: str) -> bool:
    """Ensure a minimal `permit_cases` row exists.

    This proves the determinism boundary: all DB I/O happens in an activity, not
    in workflow code.

    Returns:
        True if the row was created, False if it already existed.
    """

    info = activity.info()
    logger.info(
        "activity.start name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s",
        info.workflow_id,
        info.workflow_run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    created = False

    try:
        with SessionLocal() as session:
            existing = session.get(PermitCase, case_id)
            if existing is None:
                created = True
                session.add(
                    PermitCase(
                        case_id=case_id,
                        tenant_id="tenant-local",
                        project_id=f"project-{case_id}",
                        # Contract-valid seed: the workflow proof path starts at REVIEW_PENDING.
                        case_state=CaseState.REVIEW_PENDING.value,
                        review_state="PENDING",
                        submission_mode="AUTOMATED",
                        portal_support_level="FULLY_SUPPORTED",
                        current_package_id=None,
                        current_release_profile="default",
                        legal_hold=False,
                        closure_reason=None,
                    )
                )
                session.commit()

        logger.info(
            "activity.ok name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s created=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            created,
        )
        return created
    except Exception as exc:
        # Temporal will record the exception; this log line provides a grep-able correlation tuple.
        logger.exception(
            "activity.error name=ensure_permit_case_exists workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            info.workflow_id,
            info.workflow_run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def fetch_permit_case_state(case_id: str) -> PermitCaseStateSnapshot:
    """Fetch the current PermitCase state for workflow branching."""

    workflow_id, run_id = _safe_temporal_ids()
    logger.info(
        "activity.start name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s",
        workflow_id,
        run_id,
        case_id,
    )

    SessionLocal = get_sessionmaker()
    try:
        with SessionLocal() as session:
            case = session.get(PermitCase, case_id)
            if case is None:
                raise LookupError(f"permit_cases row not found for case_id={case_id}")

            snapshot = PermitCaseStateSnapshot(
                case_id=case.case_id,
                case_state=CaseState(case.case_state),
                project_id=case.project_id,
            )

        logger.info(
            "activity.ok name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s case_state=%s",
            workflow_id,
            run_id,
            case_id,
            snapshot.case_state,
        )
        return snapshot
    except Exception as exc:
        logger.exception(
            "activity.error name=fetch_permit_case_state workflow_id=%s run_id=%s case_id=%s exc_type=%s",
            workflow_id,
            run_id,
            case_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_jurisdiction_resolutions(
    request: PersistJurisdictionResolutionRequest | dict,
) -> list[str]:
    """Persist jurisdiction resolution fixtures for a case idempotently."""

    req = PersistJurisdictionResolutionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    fixtures, fixture_case_id = select_jurisdiction_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    if not fixtures:
        raise LookupError(
            "no jurisdiction fixtures found for case_id=%s fixture_case_id=%s"
            % (req.case_id, fixture_case_id)
        )

    SessionLocal = get_sessionmaker()
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for fixture in fixtures:
                        existing = session.get(JurisdictionResolution, fixture.jurisdiction_resolution_id)
                        if existing is None:
                            session.add(
                                JurisdictionResolution(
                                    jurisdiction_resolution_id=fixture.jurisdiction_resolution_id,
                                    case_id=fixture.case_id,
                                    city_authority_id=fixture.city_authority_id,
                                    county_authority_id=fixture.county_authority_id,
                                    state_authority_id=fixture.state_authority_id,
                                    utility_authority_id=fixture.utility_authority_id,
                                    zoning_district=fixture.zoning_district,
                                    overlays=fixture.overlays,
                                    permitting_portal_family=fixture.permitting_portal_family,
                                    support_level=str(fixture.support_level),
                                    manual_requirements=fixture.manual_requirements,
                                    evidence_ids=fixture.evidence_ids,
                                    provenance=fixture.provenance,
                                    evidence_payload=fixture.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(fixture.jurisdiction_resolution_id)

                logger.info(
                    "jurisdiction_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )

                logger.info(
                    "activity.ok name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(JurisdictionResolution)
                .filter(JurisdictionResolution.case_id == req.case_id)
                .all()
            )
            existing_ids = [row.jurisdiction_resolution_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    f"jurisdiction_resolutions insert raced but rows not found for case_id={req.case_id}"
                )

            logger.info(
                "jurisdiction_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_jurisdiction_resolutions workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_requirement_sets(request: PersistRequirementSetRequest | dict) -> list[str]:
    """Persist requirement set fixtures for a case idempotently."""

    req = PersistRequirementSetRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    fixtures, fixture_case_id = select_requirement_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    if not fixtures:
        raise LookupError(
            "no requirement fixtures found for case_id=%s fixture_case_id=%s"
            % (req.case_id, fixture_case_id)
        )

    SessionLocal = get_sessionmaker()
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for fixture in fixtures:
                        existing = session.get(RequirementSet, fixture.requirement_set_id)
                        if existing is None:
                            freshness_expires_at = fixture.freshness_expires_at
                            if freshness_expires_at.tzinfo is None:
                                freshness_expires_at = freshness_expires_at.replace(tzinfo=dt.UTC)

                            session.add(
                                RequirementSet(
                                    requirement_set_id=fixture.requirement_set_id,
                                    case_id=fixture.case_id,
                                    jurisdiction_ids=fixture.jurisdiction_ids,
                                    permit_types=fixture.permit_types,
                                    forms_required=fixture.forms_required,
                                    attachments_required=fixture.attachments_required,
                                    fee_rules=fixture.fee_rules,
                                    source_rankings=fixture.source_rankings,
                                    freshness_state=str(fixture.freshness_state),
                                    freshness_expires_at=freshness_expires_at,
                                    contradiction_state=str(fixture.contradiction_state),
                                    evidence_ids=fixture.evidence_ids,
                                    provenance=fixture.provenance,
                                    evidence_payload=fixture.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(fixture.requirement_set_id)

                logger.info(
                    "requirements_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )

                logger.info(
                    "activity.ok name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(RequirementSet)
                .filter(RequirementSet.case_id == req.case_id)
                .all()
            )
            existing_ids = [row.requirement_set_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    f"requirement_sets insert raced but rows not found for case_id={req.case_id}"
                )

            logger.info(
                "requirements_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_requirement_sets workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_compliance_evaluation(
    request: PersistComplianceEvaluationRequest | dict,
) -> list[str]:
    """Persist compliance evaluation fixtures for a case idempotently."""

    req = PersistComplianceEvaluationRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    fixtures, fixture_case_id = select_compliance_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    if not fixtures:
        raise LookupError(
            "no compliance fixtures found for case_id=%s fixture_case_id=%s"
            % (req.case_id, fixture_case_id)
        )

    SessionLocal = get_sessionmaker()
    fixture_ids = [fixture.compliance_evaluation_id for fixture in fixtures]
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for fixture in fixtures:
                        existing = session.get(ComplianceEvaluation, fixture.compliance_evaluation_id)
                        if existing is None:
                            evaluated_at = fixture.evaluated_at
                            if evaluated_at.tzinfo is None:
                                evaluated_at = evaluated_at.replace(tzinfo=dt.UTC)

                            session.add(
                                ComplianceEvaluation(
                                    compliance_evaluation_id=fixture.compliance_evaluation_id,
                                    case_id=fixture.case_id,
                                    schema_version=fixture.schema_version,
                                    evaluated_at=evaluated_at,
                                    rule_results=[rule.model_dump() for rule in fixture.rule_results],
                                    blockers=[issue.model_dump() for issue in fixture.blockers],
                                    warnings=[issue.model_dump() for issue in fixture.warnings],
                                    provenance=fixture.provenance,
                                    evidence_payload=fixture.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(fixture.compliance_evaluation_id)

                logger.info(
                    "compliance_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )
                logger.info(
                    "activity.ok name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(ComplianceEvaluation)
                .filter(ComplianceEvaluation.compliance_evaluation_id.in_(fixture_ids))
                .all()
            )
            existing_ids = [row.compliance_evaluation_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    "compliance_evaluations insert raced but rows not found for compliance_evaluation_ids=%s"
                    % ",".join(fixture_ids)
                )

            logger.info(
                "compliance_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_compliance_evaluation workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_incentive_assessment(
    request: PersistIncentiveAssessmentRequest | dict,
) -> list[str]:
    """Persist incentive assessment fixtures for a case idempotently."""

    req = PersistIncentiveAssessmentRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    logger.info(
        "activity.start name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )

    fixtures, fixture_case_id = select_incentive_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    if not fixtures:
        raise LookupError(
            "no incentive fixtures found for case_id=%s fixture_case_id=%s"
            % (req.case_id, fixture_case_id)
        )

    SessionLocal = get_sessionmaker()
    fixture_ids = [fixture.incentive_assessment_id for fixture in fixtures]
    try:
        created_ids: list[str] = []
        created_count = 0
        with SessionLocal() as session:
            try:
                with session.begin():
                    for fixture in fixtures:
                        existing = session.get(IncentiveAssessment, fixture.incentive_assessment_id)
                        if existing is None:
                            assessed_at = fixture.assessed_at
                            if assessed_at.tzinfo is None:
                                assessed_at = assessed_at.replace(tzinfo=dt.UTC)

                            session.add(
                                IncentiveAssessment(
                                    incentive_assessment_id=fixture.incentive_assessment_id,
                                    case_id=fixture.case_id,
                                    schema_version=fixture.schema_version,
                                    assessed_at=assessed_at,
                                    candidate_programs=[
                                        program.model_dump(mode="json")
                                        for program in fixture.candidate_programs
                                    ],
                                    eligibility_status=fixture.eligibility_status,
                                    stacking_conflicts=fixture.stacking_conflicts,
                                    deadlines=[
                                        deadline.model_dump(mode="json")
                                        for deadline in fixture.deadlines
                                    ]
                                    if fixture.deadlines
                                    else None,
                                    source_ids=fixture.source_ids,
                                    advisory_value_range=fixture.advisory_value_range,
                                    authoritative_value_state=fixture.authoritative_value_state,
                                    provenance=fixture.provenance,
                                    evidence_payload=fixture.evidence_payload,
                                )
                            )
                            created_count += 1
                        created_ids.append(fixture.incentive_assessment_id)

                logger.info(
                    "incentives_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                    created_count,
                    1 if created_count == 0 else 0,
                )
                logger.info(
                    "activity.ok name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    fixture_case_id,
                    req.request_id,
                    len(created_ids),
                )
                return created_ids
            except IntegrityError:
                session.rollback()

        with SessionLocal() as session:
            existing_rows = (
                session.query(IncentiveAssessment)
                .filter(IncentiveAssessment.incentive_assessment_id.in_(fixture_ids))
                .all()
            )
            existing_ids = [row.incentive_assessment_id for row in existing_rows]
            if not existing_ids:
                raise RuntimeError(
                    "incentive_assessments insert raced but rows not found for incentive_assessment_ids=%s"
                    % ",".join(fixture_ids)
                )

            logger.info(
                "incentives_activity.persisted workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s created=0 idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            logger.info(
                "activity.ok name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s request_id=%s count=%s idempotent=1",
                workflow_id,
                run_id,
                req.case_id,
                fixture_case_id,
                req.request_id,
                len(existing_ids),
            )
            return existing_ids
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_incentive_assessment workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise



def _safe_temporal_ids() -> tuple[str | None, str | None]:
    """Best-effort activity correlation identifiers.

    This activity is sometimes called directly in DB-level integration tests where
    Temporal activity context is unavailable.
    """

    try:
        info = activity.info()
        return info.workflow_id, info.workflow_run_id
    except Exception:
        return None, None


_EVENT_CASE_STATE_CHANGED = "CASE_STATE_CHANGED"
_EVENT_APPROVAL_GATE_DENIED = "APPROVAL_GATE_DENIED"
_EVENT_CONTRADICTION_ADVANCE_DENIED = "CONTRADICTION_ADVANCE_DENIED"
_EVENT_INTAKE_PROJECT_DENIED = "INTAKE_PROJECT_REQUIRED_DENIED"
_EVENT_JURISDICTION_REQUIRED_DENIED = "JURISDICTION_REQUIRED_DENIED"
_EVENT_REQUIREMENTS_REQUIRED_DENIED = "REQUIREMENTS_REQUIRED_DENIED"
_EVENT_REQUIREMENTS_FRESHNESS_DENIED = "REQUIREMENTS_FRESHNESS_DENIED"
_EVENT_COMPLIANCE_REQUIRED_DENIED = "COMPLIANCE_REQUIRED_DENIED"
_EVENT_COMPLIANCE_FRESHNESS_DENIED = "COMPLIANCE_FRESHNESS_DENIED"
_EVENT_INCENTIVES_REQUIRED_DENIED = "INCENTIVES_REQUIRED_DENIED"
_EVENT_INCENTIVES_FRESHNESS_DENIED = "INCENTIVES_FRESHNESS_DENIED"
_GUARD_ASSERTION_REVIEW_GATE = "INV-SPS-STATE-002"
_GUARD_ASSERTION_CONTRADICTION = "INV-SPS-CONTRA-001"
_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS = "INV-SPS-RULE-001"
_GUARD_ASSERTION_COMPLIANCE_FRESHNESS = "INV-SPS-COMP-001"
_GUARD_ASSERTION_INCENTIVES_FRESHNESS = "INV-SPS-INC-001"
_ALLOWED_REVIEW_OUTCOMES = {"ACCEPT", "ACCEPT_WITH_DISSENT"}


def _deny(
    *,
    denied_at: dt.datetime,
    event_type: str,
    denial_reason: str,
    guard_assertion_id: str | None = None,
    normalized_business_invariants: list[str] | None = None,
) -> DeniedStateTransitionResult:
    return DeniedStateTransitionResult(
        event_type=event_type,
        denied_at=denied_at,
        denial_reason=denial_reason,
        guard_assertion_id=guard_assertion_id,
        normalized_business_invariants=normalized_business_invariants,
    )


@activity.defn
def apply_state_transition(request: StateTransitionRequest | dict) -> StateTransitionResult:
    """Authoritative Postgres-backed transition guard + state mutation.

    - Fail-closed: unknown transitions and missing preconditions return a structured denial.
    - Durable audit: both applied and denied attempts are persisted to case_transition_ledger.
    - Idempotent: request.request_id is treated as the ledger primary key.
    """

    req = StateTransitionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    requested_at = req.requested_at
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s",
        workflow_id,
        run_id,
        req.request_id,
        req.case_id,
        req.from_state,
        req.to_state,
    )

    SessionLocal = get_sessionmaker()

    # First attempt in a single transaction; on a rare INSERT race we re-load.
    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_event_type: str | None = None

                with session.begin():
                    existing = session.get(CaseTransitionLedger, req.request_id)
                    if existing is not None:
                        idempotent = True
                        persisted_event_type = existing.event_type
                        if existing.payload is None:
                            result = _deny(
                                denied_at=requested_at,
                                event_type=existing.event_type,
                                denial_reason="LEDGER_PAYLOAD_MISSING",
                            )
                        else:
                            result = parse_state_transition_result(existing.payload)
                    else:
                        case = session.get(PermitCase, req.case_id, with_for_update=True)
                        if case is None:
                            # With the current schema, we cannot write an audit row without
                            # an existing PermitCase due to FK constraints.
                            raise LookupError(f"permit_cases row not found for case_id={req.case_id}")

                        if case.case_state != req.from_state.value:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="FROM_STATE_MISMATCH",
                            )
                        elif (
                            req.from_state == CaseState.REVIEW_PENDING
                            and req.to_state == CaseState.APPROVED_FOR_SUBMISSION
                        ):
                            # Guard: blocking open contradictions must be resolved before advancement (CTL-14A).
                            blocking_contradiction = (
                                session.query(ContradictionArtifact)
                                .filter(
                                    ContradictionArtifact.case_id == req.case_id,
                                    ContradictionArtifact.blocking_effect.is_(True),
                                    ContradictionArtifact.resolution_status == "OPEN",
                                )
                                .first()
                            )
                            if blocking_contradiction is not None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_CONTRADICTION_ADVANCE_DENIED,
                                    denial_reason="BLOCKING_CONTRADICTION_UNRESOLVED",
                                    guard_assertion_id=_GUARD_ASSERTION_CONTRADICTION,
                                    normalized_business_invariants=get_normalized_business_invariants(
                                        _GUARD_ASSERTION_CONTRADICTION
                                    ),
                                )
                            else:
                                # Canonical protected transition: requires a valid ReviewDecision.
                                invariants = get_normalized_business_invariants(_GUARD_ASSERTION_REVIEW_GATE)

                                review_id = req.required_review_id
                                review: ReviewDecision | None = (
                                    session.get(ReviewDecision, review_id) if review_id else None
                                )

                                if (
                                    review_id is None
                                    or review is None
                                    or review.case_id != req.case_id
                                    or review.decision_outcome not in _ALLOWED_REVIEW_OUTCOMES
                                ):
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_APPROVAL_GATE_DENIED,
                                        denial_reason="REVIEW_DECISION_REQUIRED",
                                        guard_assertion_id=_GUARD_ASSERTION_REVIEW_GATE,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.INTAKE_PENDING
                            and req.to_state == CaseState.INTAKE_COMPLETE
                        ):
                            project = (
                                session.query(Project)
                                .filter(Project.case_id == req.case_id)
                                .one_or_none()
                            )
                            if project is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_INTAKE_PROJECT_DENIED,
                                    denial_reason="PROJECT_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.INTAKE_COMPLETE
                            and req.to_state == CaseState.JURISDICTION_COMPLETE
                        ):
                            resolution = (
                                session.query(JurisdictionResolution)
                                .filter(JurisdictionResolution.case_id == req.case_id)
                                .first()
                            )
                            if resolution is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_JURISDICTION_REQUIRED_DENIED,
                                    denial_reason="JURISDICTION_RESOLUTION_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.JURISDICTION_COMPLETE
                            and req.to_state == CaseState.RESEARCH_COMPLETE
                        ):
                            requirement_set = (
                                session.query(RequirementSet)
                                .filter(RequirementSet.case_id == req.case_id)
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_REQUIREMENTS_FRESHNESS
                            )
                            if requirement_set is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_REQUIREMENTS_REQUIRED_DENIED,
                                    denial_reason="REQUIREMENT_SET_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            elif requirement_set.freshness_state != "FRESH":
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_REQUIREMENTS_FRESHNESS_DENIED,
                                    denial_reason="REQUIREMENT_SET_STALE",
                                    guard_assertion_id=_GUARD_ASSERTION_REQUIREMENTS_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.RESEARCH_COMPLETE
                            and req.to_state == CaseState.COMPLIANCE_COMPLETE
                        ):
                            compliance_eval = (
                                session.query(ComplianceEvaluation)
                                .filter(ComplianceEvaluation.case_id == req.case_id)
                                .order_by(ComplianceEvaluation.evaluated_at.desc())
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_COMPLIANCE_FRESHNESS
                            )
                            if compliance_eval is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_COMPLIANCE_REQUIRED_DENIED,
                                    denial_reason="COMPLIANCE_EVALUATION_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_COMPLIANCE_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                evaluated_at = compliance_eval.evaluated_at
                                if evaluated_at.tzinfo is None:
                                    evaluated_at = evaluated_at.replace(tzinfo=dt.UTC)
                                freshness_deadline = requested_at - dt.timedelta(days=30)
                                if evaluated_at < freshness_deadline:
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_COMPLIANCE_FRESHNESS_DENIED,
                                        denial_reason="COMPLIANCE_EVALUATION_STALE",
                                        guard_assertion_id=_GUARD_ASSERTION_COMPLIANCE_FRESHNESS,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.COMPLIANCE_COMPLETE
                            and req.to_state == CaseState.INCENTIVES_COMPLETE
                        ):
                            incentive_assessment = (
                                session.query(IncentiveAssessment)
                                .filter(IncentiveAssessment.case_id == req.case_id)
                                .order_by(IncentiveAssessment.assessed_at.desc())
                                .first()
                            )
                            invariants = get_normalized_business_invariants(
                                _GUARD_ASSERTION_INCENTIVES_FRESHNESS
                            )
                            if incentive_assessment is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type=_EVENT_INCENTIVES_REQUIRED_DENIED,
                                    denial_reason="INCENTIVE_ASSESSMENT_REQUIRED",
                                    guard_assertion_id=_GUARD_ASSERTION_INCENTIVES_FRESHNESS,
                                    normalized_business_invariants=invariants,
                                )
                            else:
                                assessed_at = incentive_assessment.assessed_at
                                if assessed_at.tzinfo is None:
                                    assessed_at = assessed_at.replace(tzinfo=dt.UTC)
                                freshness_deadline = requested_at - dt.timedelta(days=3)
                                if assessed_at < freshness_deadline:
                                    result = _deny(
                                        denied_at=requested_at,
                                        event_type=_EVENT_INCENTIVES_FRESHNESS_DENIED,
                                        denial_reason="INCENTIVE_ASSESSMENT_STALE",
                                        guard_assertion_id=_GUARD_ASSERTION_INCENTIVES_FRESHNESS,
                                        normalized_business_invariants=invariants,
                                    )
                                else:
                                    result = AppliedStateTransitionResult(
                                        event_type=_EVENT_CASE_STATE_CHANGED,
                                        applied_at=requested_at,
                                    )
                                    case.case_state = req.to_state.value
                        elif (
                            req.from_state == CaseState.INCENTIVES_COMPLETE
                            and req.to_state == CaseState.DOCUMENT_COMPLETE
                        ):
                            # Guard: submission package must exist
                            package = (
                                session.query(SubmissionPackage)
                                .filter(SubmissionPackage.case_id == req.case_id)
                                .first()
                            )
                            if package is None:
                                result = _deny(
                                    denied_at=requested_at,
                                    event_type="DOCUMENT_PACKAGE_REQUIRED_DENIED",
                                    denial_reason="SUBMISSION_PACKAGE_REQUIRED",
                                )
                            else:
                                result = AppliedStateTransitionResult(
                                    event_type=_EVENT_CASE_STATE_CHANGED,
                                    applied_at=requested_at,
                                )
                                case.case_state = req.to_state.value
                        else:
                            result = _deny(
                                denied_at=requested_at,
                                event_type="STATE_TRANSITION_DENIED",
                                denial_reason="UNKNOWN_TRANSITION",
                            )

                        session.add(
                            CaseTransitionLedger(
                                transition_id=req.request_id,
                                case_id=req.case_id,
                                event_type=result.event_type,
                                from_state=req.from_state.value,
                                to_state=req.to_state.value,
                                actor_type=req.actor_type.value,
                                actor_id=req.actor_id,
                                correlation_id=req.correlation_id,
                                occurred_at=requested_at,
                                payload=result.model_dump(mode="json"),
                            )
                        )
                        persisted_event_type = result.event_type

                failpoint_key = f"apply_state_transition.after_commit/{req.request_id}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s correlation_id=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.correlation_id,
                        failpoint_key,
                    )
                    raise

                if idempotent:
                    logger.info(
                        "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        persisted_event_type,
                        result.result,
                    )
                else:
                    log_event = "activity.ok" if result.result == "applied" else "activity.denied"
                    logger.info(
                        "%s name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s event_type=%s result=%s idempotent=0",
                        log_event,
                        workflow_id,
                        run_id,
                        req.request_id,
                        req.case_id,
                        req.from_state,
                        req.to_state,
                        result.event_type,
                        result.result,
                    )

                return result
            except IntegrityError:
                # If we raced another attempt with the same request_id, the primary key
                # ensures we can safely re-load and return the persisted outcome.
                session.rollback()

        with SessionLocal() as session:
            existing = session.get(CaseTransitionLedger, req.request_id)
            if existing is None:
                raise RuntimeError(f"ledger insert failed but row not found for request_id={req.request_id}")
            if existing.payload is None:
                result = _deny(
                    denied_at=requested_at,
                    event_type=existing.event_type,
                    denial_reason="LEDGER_PAYLOAD_MISSING",
                )
            else:
                result = parse_state_transition_result(existing.payload)

            logger.info(
                "activity.ok name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s event_type=%s result=%s idempotent=1",
                workflow_id,
                run_id,
                req.request_id,
                req.case_id,
                existing.event_type,
                result.result,
            )
            return result
    except Exception as exc:
        logger.exception(
            "activity.error name=apply_state_transition workflow_id=%s run_id=%s request_id=%s case_id=%s from_state=%s to_state=%s exc_type=%s",
            workflow_id,
            run_id,
            req.request_id,
            req.case_id,
            req.from_state,
            req.to_state,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_review_decision(request: PersistReviewDecisionRequest | dict) -> str:
    """Persist a ReviewDecision row idempotently.

    Idempotency boundary: review_decisions.idempotency_key (unique).

    Returns:
        The persisted decision_id.
    """

    req = PersistReviewDecisionRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()

    decision_at = req.decision_at
    if decision_at.tzinfo is None:
        decision_at = decision_at.replace(tzinfo=dt.UTC)

    logger.info(
        "activity.start name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s outcome=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.decision_id,
        req.idempotency_key,
        req.decision_outcome,
    )

    SessionLocal = get_sessionmaker()

    try:
        with SessionLocal() as session:
            try:
                idempotent = False
                persisted_decision_id: str | None = None

                with session.begin():
                    existing = (
                        session.query(ReviewDecision)
                        .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                        .one_or_none()
                    )
                    if existing is not None:
                        idempotent = True
                        persisted_decision_id = existing.decision_id
                    else:
                        session.add(
                            ReviewDecision(
                                decision_id=req.decision_id,
                                schema_version=req.schema_version,
                                case_id=req.case_id,
                                object_type=req.object_type,
                                object_id=req.object_id,
                                decision_outcome=req.decision_outcome.value,
                                reviewer_id=req.reviewer_id,
                                reviewer_independence_status=req.reviewer_independence_status.value,
                                evidence_ids=req.evidence_ids,
                                contradiction_resolution=req.contradiction_resolution,
                                dissent_flag=req.dissent_flag,
                                notes=req.notes,
                                decision_at=decision_at,
                                idempotency_key=req.idempotency_key,
                            )
                        )
                        persisted_decision_id = req.decision_id

                assert persisted_decision_id is not None

                failpoint_key = f"persist_review_decision.after_commit/{req.idempotency_key}"
                try:
                    fail_once(failpoint_key)
                except FailpointFired:
                    logger.error(
                        "activity.failpoint name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotency_key=%s failpoint_key=%s",
                        workflow_id,
                        run_id,
                        req.case_id,
                        persisted_decision_id,
                        req.idempotency_key,
                        failpoint_key,
                    )
                    raise

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    persisted_decision_id,
                    1 if idempotent else 0,
                )
                return persisted_decision_id
            except IntegrityError:
                session.rollback()
                raced = (
                    session.query(ReviewDecision)
                    .filter(ReviewDecision.idempotency_key == req.idempotency_key)
                    .one_or_none()
                )
                if raced is None:
                    raise RuntimeError(
                        "review_decisions insert raced but row not found for idempotency_key="
                        f"{req.idempotency_key}"
                    )

                logger.info(
                    "activity.ok name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    raced.decision_id,
                )
                return raced.decision_id
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_review_decision workflow_id=%s run_id=%s case_id=%s decision_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.decision_id,
            type(exc).__name__,
        )
        raise


@activity.defn
def persist_submission_package(request: PersistSubmissionPackageRequest | dict) -> str:
    """
    Persist submission package + document artifacts idempotently.
    
    Generates documents from Phase 6 fixtures, registers them in evidence registry,
    stores SubmissionPackage row + DocumentArtifact rows, and updates 
    permit_cases.current_package_id in a single transaction.
    
    Returns the persisted package_id.
    """
    from sps.config import get_settings
    from sps.db.models import EvidenceArtifact
    from sps.documents.generator import generate_submission_package
    from sps.documents.registry import EvidenceRegistry
    from sps.evidence.ids import new_evidence_id
    from sps.evidence.models import ArtifactClass, RetentionClass
    from sps.fixtures.phase6 import select_document_fixtures
    from sps.storage.s3 import S3Storage
    
    req = PersistSubmissionPackageRequest.model_validate(request)
    workflow_id, run_id = _safe_temporal_ids()
    
    logger.info(
        "activity.start name=persist_submission_package workflow_id=%s run_id=%s case_id=%s request_id=%s",
        workflow_id,
        run_id,
        req.case_id,
        req.request_id,
    )
    
    # Load fixture and generate documents
    fixtures, fixture_case_id = select_document_fixtures(req.case_id)
    logger.info(
        "activity.lookup name=persist_submission_package workflow_id=%s run_id=%s case_id=%s fixture_case_id=%s override=%s",
        workflow_id,
        run_id,
        req.case_id,
        fixture_case_id,
        1 if fixture_case_id != req.case_id else 0,
    )
    
    if not fixtures:
        raise LookupError(
            f"no document fixtures found for case_id={req.case_id} fixture_case_id={fixture_case_id}"
        )
    
    doc_set = fixtures[0]
    
    # Generate submission package with all documents
    package_payload = generate_submission_package(doc_set, runtime_case_id=req.case_id)
    package_id = package_payload.package_id
    
    # Initialize evidence registry
    settings = get_settings()
    storage = S3Storage(settings=settings)
    registry = EvidenceRegistry(storage=storage, settings=settings)
    
    # Register manifest in evidence registry
    manifest_json = package_payload.manifest.model_dump_json(exclude_none=True, indent=None)
    manifest_bytes = manifest_json.encode("utf-8")
    manifest_reg = registry.register_manifest(
        content=manifest_bytes,
        case_id=req.case_id,
        provenance={"package_id": package_id, "request_id": req.request_id},
    )
    
    logger.info(
        "package_activity.manifest_registered case_id=%s manifest_id=%s artifact_id=%s digest=%s bytes=%d",
        req.case_id,
        package_payload.manifest.manifest_id,
        manifest_reg.artifact_id,
        manifest_reg.sha256_digest,
        manifest_reg.content_bytes,
    )
    
    SessionLocal = get_sessionmaker()
    
    try:
        with SessionLocal() as session:
            try:
                with session.begin():
                    # Check if package already exists (idempotency)
                    existing = session.get(SubmissionPackage, package_id)
                    if existing is not None:
                        logger.info(
                            "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s idempotent=1",
                            workflow_id,
                            run_id,
                            req.case_id,
                            package_id,
                        )
                        return package_id
                    
                    # Create manifest evidence artifact
                    session.add(
                        EvidenceArtifact(
                            artifact_id=manifest_reg.artifact_id,
                            artifact_class=ArtifactClass.MANIFEST.value,
                            producing_service="permit_case_workflow",
                            linked_case_id=req.case_id,
                            linked_object_id=package_id,
                            authoritativeness="AUTHORITATIVE",
                            retention_class=RetentionClass.CASE_CORE_7Y.value,
                            checksum=manifest_reg.sha256_digest,
                            storage_uri=manifest_reg.storage_uri,
                            content_bytes=manifest_reg.content_bytes,
                            content_type="application/json",
                            provenance={"request_id": req.request_id, "manifest_id": package_payload.manifest.manifest_id},
                            created_at=dt.datetime.now(dt.UTC),
                            legal_hold_flag=False,
                        )
                    )
                    session.flush()
                    
                    # Create submission package
                    session.add(
                        SubmissionPackage(
                            package_id=package_id,
                            case_id=req.case_id,
                            package_version=package_payload.package_version,
                            manifest_artifact_id=manifest_reg.artifact_id,
                            manifest_sha256_digest=manifest_reg.sha256_digest,
                            provenance={"request_id": req.request_id, "fixture_set_id": doc_set.document_set_id},
                        )
                    )
                    
                    # Flush to ensure package exists before document artifacts
                    session.flush()
                    
                    # Register and persist document artifacts
                    doc_count = 0
                    for doc_payload in package_payload.document_artifacts:
                        # Register document in evidence registry
                        doc_reg = registry.register_document(
                            content=doc_payload.content_bytes,
                            case_id=req.case_id,
                            document_type=doc_payload.document_type.value,
                            provenance={
                                "document_id": doc_payload.document_id,
                                "template_name": doc_payload.template_name,
                            },
                        )
                        
                        # Evidence artifact for document
                        session.add(
                            EvidenceArtifact(
                                artifact_id=doc_reg.artifact_id,
                                artifact_class=ArtifactClass.DOCUMENT.value,
                                producing_service="permit_case_workflow",
                                linked_case_id=req.case_id,
                                linked_object_id=doc_payload.document_id,
                                authoritativeness="AUTHORITATIVE",
                                retention_class=RetentionClass.CASE_CORE_7Y.value,
                                checksum=doc_reg.sha256_digest,
                                storage_uri=doc_reg.storage_uri,
                                content_bytes=doc_reg.content_bytes,
                                content_type="text/plain",
                                provenance={"document_id": doc_payload.document_id},
                                created_at=dt.datetime.now(dt.UTC),
                                legal_hold_flag=False,
                            )
                        )
                        session.flush()
                        
                        # Document artifact row
                        session.add(
                            DocumentArtifact(
                                document_artifact_id=new_evidence_id(),
                                package_id=package_id,
                                document_id=doc_payload.document_id,
                                document_type=doc_payload.document_type.value,
                                template_name=doc_payload.template_name,
                                evidence_artifact_id=doc_reg.artifact_id,
                                sha256_digest=doc_reg.sha256_digest,
                                provenance={"template_name": doc_payload.template_name},
                            )
                        )
                        doc_count += 1
                    
                    # Update permit_cases.current_package_id
                    case = session.get(PermitCase, req.case_id)
                    if case is None:
                        raise RuntimeError(f"permit_case not found: {req.case_id}")
                    case.current_package_id = package_id
                    
                    logger.info(
                        "package_activity.persisted workflow_id=%s run_id=%s case_id=%s package_id=%s manifest_id=%s doc_count=%s",
                        workflow_id,
                        run_id,
                        req.case_id,
                        package_id,
                        manifest_reg.artifact_id,
                        doc_count,
                    )
                
                logger.info(
                    "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s",
                    workflow_id,
                    run_id,
                    req.case_id,
                    package_id,
                )
                return package_id
                
            except IntegrityError as e:
                session.rollback()
                # Check if package exists from a race
                existing = session.get(SubmissionPackage, package_id)
                if existing is None:
                    raise RuntimeError(
                        f"submission_packages insert raced but row not found for package_id={package_id}"
                    ) from e
                
                logger.info(
                    "activity.ok name=persist_submission_package workflow_id=%s run_id=%s case_id=%s package_id=%s idempotent=1",
                    workflow_id,
                    run_id,
                    req.case_id,
                    package_id,
                )
                return package_id
                
    except Exception as exc:
        logger.exception(
            "activity.error name=persist_submission_package workflow_id=%s run_id=%s case_id=%s request_id=%s exc_type=%s",
            workflow_id,
            run_id,
            req.case_id,
            req.request_id,
            type(exc).__name__,
        )
        raise
