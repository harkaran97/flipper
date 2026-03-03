"""
ebay.py

eBay Parts adapter for the multi-source parts pricing service.
Uses the eBay Browse API, category 33743 (Car Parts & Accessories).
Filters to UK location and delivery only.

Uses stub when EBAY_STUB=true.
"""
import logging

from app.adapters.parts.base import BasePartsSupplierAdapter
from app.adapters.parts.stub import StubPartsAdapter
from app.schemas.parts_pricing import PartResult
from config import settings

logger = logging.getLogger(__name__)

EBAY_PARTS_CATEGORY = "33743"
EBAY_BROWSE_BASE = "https://api.ebay.com/buy/browse/v1"

_CONDITION_MAP = {
    "NEW": "new",
    "LIKE_NEW": "new",
    "VERY_GOOD": "reconditioned",
    "GOOD": "used",
    "ACCEPTABLE": "used",
    "FOR_PARTS_OR_NOT_WORKING": "used",
}


class EbayPartsAdapter(BasePartsSupplierAdapter):
    """
    Queries eBay Browse API for UK car parts listings.
    Returns top 5 results sorted by total cost (part + shipping).
    """

    async def search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        if settings.ebay_stub:
            stub = StubPartsAdapter()
            return await stub.search(part_name, make, model, year)

        try:
            return await self._live_search(part_name, make, model, year)
        except Exception as exc:
            logger.warning("EbayPartsAdapter error for '%s': %s", part_name, exc)
            return []

    async def _live_search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        from app.adapters.ebay.client import EbayClient
        client = EbayClient()

        query = f"{make} {model} {year} {part_name}"
        params = {
            "q": query,
            "category_ids": EBAY_PARTS_CATEGORY,
            "filter": "itemLocationCountry:GB,deliveryCountry:GB",
            "sort": "price",
            "limit": "10",
        }

        data = await client.get("/item_summary/search", params)
        items = data.get("itemSummaries", [])

        results = []
        for item in items[:10]:
            try:
                base_price_pence = int(float(item["price"]["value"]) * 100)
                shipping_options = item.get("shippingOptions", [])
                if shipping_options:
                    ship_cost = float(shipping_options[0].get("shippingCost", {}).get("value", 0))
                    delivery_pence = int(ship_cost * 100)
                else:
                    delivery_pence = 0

                condition_raw = item.get("condition", "GOOD")
                condition = _CONDITION_MAP.get(condition_raw, "used")

                results.append(PartResult(
                    supplier="eBay",
                    supplier_logo_key="ebay",
                    part_description=item.get("title", part_name)[:200],
                    part_number=None,
                    condition=condition,
                    base_price_pence=base_price_pence,
                    delivery_pence=delivery_pence,
                    total_cost_pence=base_price_pence + delivery_pence,
                    availability="in_stock",
                    url=item.get("itemWebUrl", ""),
                    price_confidence="live",
                ))
            except (KeyError, ValueError, TypeError) as exc:
                logger.debug("EbayPartsAdapter: skipping item due to parse error: %s", exc)
                continue

        results.sort(key=lambda r: r.total_cost_pence)
        return results[:5]
