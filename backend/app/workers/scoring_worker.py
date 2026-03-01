"""
scoring_worker.py

Subscribes to MARKET_VALUE_ESTIMATED.
Calls opportunity_scorer for each listing.
Emits OPPORTUNITY_CREATED on completion.
"""
import logging
import uuid

from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.services.opportunity_scorer import score_opportunity

logger = logging.getLogger(__name__)

# Module-level bus reference, set by register_scoring_worker
_bus: EventBus | None = None


async def handle_market_value_estimated(event: Event) -> None:
    """
    Handler for MARKET_VALUE_ESTIMATED events.
    Calls score_opportunity() for the listing.
    On failure: logs error, does NOT crash the worker.
    """
    listing_id_str = event.payload.get("listing_id")
    if not listing_id_str:
        logger.error("MARKET_VALUE_ESTIMATED event missing listing_id")
        return

    try:
        listing_id = uuid.UUID(listing_id_str)
    except ValueError:
        logger.error("Invalid listing_id in event: %s", listing_id_str)
        return

    logger.info("Scoring worker processing listing %s", listing_id)

    try:
        async with AsyncSessionLocal() as session:
            await score_opportunity(session, listing_id, _bus)
    except Exception:
        logger.error("Scoring failed for listing %s", listing_id, exc_info=True)


def register_scoring_worker(bus: EventBus) -> None:
    """
    Registers the scoring worker handler with the event bus.
    Called from main.py on startup.
    """
    global _bus
    _bus = bus
    bus.subscribe(EventType.MARKET_VALUE_ESTIMATED, handle_market_value_estimated)
    logger.info("Scoring worker subscribed to MARKET_VALUE_ESTIMATED")
