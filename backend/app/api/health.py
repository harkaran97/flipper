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

    return health
