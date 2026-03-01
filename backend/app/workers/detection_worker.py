"""
detection_worker.py

Subscribes to NEW_LISTING_FOUND.
Calls problem_detector for each new listing.
Emits PROBLEMS_DETECTED on completion.
"""
import logging
import uuid

from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.services.problem_detector import detect_problems

logger = logging.getLogger(__name__)


async def handle_new_listing(event: Event) -> None:
    """
    Handler for NEW_LISTING_FOUND events.
    Calls detect_problems() for the listing.
    On failure: logs error, does NOT crash the worker.
    """
    listing_id_str = event.payload.get("listing_id")
    if not listing_id_str:
        logger.error("NEW_LISTING_FOUND event missing listing_id")
        return

    try:
        listing_id = uuid.UUID(listing_id_str)
    except ValueError:
        logger.error("Invalid listing_id in event: %s", listing_id_str)
        return

    logger.info("Detection worker processing listing %s", listing_id)

    try:
        async with AsyncSessionLocal() as session:
            await detect_problems(session, listing_id, _bus)
    except Exception:
        logger.error("Detection failed for listing %s", listing_id, exc_info=True)


# Module-level bus reference, set by register_detection_worker
_bus: EventBus | None = None


def register_detection_worker(bus: EventBus) -> None:
    """
    Registers the detection worker handler with the event bus.
    Called from main.py on startup.
    """
    global _bus
    _bus = bus
    bus.subscribe(EventType.NEW_LISTING_FOUND, handle_new_listing)
