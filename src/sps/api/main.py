from __future__ import annotations

from fastapi import FastAPI

from sps.config import get_settings

from sps.api.routes.cases import router as cases_router
from sps.api.routes.contradictions import router as contradictions_router
from sps.api.routes.dissents import router as dissents_router
from sps.api.routes.evidence import router as evidence_router
from sps.api.routes.reviews import router as reviews_router
from sps.api.routes.reviewer_console import router as reviewer_console_router

app = FastAPI(
    title="SPS API",
    version="0.0.0",
)

# Phase 1 API surface
app.include_router(cases_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1/reviews")
app.include_router(reviewer_console_router)
app.include_router(contradictions_router, prefix="/api/v1/contradictions")
app.include_router(dissents_router, prefix="/api/v1/dissents")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # Liveness: should not depend on Postgres/MinIO being reachable.
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    # Readiness: Phase 1 keeps this lightweight; deeper dependency checks land in later tasks/slices.
    settings = get_settings()
    return {"status": "ok", "env": settings.env}
