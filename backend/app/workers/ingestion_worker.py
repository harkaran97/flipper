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
from app.adapters.ebay.listings import EbayListingsAdapter
from app.adapters.ebay.stub import EbayStubAdapter
from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.listing import Listing
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
        listing.processed = True
        stats["stored"] += 1

    await session.commit()
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


async def start_ingestion_worker(bus: EventBus) -> None:
    """
    Runs indefinitely. Polls every settings.poll_interval_seconds.
    Handles exceptions gracefully — logs error, continues polling.
    Never crashes the worker on a single failed cycle.
    """
    global last_poll_time

    logger.info(
        "Ingestion worker starting. Interval: %ds, stub: %s",
        settings.poll_interval_seconds,
        settings.ebay_stub,
    )
    adapter = get_listings_adapter()

    while True:
        try:
            async with AsyncSessionLocal() as session:
                stats = await run_poll_cycle(session, adapter, bus)
                last_poll_time = datetime.now(timezone.utc)
                logger.info("Poll cycle complete: %s", stats)
        except Exception as e:
            logger.error("Poll cycle failed: %s", e, exc_info=True)

        await asyncio.sleep(settings.poll_interval_seconds)
