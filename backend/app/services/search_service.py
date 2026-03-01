"""
search_service.py

ALL LinkUp web search calls go through this module. No exceptions.

LinkUp fires ONLY when:
1. AI detects a fault not in cars_common_problems for this vehicle
2. eBay sold comps < 3 (market value fallback — TASK_005)

Never called for:
- Opportunity discovery
- Parts pricing primary lookup
- Any fault already in cars_common_problems
"""
import logging

from app.adapters.base import SearchResult
from app.adapters.linkup.stub import LinkUpStubAdapter
from config import settings

logger = logging.getLogger(__name__)


def get_search_adapter():
    """Returns stub or live adapter based on config."""
    if settings.linkup_stub:
        return LinkUpStubAdapter()
    # Live adapter not yet implemented — LINKUP_STUB must be true for now
    return LinkUpStubAdapter()


async def search_fault_intelligence(
    make: str,
    model: str,
    year: int,
    fault_type: str,
) -> SearchResult:
    """
    Searches for repair cost and fault intelligence for a specific
    fault on a specific vehicle model.

    Query format: "{make} {model} {year} {fault_type} repair cost UK common problem"
    """
    adapter = get_search_adapter()
    query = f"{make} {model} {year} {fault_type} repair cost UK common problem"
    logger.info("Searching fault intelligence: %s", query)
    result = await adapter.web_search(query)
    return result


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
    adapter = get_search_adapter()
    label_part = f" {write_off_label}" if write_off_label else ""
    query = f"{make} {model} {year}{label_part} sold price UK"
    logger.info("Searching market value fallback: %s", query)
    result = await adapter.web_search(query)
    return result
