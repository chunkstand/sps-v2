from __future__ import annotations

from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sps.config import get_settings
from sps.logging.redaction import attach_redaction_filter

from sps.api.routes.cases import router as cases_router
from sps.api.routes.contradictions import router as contradictions_router
from sps.api.routes.dissents import router as dissents_router
from sps.api.routes.evidence import router as evidence_router
from sps.api.routes.reviews import router as reviews_router
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
app.include_router(dissents_router, prefix="/api/v1/dissents")
app.include_router(releases_router, prefix="/api/v1/releases")
app.include_router(ops_router, prefix="/api/v1/ops")
app.include_router(ops_page_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # Liveness: should not depend on Postgres/MinIO being reachable.
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    # Readiness: Phase 1 keeps this lightweight; deeper dependency checks land in later tasks/slices.
    settings = get_settings()
    return {"status": "ok", "env": settings.env}
