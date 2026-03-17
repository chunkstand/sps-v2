from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from sps.auth.rbac import Role, require_roles
from sps.db.session import get_db
from sps.services.ops_metrics import OpsMetricsResponse, build_ops_metrics_response
from sps.services.release_blockers import ReleaseBlockersResponse, build_release_blockers_response

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["ops"], dependencies=[Depends(require_roles(Role.OPS))])
page_router = APIRouter(tags=["ops"], dependencies=[Depends(require_roles(Role.OPS))])


@page_router.get("/ops", response_class=HTMLResponse)
def ops_dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "ops/index.html",
        {"request": request, "metrics_endpoint": "/api/v1/ops/dashboard/metrics"},
    )


@router.get("/dashboard/metrics", response_model=OpsMetricsResponse)
def get_ops_dashboard_metrics(db: Session = Depends(get_db)) -> OpsMetricsResponse:
    """Return queue depth, contradiction backlog, and stalled review metrics."""
    response = build_ops_metrics_response(db)
    logger.info(
        "ops_metrics.snapshot queue_depth=%d contradiction_backlog=%d stalled_review_count=%d",
        response.queue_depth,
        response.contradiction_backlog,
        response.stalled_review_count,
    )
    return response


@router.get("/release-blockers", response_model=ReleaseBlockersResponse)
def get_release_blockers(db: Session = Depends(get_db)) -> ReleaseBlockersResponse:
    """Return open blockers that should gate release bundle generation."""
    response = build_release_blockers_response(db)
    logger.info(
        "release_blockers.snapshot contradictions=%d dissents=%d blocker_count=%d",
        len(response.contradictions),
        len(response.dissents),
        response.blocker_count,
    )
    return response
