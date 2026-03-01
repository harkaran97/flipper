"""
valuation_worker.py

Subscribes to REPAIR_ESTIMATED.
Calls market_valuator for each listing.
Emits MARKET_VALUE_ESTIMATED on completion.
"""
import logging
import uuid

from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.services.market_valuator import estimate_market_value

logger = logging.getLogger(__name__)

# Module-level bus reference, set by register_valuation_worker
_bus: EventBus | None = None


async def handle_repair_estimated(event: Event) -> None:
    """
    Handler for REPAIR_ESTIMATED events.
    Calls estimate_market_value() for the listing.
    On failure: logs error, does NOT crash the worker.
    """
    listing_id_str = event.payload.get("listing_id")
    if not listing_id_str:
        logger.error("REPAIR_ESTIMATED event missing listing_id")
        return

    try:
        listing_id = uuid.UUID(listing_id_str)
    except ValueError:
        logger.error("Invalid listing_id in event: %s", listing_id_str)
        return

    logger.info("Valuation worker processing listing %s", listing_id)

    try:
        async with AsyncSessionLocal() as session:
            await estimate_market_value(session, listing_id, _bus)
    except Exception:
        logger.error("Market valuation failed for listing %s", listing_id, exc_info=True)


def register_valuation_worker(bus: EventBus) -> None:
    """
    Registers the valuation worker handler with the event bus.
    Called from main.py on startup.
    """
    global _bus
    _bus = bus
    bus.subscribe(EventType.REPAIR_ESTIMATED, handle_repair_estimated)
    logger.info("Valuation worker subscribed to REPAIR_ESTIMATED")
