from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from sps.api.routes.reviews import require_reviewer_api_key
from sps.db.session import get_db
from sps.services.ops_metrics import OpsMetricsResponse, build_ops_metrics_response

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["ops"], dependencies=[Depends(require_reviewer_api_key)])
page_router = APIRouter(tags=["ops"])


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
