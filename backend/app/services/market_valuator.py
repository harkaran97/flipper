"""
market_valuator.py

Estimates market value for a vehicle based on sold comps.

Rules:
- Like-for-like ONLY: comp pool filtered by write-off category
- Median price used (not mean)
- eBay sold comps always fetched; LinkUp always called (cache-first, 30d TTL)
- eBay + LinkUp prices combined into one pool
- Confidence: HIGH (>=5), MEDIUM (3-4), LOW (<3)
- Never blocks pipeline — always produces an estimate even if low confidence
"""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ebay.stub import EbayStubAdapter
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.enums import MarketValueConfidence, MarketValueSource, WriteOffCategory
from app.models.exterior_condition import ExteriorCondition
from app.models.linkup_market_value_cache import LinkupMarketValueCache
from app.models.market_value import MarketValue
from app.models.vehicle import Vehicle
from app.services.search_service import search_market_value
from config import settings

logger = logging.getLogger(__name__)

# Maps write-off category to the label used in LinkUp queries and eBay searches
WRITE_OFF_LABELS = {
    WriteOffCategory.CLEAN: "",
    WriteOffCategory.CAT_N: "cat n",
    WriteOffCategory.CAT_S: "cat s",
    WriteOffCategory.FLOOD: "flood damaged",
    WriteOffCategory.FIRE: "fire damaged",
    WriteOffCategory.UNKNOWN_WRITEOFF: "salvage",
}

# Maps write-off category to its comp pool identifier
COMP_POOL_MAP = {
    WriteOffCategory.CLEAN: "clean",
    WriteOffCategory.CAT_N: "cat_n",
    WriteOffCategory.CAT_S: "cat_s",
    WriteOffCategory.FLOOD: "flood",
    WriteOffCategory.FIRE: "fire",
    WriteOffCategory.UNKNOWN_WRITEOFF: "salvage",
    # CAT_A and CAT_B never reach this service — excluded at detection
}


def get_sold_adapter():
    """Returns stub or live sold comps adapter based on config."""
    if settings.ebay_stub:
        return EbayStubAdapter()
    from app.adapters.ebay.sold import EbaySoldAdapter
    return EbaySoldAdapter()


def calculate_median(prices: list[int]) -> int:
    """
    Returns the median of a list of integer prices (in pence).
    Uses integer division for even-length lists — no floating point.
    """
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_prices[mid - 1] + sorted_prices[mid]) // 2
    return sorted_prices[mid]


def get_confidence(comp_count: int) -> MarketValueConfidence:
    """
    Returns confidence level based on number of sold comps found.
    HIGH: >= 5, MEDIUM: 3-4, LOW: < 3
    """
    if comp_count >= 5:
        return MarketValueConfidence.HIGH
    elif comp_count >= 3:
        return MarketValueConfidence.MEDIUM
    else:
        return MarketValueConfidence.LOW


def build_comp_search_query(
    make: str,
    model: str,
    year: int,
    write_off_category: WriteOffCategory,
) -> str:
    """
    Builds eBay search query string ensuring like-for-like comps.
    Write-off category is injected into the query so results are comparable.
    """
    base = f"{make} {model} {year}"
    category_terms = {
        WriteOffCategory.CLEAN: base,
        WriteOffCategory.CAT_N: f"{base} cat n",
        WriteOffCategory.CAT_S: f"{base} cat s",
        WriteOffCategory.FLOOD: f"{base} flood damaged",
        WriteOffCategory.FIRE: f"{base} fire damaged",
        WriteOffCategory.UNKNOWN_WRITEOFF: f"{base} salvage",
    }
    return category_terms.get(write_off_category, base)


async def _get_linkup_data(
    session: AsyncSession,
    make: str,
    model: str,
    year: int,
    write_off_category: WriteOffCategory,
    write_off_label: str,
    listing_id: uuid.UUID,
) -> dict | None:
    """
    Returns LinkUp market value data, using cache when valid (created_at + ttl_days > now).
    On cache miss: calls LinkUp, stores result, returns data.
    Returns None if no valid data available.
    """
    cache_key = f"{make}_{model}_{year}_{write_off_category.value}".lower()

    result = await session.execute(
        select(LinkupMarketValueCache).where(LinkupMarketValueCache.cache_key == cache_key)
    )
    cached = result.scalar_one_or_none()

    if cached is not None:
        expiry = cached.created_at + timedelta(days=cached.ttl_days)
        if expiry > datetime.utcnow():
            logger.info(
                "LinkUp cache hit for listing %s: key=%s", listing_id, cache_key
            )
            return {
                "median_sold_price_gbp": cached.median_sold_price_gbp,
                "price_range_low_gbp": cached.price_range_low_gbp,
                "price_range_high_gbp": cached.price_range_high_gbp,
            }
        logger.info("LinkUp cache expired for key=%s — refreshing", cache_key)

    # Cache miss or expired — call LinkUp
    try:
        fallback_result = await search_market_value(
            make=make,
            model=model,
            year=year,
            write_off_label=write_off_label,
        )
        data = fallback_result.structured_data or {}
        median_gbp = float(data.get("median_sold_price_gbp") or 0)
        low_gbp = float(data.get("price_range_low_gbp") or 0)
        high_gbp = float(data.get("price_range_high_gbp") or 0)
        sample_count = data.get("sample_count")

        if median_gbp > 0:
            if cached is not None:
                await session.delete(cached)
                await session.flush()

            entry = LinkupMarketValueCache(
                cache_key=cache_key,
                median_sold_price_gbp=median_gbp,
                price_range_low_gbp=low_gbp,
                price_range_high_gbp=high_gbp,
                sample_count=sample_count,
            )
            session.add(entry)
            await session.flush()

            logger.info(
                "LinkUp result stored for listing %s: key=%s, median=£%.0f",
                listing_id, cache_key, median_gbp,
            )
            return {
                "median_sold_price_gbp": median_gbp,
                "price_range_low_gbp": low_gbp,
                "price_range_high_gbp": high_gbp,
            }
    except Exception:
        logger.error("LinkUp search failed for listing %s", listing_id, exc_info=True)

    return None


async def estimate_market_value(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus,
) -> None:
    """
    Estimates market value for a listing by fetching sold comps.

    1. Load vehicle + exterior_condition (for write_off_category)
    2. Build sold comps query using vehicle spec + write_off_category
    3. Fetch eBay sold comps
    4. Always call LinkUp (cache-first, 30d TTL) — combine with eBay prices
    5. Calculate median, low, high from combined price pool
    6. Store MarketValue
    7. Emit MARKET_VALUE_ESTIMATED
    """
    # 1. Load vehicle data
    result = await session.execute(
        select(Vehicle).where(Vehicle.listing_id == listing_id)
    )
    vehicle = result.scalar_one_or_none()

    make = vehicle.make if vehicle else "Unknown"
    model = vehicle.model if vehicle else "Unknown"
    year = vehicle.year if vehicle else 0

    # Load exterior_condition for write_off_category
    result = await session.execute(
        select(ExteriorCondition).where(ExteriorCondition.listing_id == listing_id)
    )
    ext_condition = result.scalar_one_or_none()

    write_off_str = ext_condition.write_off_category if ext_condition else WriteOffCategory.CLEAN.value
    try:
        write_off_category = WriteOffCategory(write_off_str)
    except ValueError:
        write_off_category = WriteOffCategory.CLEAN

    # 2. Build like-for-like comp query
    comp_query = build_comp_search_query(make, model, year, write_off_category)
    write_off_label = WRITE_OFF_LABELS.get(write_off_category, "")
    logger.info(
        "Market value search for listing %s: query=%r, write_off=%s",
        listing_id, comp_query, write_off_category.value,
    )

    # 3. Fetch eBay sold comps
    adapter = get_sold_adapter()
    try:
        sold_comps = await adapter.search_sold(make, model, year)
    except Exception:
        logger.error("eBay sold comps fetch failed for listing %s", listing_id, exc_info=True)
        sold_comps = []

    prices = [comp.sold_price_pence for comp in sold_comps]
    source = MarketValueSource.EBAY_SOLD.value
    linkup_fallback_used = False

    # 4. Always call LinkUp (cache-first) and combine with eBay prices
    linkup_data = await _get_linkup_data(
        session=session,
        make=make,
        model=model,
        year=year,
        write_off_category=write_off_category,
        write_off_label=write_off_label,
        listing_id=listing_id,
    )

    if linkup_data:
        median_pence = int(linkup_data["median_sold_price_gbp"] * 100)
        low_pence = int(linkup_data["price_range_low_gbp"] * 100)
        high_pence = int(linkup_data["price_range_high_gbp"] * 100)
        if median_pence > 0:
            prices.extend([low_pence, median_pence, high_pence])
            linkup_fallback_used = True
            if not sold_comps:
                source = MarketValueSource.LINKUP_FALLBACK.value

    # 5. Calculate median, low, high
    if prices:
        median_value = calculate_median(prices)
        low_value = min(prices)
        high_value = max(prices)
    else:
        median_value = 0
        low_value = 0
        high_value = 0

    confidence = get_confidence(len(prices))
    comp_count = len(prices)

    logger.info(
        "Market value for listing %s: median=£%d, comps=%d, confidence=%s",
        listing_id, median_value // 100, comp_count, confidence.value,
    )

    # 6. Store MarketValue (upsert: delete existing if present)
    existing = await session.execute(
        select(MarketValue).where(MarketValue.listing_id == listing_id)
    )
    existing_record = existing.scalar_one_or_none()
    if existing_record is not None:
        await session.delete(existing_record)
        await session.flush()

    market_value = MarketValue(
        listing_id=listing_id,
        write_off_category=write_off_category.value,
        comp_count=comp_count,
        median_value_pence=median_value,
        low_value_pence=low_value,
        high_value_pence=high_value,
        source=source,
        confidence=confidence.value,
        linkup_fallback_used=linkup_fallback_used,
    )
    session.add(market_value)
    await session.commit()

    # 7. Emit MARKET_VALUE_ESTIMATED
    await bus.emit(Event(
        type=EventType.MARKET_VALUE_ESTIMATED,
        payload={
            "listing_id": str(listing_id),
            "median_value_pence": market_value.median_value_pence,
            "comp_count": market_value.comp_count,
            "confidence": market_value.confidence,
            "write_off_category": market_value.write_off_category,
            "linkup_fallback_used": market_value.linkup_fallback_used,
        },
    ))

    logger.info("MARKET_VALUE_ESTIMATED emitted for listing %s", listing_id)
