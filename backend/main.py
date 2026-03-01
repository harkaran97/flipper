import asyncio
import logging

from fastapi import FastAPI

from app.api.device_tokens import router as device_tokens_router
from app.api.health import router as health_router
from app.api.opportunities import router as opportunities_router
from app.api.refresh import router as refresh_router
from app.core.logging import setup_logging
from app.events.bus import EventBus
from config import settings

app = FastAPI(title="Flipper API", version="0.1.0")
app.include_router(health_router)
app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(refresh_router, prefix="/api/v1")
app.include_router(device_tokens_router, prefix="/api/v1")

logger = logging.getLogger(__name__)

bus = EventBus()


@app.on_event("startup")
async def startup():
    setup_logging()
    try:
        from app.core.database import init_db
        await init_db()
    except Exception as e:
        logger.warning("Could not initialise database tables: %s", e)

    if settings.environment == "development" or settings.seed_data:
        try:
            from app.core.database import AsyncSessionLocal
            from app.core.seed_data import seed_reference_data
            async with AsyncSessionLocal() as session:
                await seed_reference_data(session)
                logger.info("Reference data seeded")
        except Exception as e:
            logger.warning("Could not seed reference data: %s", e)

    from app.workers.detection_worker import register_detection_worker
    register_detection_worker(bus)
    logger.info("Detection worker registered")

    from app.workers.valuation_worker import register_valuation_worker
    register_valuation_worker(bus)
    logger.info("Valuation worker registered")
    from app.workers.estimation_worker import register_estimation_worker
    register_estimation_worker(bus)
    logger.info("Estimation worker registered")

    from app.workers.scoring_worker import register_scoring_worker
    register_scoring_worker(bus)
    logger.info("Scoring worker registered")

    from app.workers.ingestion_worker import start_ingestion_worker
    asyncio.create_task(start_ingestion_worker(bus))
    logger.info("Ingestion worker scheduled")
