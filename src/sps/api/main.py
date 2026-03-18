from __future__ import annotations

import asyncio
from pathlib import Path
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from sps.config import get_settings
from sps.db.session import get_engine
from sps.logging.redaction import attach_redaction_filter
from sps.storage.s3 import S3Storage
from sps.workflows.temporal import connect_client

from sps.api.routes.cases import router as cases_router
from sps.api.routes.contradictions import router as contradictions_router
from sps.api.routes.dissents import router as dissents_router
from sps.api.routes.emergencies import router as emergencies_router
from sps.api.routes.evidence import router as evidence_router
from sps.api.routes.overrides import router as overrides_router
from sps.api.routes.reviews import router as reviews_router
from sps.api.routes.admin_portal_support import router as admin_portal_support_router
from sps.api.routes.admin_source_rules import router as admin_source_rules_router
from sps.api.routes.admin_incentive_programs import router as admin_incentive_programs_router
from sps.api.routes.reviewer_console import router as reviewer_console_router
from sps.api.routes.releases import router as releases_router
from sps.api.routes.ops import page_router as ops_page_router
from sps.api.routes.ops import router as ops_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    attach_redaction_filter()


_configure_logging()

app = FastAPI(
    title="SPS API",
    version="0.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Phase 1 API surface
app.include_router(cases_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1/reviews")
app.include_router(reviewer_console_router)
app.include_router(contradictions_router, prefix="/api/v1/contradictions")
app.include_router(admin_portal_support_router, prefix="/api/v1/admin/portal-support")
app.include_router(admin_source_rules_router, prefix="/api/v1/admin/source-rules")
app.include_router(admin_incentive_programs_router, prefix="/api/v1/admin/incentive-programs")
app.include_router(dissents_router, prefix="/api/v1/dissents")
app.include_router(releases_router, prefix="/api/v1/releases")
app.include_router(emergencies_router, prefix="/api/v1/emergencies")
app.include_router(overrides_router, prefix="/api/v1/overrides")
app.include_router(ops_router, prefix="/api/v1/ops")
app.include_router(ops_page_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # Liveness: should not depend on Postgres/MinIO being reachable.
    return {"status": "ok"}


def _ok_check() -> dict[str, str]:
    return {"status": "ok"}


def _error_check(exc: Exception) -> dict[str, str]:
    return {"status": "error", "error": type(exc).__name__}


def _check_postgres_ready() -> dict[str, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return _ok_check()
    except Exception as exc:
        return _error_check(exc)


def _check_temporal_ready() -> dict[str, str]:
    try:
        asyncio.run(connect_client())
        return _ok_check()
    except Exception as exc:
        return _error_check(exc)


def _check_storage_ready() -> dict[str, str]:
    settings = get_settings()
    try:
        storage = S3Storage(settings=settings)
        storage.head_bucket(settings.s3_bucket_evidence)
        return _ok_check()
    except Exception as exc:
        return _error_check(exc)


@app.get("/readyz")
def readyz() -> JSONResponse:
    settings = get_settings()
    checks: dict[str, dict[str, str]] = {
        "postgres": _check_postgres_ready(),
        "temporal": _check_temporal_ready(),
        "storage": _check_storage_ready(),
    }
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "error"
    payload: dict[str, Any] = {"status": status, "env": settings.env, "checks": checks}
    return JSONResponse(status_code=200 if status == "ok" else 503, content=payload)
