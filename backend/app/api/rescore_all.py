"""
rescore_all.py

POST /api/v1/rescore-all — re-emit NEW_LISTING_FOUND for every unprocessed listing.

Queries listings where processed = False and emits a NEW_LISTING_FOUND event for
each one directly onto the bus, bypassing the duplicate check in the ingestion
worker and feeding existing listings back through the full pipeline.

Shares the same 5-minute cooldown as /trigger-poll.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_bus, get_session
from app.api.trigger_poll import _COOLDOWN_SECONDS, _seconds_since_last_trigger
import app.api.trigger_poll as trigger_poll_module
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.listing import Listing

logger = logging.getLogger(__name__)

router = APIRouter()


async def _emit_unprocessed(bus: EventBus) -> None:
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Listing).where(Listing.processed == False)  # noqa: E712
        )
        listings = result.scalars().all()

    count = 0
    for listing in listings:
        try:
            await bus.emit(Event(
                type=EventType.NEW_LISTING_FOUND,
                payload={
                    "listing_id": str(listing.id),
                    "source": listing.source,
                    "title": listing.title,
                    "price_pence": listing.price_pence,
                    "postcode": listing.postcode,
                },
            ))
            count += 1
        except Exception as e:
            logger.error("[RESCORE] Failed to emit event for listing %s: %s", listing.id, e, exc_info=True)

    logger.info("[RESCORE] Re-emitted NEW_LISTING_FOUND for %d unprocessed listings", count)


@router.post("/rescore-all", status_code=202)
async def rescore_all(
    background_tasks: BackgroundTasks,
    bus: EventBus = Depends(get_bus),
) -> dict:
    """
    Re-emit NEW_LISTING_FOUND for all listings where processed = False.
    Returns {"listings_queued": N} on success, 429 if within the cooldown window.
    """
    elapsed = _seconds_since_last_trigger()
    if elapsed is not None and elapsed < _COOLDOWN_SECONDS:
        retry_after = int(_COOLDOWN_SECONDS - elapsed)
        return JSONResponse(
            status_code=429,
            content={
                "status": "cooldown",
                "message": "Poll triggered recently, please wait before refreshing again",
                "retry_after_seconds": retry_after,
            },
        )

    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Listing).where(Listing.processed == False)  # noqa: E712
        )
        listings = result.scalars().all()
        count = len(listings)

    from datetime import datetime, timezone
    trigger_poll_module._last_triggered_at = datetime.now(timezone.utc)

    logger.info("[RESCORE] Queuing %d unprocessed listings for re-scoring", count)
    background_tasks.add_task(_emit_unprocessed, bus)

    return {"listings_queued": count}
