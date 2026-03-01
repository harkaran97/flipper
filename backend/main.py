import logging

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.logging import setup_logging
from config import settings

app = FastAPI(title="Flipper API", version="0.1.0")
app.include_router(health_router)

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    setup_logging()
    if settings.environment == "development":
        try:
            from app.core.database import init_db
            await init_db()
        except Exception as e:
            logger.warning("Could not initialise database tables: %s", e)
