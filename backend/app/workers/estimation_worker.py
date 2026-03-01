"""
estimation_worker.py

Subscribes to PROBLEMS_DETECTED.
Calls repair_estimator for each listing.
Emits REPAIR_ESTIMATED on completion.
"""
import logging
import uuid

from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.services.repair_estimator import estimate_repairs

logger = logging.getLogger(__name__)

# Module-level bus reference, set by register_estimation_worker
_bus: EventBus | None = None


async def handle_problems_detected(event: Event) -> None:
    """
    Handler for PROBLEMS_DETECTED events.
    Calls estimate_repairs() for the listing.
    On failure: logs error, does NOT crash the worker.
    """
    listing_id_str = event.payload.get("listing_id")
    if not listing_id_str:
        logger.error("PROBLEMS_DETECTED event missing listing_id")
        return

    try:
        listing_id = uuid.UUID(listing_id_str)
    except ValueError:
        logger.error("Invalid listing_id in event: %s", listing_id_str)
        return

    logger.info("Estimation worker processing listing %s", listing_id)

    try:
        async with AsyncSessionLocal() as session:
            await estimate_repairs(session, listing_id, _bus)
    except Exception:
        logger.error("Estimation failed for listing %s", listing_id, exc_info=True)


def register_estimation_worker(bus: EventBus) -> None:
    """
    Registers the estimation worker handler with the event bus.
    Called from main.py on startup.
    """
    global _bus
    _bus = bus
    bus.subscribe(EventType.PROBLEMS_DETECTED, handle_problems_detected)
