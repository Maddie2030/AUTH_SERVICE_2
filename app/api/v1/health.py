import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health/live", summary="Liveness probe")
async def liveness():
    return {"status": "ok", "service": "mocktest-auth"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {"database": False, "redis": False}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error("Database health check failed: %s", e)

    try:
        from app.core.redis import get_redis
        r = await get_redis()
        await r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)

    all_healthy = all(checks.values())
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }
