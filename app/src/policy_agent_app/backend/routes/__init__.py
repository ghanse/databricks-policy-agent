"""Versioned API router assembling every route module under ``/api/v1``."""

from fastapi import APIRouter

from policy_agent_app.backend.routes.approvals import router as approvals_router
from policy_agent_app.backend.routes.policies import router as policies_router
from policy_agent_app.backend.routes.remediations import router as remediations_router
from policy_agent_app.backend.routes.roles import router as roles_router
from policy_agent_app.backend.routes.scans import router as scans_router
from policy_agent_app.backend.routes.schedules import router as schedules_router
from policy_agent_app.backend.routes.settings import router as settings_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(policies_router)
api_router.include_router(approvals_router)
api_router.include_router(scans_router)
api_router.include_router(remediations_router)
api_router.include_router(schedules_router)
api_router.include_router(roles_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
