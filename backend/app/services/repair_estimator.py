"""
repair_estimator.py

Estimates repair costs for detected faults.
Uses eBay parts pricing as the primary source, with static knowledge base fallback.

NOTE: Full implementation is TASK_004. This file contains the minimum required
for TASK_005 smoke tests to pass (search_part_price import).
"""
import logging

logger = logging.getLogger(__name__)


async def search_part_price(part_name: str, vehicle: str) -> dict:
    """
    Searches for part pricing via eBay Parts adapter.
    Returns a dict with min_pence and max_pence estimates.

    Full implementation: TASK_004.
    """
    logger.info("search_part_price called for %s on %s", part_name, vehicle)
    return {"min_pence": 0, "max_pence": 0}
