"""
Ingestion Worker

Polls eBay for new vehicle listings on a fixed interval (broad fetch, no keyword query).
Deduplicates against the database.
Stores all new listings, then applies two-tier pre-filter on title + full description.
Listings passing pre-filter emit NEW_LISTING_FOUND events.
Listings failing pre-filter are stored with skip_reason='pre_filter_no_match'.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.adapters.base import RawListing
from app.adapters.ebay.listings import (
    EbayListingsAdapter,
    extract_description,
    extract_vehicle_from_item,
)
from app.adapters.ebay.stub import EbayStubAdapter
from app.core.database import AsyncSessionLocal
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.listing import Listing
from app.models.vehicle import Vehicle
from app.services.listing_prefilter import should_process_listing
from config import settings

logger = logging.getLogger(__name__)

# Shared state for health endpoint
last_poll_time: datetime | None = None


def get_listings_adapter():
    """Returns stub or live adapter based on config."""
    if settings.ebay_stub:
        return EbayStubAdapter()
    return EbayListingsAdapter()


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
    1. Fetch listings from adapter (broad, no keyword query)
    2. For each listing:
       a. Check duplicate — skip if seen
       b. Store in DB
       c. Fetch full item data (live eBay only) to enrich vehicle + description
       d. Apply two-tier pre-filter on title + full description
       e. Fail pre-filter → mark processed with skip_reason, commit, continue
       f. Pass pre-filter → seed Vehicle row, commit, emit NEW_LISTING_FOUND
    Returns: dict with counts for logging
    """
    stats = {"fetched": 0, "duplicates": 0, "passed": 0, "skipped": 0}

    raw_listings = await adapter.search_listings(query="", filters={})
    stats["fetched"] = len(raw_listings)

    for raw in raw_listings:
        if await is_duplicate(session, raw.external_id, raw.source):
            stats["duplicates"] += 1
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

        # Attempt full item fetch for live eBay listings to get structured
        # specifics and full seller description. Degrades gracefully on failure.
        full_item: dict | None = None
        if isinstance(adapter, EbayListingsAdapter) and raw.source == "ebay":
            try:
                full_item = await adapter.fetch_item(raw.external_id)
                full_description = extract_description(full_item)
                if full_description:
                    listing.description = full_description
                    logger.info(
                        "[INGESTION] Full description stored for ebay_id=%s len=%d",
                        raw.external_id, len(full_description),
                    )
            except Exception:
                logger.warning(
                    "[INGESTION] Item fetch failed for ebay_id=%s — continuing with summary data only",
                    raw.external_id,
                )

        # Two-tier pre-filter: match title + description before spending AI budget
        passes = should_process_listing(listing.title, listing.description or "")
        logger.info(
            "[PRE-FILTER] listing=%s title='%s' result=%s",
            raw.external_id,
            listing.title[:60],
            "PASS" if passes else "SKIP",
        )

        if not passes:
            listing.processed = True
            listing.skip_reason = "pre_filter_no_match"
            await session.commit()
            stats["skipped"] += 1
            continue

        # Seed a Vehicle row from stub data (stub adapter) or from eBay item
        # specifics / title heuristics (real eBay adapter).
        stub_vehicles: dict = getattr(adapter, "STUB_VEHICLE_DATA", {})
        vehicle_data = stub_vehicles.get(raw.external_id)

        if vehicle_data is None and raw.source == "ebay":
            item_data = full_item if full_item is not None else raw.raw_json
            if item_data:
                vehicle_data, _missing = extract_vehicle_from_item(item_data)

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
        stats["passed"] += 1

    total = stats["passed"] + stats["skipped"]
    if total > 0:
        pass_rate = stats["passed"] / total * 100
        logger.info(
            "[PRE-FILTER SUMMARY] fetched=%d passed=%d skipped=%d pass_rate=%.1f%%",
            stats["fetched"],
            stats["passed"],
            stats["skipped"],
            pass_rate,
        )

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
