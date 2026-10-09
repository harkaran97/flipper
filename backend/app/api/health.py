from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from config import settings

router = APIRouter()

INGESTION_STALE_AFTER = timedelta(hours=26)


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
    ingestion_stale = (
        last_poll_time is None
        or datetime.now(timezone.utc) - last_poll_time > INGESTION_STALE_AFTER
    )
    health["pipeline"] = {"ingestion": "stale" if ingestion_stale else "ok"}

    return health
