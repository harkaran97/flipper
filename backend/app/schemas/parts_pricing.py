"""
parts_pricing.py

Pydantic models for the multi-source parts pricing service.
All prices are in pence. These schemas are used internally by the service
and exposed via the API detail endpoint.
"""
from typing import Optional

from pydantic import BaseModel


class PartResult(BaseModel):
    """A single parts listing from one supplier."""
    supplier: str                    # "eBay", "Autodoc", "GSF", etc.
    supplier_logo_key: str           # key for mobile logo lookup
    part_description: str
    part_number: Optional[str] = None
    condition: str                   # "new" | "reconditioned" | "used"
    base_price_pence: int
    delivery_pence: int              # 0 if free
    total_cost_pence: int            # base + delivery
    availability: str                # "in_stock" | "unknown"
    url: str                         # direct product link
    price_confidence: str            # "live" | "estimated"
    # "live" = scraped directly from page
    # "estimated" = from search summary, may be stale


class PartsPricingResult(BaseModel):
    """Aggregated pricing result for one part name across all suppliers."""
    part_name: str
    results: list[PartResult]        # sorted by total_cost_pence ASC
    cheapest_pence: Optional[int] = None
    sourced_at: str                  # ISO timestamp
    cache_hit: bool
