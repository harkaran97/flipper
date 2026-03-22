"""
search_service.py

ALL LinkUp web search calls go through this module. No exceptions.

LinkUp fires ONLY when:
1. AI detects a fault not in cars_common_problems for this vehicle
2. eBay sold comps < 3 (market value fallback — TASK_005)
3. Parts price lookup for repair estimation

Never called for:
- Opportunity discovery
- Any fault already in cars_common_problems
"""
import logging

from app.adapters.base import SearchResult
from app.adapters.linkup.stub import PARTS_STUB_DEFAULT, PARTS_STUB_RESULTS, LinkUpStubAdapter
import app.adapters.linkup.search as linkup_search
from config import settings

logger = logging.getLogger(__name__)


async def search_fault_intelligence(
    make: str,
    model: str,
    year: int,
    fault_type: str,
) -> SearchResult:
    """
    Searches for repair cost and fault intelligence for a specific
    fault on a specific vehicle model.

    Query format: "{make} {model} {year} {fault_type} repair cost common problem UK"
    """
    if settings.linkup_stub:
        query = f"{make} {model} {year} {fault_type} repair cost UK common problem"
        logger.info("Searching fault intelligence (stub): %s", query)
        return await LinkUpStubAdapter().web_search(query)

    logger.info("Searching fault intelligence (live): %s %s %d %s", make, model, year, fault_type)
    return await linkup_search.search_fault_intelligence(make, model, year, fault_type)


async def search_market_value(
    make: str,
    model: str,
    year: int,
    write_off_label: str,
) -> SearchResult:
    """
    Fallback market value search via LinkUp.
    Only fires when eBay returns fewer than 3 sold comps.

    Query format: "{make} {model} {year} {write_off_label} sold price UK"
    Example: "BMW 3 Series 2010 cat n sold price UK"
    """
    if settings.linkup_stub:
        label_part = f" {write_off_label}" if write_off_label else ""
        query = f"{make} {model} {year}{label_part} sold price UK"
        logger.info("Searching market value fallback (stub): %s", query)
        return await LinkUpStubAdapter().web_search(query)

    logger.info("Searching market value fallback (live): %s %s %d %s", make, model, year, write_off_label)
    return await linkup_search.search_market_value(make, model, year, write_off_label)
async def search_parts_price(
    make: str,
    model: str,
    year: int,
    part_name: str,
) -> list[dict]:
    """
    Searches for current UK parts prices for a specific part and vehicle.

    Query format: "{make} {model} {year} {part_name} buy UK"
    Returns list of {supplier, price_pence, url, in_stock}.
    Returns empty list on failure — never crashes estimation.
    """
    logger.info("Searching parts price: %s %s %d %s", make, model, year, part_name)

    if settings.linkup_stub:
        key = part_name.lower()
        results = PARTS_STUB_RESULTS.get(key, PARTS_STUB_DEFAULT)
        logger.debug("Parts stub returning %d results for '%s'", len(results), part_name)
        return list(results)

    # Live LinkUp not yet implemented for structured parts search
    logger.warning("Live parts search not implemented — returning empty")
    return []
