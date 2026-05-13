from fastapi import APIRouter
from app.api.v1.endpoints import trades, status, balance, notifications, ai, stats, local_ai

api_router = APIRouter()
api_router.include_router(trades.router,        prefix="/trades",   tags=["trades"])
api_router.include_router(status.router,        prefix="/status",   tags=["status"])
api_router.include_router(balance.router,       prefix="/balance",  tags=["balance"])
api_router.include_router(ai.router,            prefix="/ai",       tags=["ai"])
api_router.include_router(local_ai.router,      prefix="/local-ai", tags=["local-ai"])
api_router.include_router(stats.router,         prefix="/stats",    tags=["stats"])
api_router.include_router(notifications.router,                     tags=["notifications"])
