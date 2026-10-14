from fastapi import APIRouter

from app.api.v1 import (
    admin,
    audit,
    auth,
    chat,
    chat_sessions,
    cloud_accounts,
    commitments,
    costs,
    executions,
    forecasts,
    health,
    kubernetes,
    notifications,
    recommendations,
    resources,
    settings,
    team,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(cloud_accounts.router)
api_router.include_router(resources.router)
api_router.include_router(costs.router)
api_router.include_router(recommendations.router)
api_router.include_router(forecasts.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(team.router)
api_router.include_router(chat.router)
api_router.include_router(chat_sessions.router)
api_router.include_router(kubernetes.router)
api_router.include_router(commitments.router)
api_router.include_router(notifications.router)
api_router.include_router(executions.router)