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
    logger.info(
        "[DETECTION] Event received: type=%s payload=%s",
        event.type,
        event.payload,
    )

    try:
        listing_id_str = event.payload.get("listing_id")
        if not listing_id_str:
            logger.error("[DETECTION] NEW_LISTING_FOUND event missing listing_id — payload: %s", event.payload)
            return

        logger.info("[DETECTION] Extracted listing_id=%s, opening DB session", listing_id_str)
        listing_id = uuid.UUID(listing_id_str)

        async with AsyncSessionLocal() as session:
            logger.info("[DETECTION] DB session opened, calling detect_problems for listing %s", listing_id)
            await detect_problems(session, listing_id, _bus)
            logger.info("[DETECTION] detect_problems completed for listing %s", listing_id)

    except Exception:
        logger.error(
            "[DETECTION] Detection failed for listing %s",
            event.payload.get("listing_id"),
            exc_info=True,
        )


# Module-level bus reference, set by register_detection_worker
_bus: EventBus | None = None


def register_detection_worker(bus: EventBus) -> None:
    """
    Registers the detection worker handler with the event bus.
    Called from main.py on startup.
    """
    global _bus
    _bus = bus
    logger.info("[DETECTION] Registering detection worker for EventType.NEW_LISTING_FOUND")
    bus.subscribe(EventType.NEW_LISTING_FOUND, handle_new_listing)
    logger.info("[DETECTION] Detection worker registered successfully")
