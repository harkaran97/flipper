from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    health = {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.environment,
    }

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health["db"] = "connected"
    except Exception:
        health["status"] = "degraded"
        health["db"] = "unreachable"
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=health)

    from app.workers.ingestion_worker import last_poll_time
    health["last_poll"] = last_poll_time.isoformat() if last_poll_time else None
    health["pipeline"] = {
        "ingestion": "running",
        "detection": "running",
        "estimation": "running",
        "valuation": "running",
        "scoring": "running",
    }

    return health
