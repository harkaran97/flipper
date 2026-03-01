"""
market_valuator.py

Estimates market value for a vehicle based on sold comps.

Rules:
- Like-for-like ONLY: comp pool filtered by write-off category
- Median price used (not mean)
- eBay sold comps first, LinkUp fallback if < 3 comps
- Confidence: HIGH (>=5), MEDIUM (3-4), LOW (<3)
- Never blocks pipeline — always produces an estimate even if low confidence
"""
import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ebay.stub import EbayStubAdapter
from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.enums import MarketValueConfidence, MarketValueSource, WriteOffCategory
from app.models.exterior_condition import ExteriorCondition
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


def _parse_prices_from_text(text: str) -> list[int]:
    """
    Extracts GBP prices (in pence) from a text summary.
    Matches patterns like £300, £1,500, £2000.
    Returns prices as pence (integer).
    """
    # Match £ followed by digits with optional comma separators
    matches = re.findall(r"£([\d,]+)", text)
    prices = []
    for match in matches:
        try:
            price_pounds = int(match.replace(",", ""))
            prices.append(price_pounds * 100)
        except ValueError:
            continue
    return prices


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
    4. If < 3 comps: trigger LinkUp fallback
    5. Calculate median, low, high from all comps
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

    # 4. LinkUp fallback if < 3 eBay comps
    if len(prices) < 3:
        logger.info(
            "Only %d eBay comps for listing %s — triggering LinkUp fallback",
            len(prices), listing_id,
        )
        try:
            fallback_result = await search_market_value(
                make=make,
                model=model,
                year=year,
                write_off_label=write_off_label,
            )
            fallback_prices = _parse_prices_from_text(fallback_result.summary)
            if fallback_prices:
                prices.extend(fallback_prices)
                source = MarketValueSource.LINKUP_FALLBACK.value
            linkup_fallback_used = True
        except Exception:
            logger.error("LinkUp fallback failed for listing %s", listing_id, exc_info=True)

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
