from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["reviewer-console"])

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/reviewer", response_class=HTMLResponse)
def reviewer_console(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "reviewer_console.html", {"request": request})
