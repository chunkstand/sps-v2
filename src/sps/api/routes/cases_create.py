from __future__ import annotations

from fastapi import APIRouter

from sps.api.routes.cases_impl import create_case

router = APIRouter()
router.add_api_route("/cases", create_case, methods=["POST"], status_code=201)

