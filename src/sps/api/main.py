from __future__ import annotations

from fastapi import FastAPI

from sps.config import get_settings

app = FastAPI(
    title="SPS API",
    version="0.0.0",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    # Liveness: should not depend on Postgres/MinIO being reachable.
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    # Readiness: Phase 1 keeps this lightweight; deeper dependency checks land in later tasks/slices.
    settings = get_settings()
    return {"status": "ok", "env": settings.env}
