"""
reset_pipeline.py

POST /reset-pipeline — truncate all pipeline tables in FK-safe order
"""
import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()

# Tables truncated in dependency order (children before parents)
_PIPELINE_TABLES = [
    "opportunities",
    "market_values",
    "repair_estimates",
    "exterior_conditions",
    "detected_faults",
    "vehicles",
    "listings",
]


class ResetPipelineResponse:
    pass


@router.post("/reset-pipeline")
async def reset_pipeline() -> dict:
    """Truncate all pipeline tables in FK-safe order."""
    async with AsyncSessionLocal() as session:
        for table in _PIPELINE_TABLES:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        await session.commit()

    logger.info("Pipeline tables truncated: %s", _PIPELINE_TABLES)
    return {"status": "ok", "tables_truncated": _PIPELINE_TABLES}
