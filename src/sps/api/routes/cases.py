from __future__ import annotations

from fastapi import APIRouter, Depends

from sps.auth.rbac import Role, require_roles

from .cases_impl import _DEFAULT_LIST_LIMIT, _MAX_LIST_LIMIT
from .cases_create import router as create_router
from .cases_operations import router as operations_router
from .cases_reads import router as reads_router

router = APIRouter(tags=["cases"], dependencies=[Depends(require_roles(Role.INTAKE))])
router.include_router(create_router)
router.include_router(reads_router)
router.include_router(operations_router)
