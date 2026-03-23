"""
Ingestion Worker

Polls eBay for new spares/repair listings on a fixed interval.
Deduplicates against the database.
Applies keyword pre-filter.
Stores new listings.
Emits NEW_LISTING_FOUND events.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.adapters.base import RawListing
from app.adapters.ebay.listings import EbayListingsAdapter, extract_vehicle_from_item
from app.adapters.ebay.stub import EbayStubAdapter
from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.listing import Listing
from app.models.vehicle import Vehicle
from config import settings

logger = logging.getLogger(__name__)

# Shared state for health endpoint
last_poll_time: datetime | None = None

OPPORTUNITY_KEYWORDS = [
    "spares", "repair", "non-runner", "non runner", "fault", "issue",
    "damage", "blown", "seized", "knocking", "smoking", "misfire",
    "gearbox", "clutch", "timing", "needs work", "project", "salvage",
]


def get_listings_adapter():
    """Returns stub or live adapter based on config."""
    if settings.ebay_stub:
        return EbayStubAdapter()
    return EbayListingsAdapter()


def passes_keyword_filter(listing: RawListing) -> bool:
    """Returns True if listing title or description contains at least one keyword."""
    text = f"{listing.title} {listing.description}".lower()
    return any(keyword in text for keyword in OPPORTUNITY_KEYWORDS)


async def is_duplicate(session, external_id: str, source: str) -> bool:
    """Check if a listing with this external_id and source already exists."""
    result = await session.execute(
        select(Listing).where(
            Listing.external_id == external_id,
            Listing.source == source,
        )
    )
    return result.scalar_one_or_none() is not None


async def run_poll_cycle(session, adapter, bus: EventBus) -> dict:
    """
    Single poll cycle:
    1. Fetch listings from adapter
    2. For each listing:
       a. Check duplicate — skip if seen
       b. Apply keyword filter — skip if no match
       c. Store in DB
       d. Emit NEW_LISTING_FOUND event
    Returns: dict with counts for logging
    """
    stats = {"fetched": 0, "duplicates": 0, "filtered": 0, "stored": 0}

    raw_listings = await adapter.search_listings(
        query="spares or repair", filters={}
    )
    stats["fetched"] = len(raw_listings)

    for raw in raw_listings:
        if await is_duplicate(session, raw.external_id, raw.source):
            stats["duplicates"] += 1
            continue

        if not passes_keyword_filter(raw):
            stats["filtered"] += 1
            continue

        listing = Listing(
            source=raw.source,
            external_id=raw.external_id,
            title=raw.title,
            description=raw.description,
            price_pence=raw.price_pence,
            postcode=raw.postcode,
            url=raw.url,
            raw_json=raw.raw_json,
            processed=False,
        )
        session.add(listing)
        await session.flush()

        # Seed a Vehicle row from stub data (stub adapter) or from eBay item
        # specifics / title heuristics (real eBay adapter).
        stub_vehicles: dict = getattr(adapter, "STUB_VEHICLE_DATA", {})
        vehicle_data = stub_vehicles.get(raw.external_id)
        if vehicle_data is None and raw.source == "ebay" and raw.raw_json:
            vehicle_data = extract_vehicle_from_item(raw.raw_json)
        if vehicle_data:
            session.add(Vehicle(listing_id=listing.id, **vehicle_data))

        listing.processed = True
        await session.commit()

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
        stats["stored"] += 1

    return stats


async def run_once(bus: EventBus) -> dict:
    """
    Run a single poll cycle outside the scheduled loop.
    Called by the /refresh endpoint for manual ingestion.
    Returns: dict with listings_found count.
    """
    adapter = get_listings_adapter()
    async with AsyncSessionLocal() as session:
        stats = await run_poll_cycle(session, adapter, bus)
    logger.info("Manual refresh cycle complete: %s", stats)
    return {"listings_found": stats.get("stored", 0)}


def _next_9am_utc() -> datetime:
    """Return the next 09:00 UTC datetime (tomorrow if already past today's 9am)."""
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now >= candidate:
        candidate = candidate.replace(day=candidate.day + 1)
    return candidate


async def start_ingestion_worker(bus: EventBus) -> None:
    """
    Runs indefinitely. Polls once daily at 09:00 UTC.
    Does NOT run immediately on startup — waits for next 09:00 UTC.
    Handles exceptions gracefully — logs error, waits for next scheduled time.
    """
    global last_poll_time

    logger.info("Ingestion worker starting. stub: %s", settings.ebay_stub)
    adapter = get_listings_adapter()

    while True:
        next_run = _next_9am_utc()
        wait_seconds = (next_run - datetime.now(timezone.utc)).total_seconds()
        hours, remainder = divmod(int(wait_seconds), 3600)
        minutes = remainder // 60
        logger.info(
            "[INGESTION] Next poll scheduled for %s (in %dh %dm)",
            next_run.strftime("%Y-%m-%dT%H:%M:%SZ"),
            hours,
            minutes,
        )
        await asyncio.sleep(wait_seconds)

        try:
            async with AsyncSessionLocal() as session:
                stats = await run_poll_cycle(session, adapter, bus)
                last_poll_time = datetime.now(timezone.utc)
                logger.info("Poll cycle complete: %s", stats)
        except Exception as e:
            logger.error("Poll cycle failed: %s", e, exc_info=True)
