"""
ebay.py

eBay Parts adapter for the multi-source parts pricing service.
Uses the eBay Browse API, category 33743 (Car Parts & Accessories).
Filters to UK location and delivery only.

Uses stub when PARTS_STUB=true OR EBAY_PARTS_LIVE=false.
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
        if settings.parts_stub or not settings.ebay_parts_live:
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
        """
        Searches eBay Parts & Accessories using compatibility_filter.
        Returns only parts tagged as compatible with the specific vehicle.
        Falls back to keyword search if compatibility search returns 0 results.
        """
        from app.adapters.ebay.client import EbayClient
        client = EbayClient()

        # Primary: compatibility filter search (vehicle-specific)
        results = await self._compatibility_search(
            client, part_name, make, model, year
        )

        # Fallback: keyword search if compatibility returns nothing
        # This handles cases where sellers haven't tagged compatibility,
        # which is common for older/rarer vehicles
        if not results:
            logger.info(
                "EbayPartsAdapter: compatibility search returned 0 for '%s' "
                "%s %s %d — falling back to keyword search",
                part_name, make, model, year,
            )
            results = await self._keyword_search(client, part_name, make, model)

        results.sort(key=lambda r: r.total_cost_pence)
        return results[:5]

    async def _compatibility_search(
        self,
        client,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        """
        Uses eBay compatibility_filter to find vehicle-specific parts.
        Only fires when make, model, and year are all known.
        Returns empty list if vehicle data insufficient or API returns nothing.
        """
        # Skip compatibility search if vehicle data is incomplete
        if (
            not make or make.lower() == "unknown"
            or not model or model.lower() == "unknown"
            or not year or year < 1990
        ):
            logger.debug(
                "EbayPartsAdapter: skipping compatibility search — "
                "insufficient vehicle data (make=%s model=%s year=%s)",
                make, model, year,
            )
            return []

        compatibility_filter = f"Year:{year},Make:{make},Model:{model}"

        params = {
            "q": part_name,
            "category_ids": EBAY_PARTS_CATEGORY,
            "compatibility_filter": compatibility_filter,
            "filter": "itemLocationCountry:GB,deliveryCountry:GB",
            "sort": "price",
            "limit": "10",
        }

        try:
            data = await client.get("/item_summary/search", params)
            items = data.get("itemSummaries", [])
            logger.info(
                "EbayPartsAdapter: compatibility search '%s' for %s %s %d "
                "returned %d results",
                part_name, make, model, year, len(items),
            )
            return self._parse_items(items, part_name)
        except Exception as exc:
            logger.warning(
                "EbayPartsAdapter: compatibility search failed for '%s': %s",
                part_name, exc,
            )
            return []

    async def _keyword_search(
        self,
        client,
        part_name: str,
        make: str,
        model: str,
    ) -> list[PartResult]:
        """
        Fallback keyword search when compatibility search returns nothing.
        Less precise but catches listings where sellers haven't tagged compatibility.
        """
        query = f"{part_name} {make} {model}".strip()

        params = {
            "q": query,
            "category_ids": EBAY_PARTS_CATEGORY,
            "filter": "itemLocationCountry:GB,deliveryCountry:GB",
            "sort": "price",
            "limit": "10",
        }

        try:
            data = await client.get("/item_summary/search", params)
            items = data.get("itemSummaries", [])
            logger.info(
                "EbayPartsAdapter: keyword search '%s' returned %d results",
                query, len(items),
            )
            return self._parse_items(items, part_name)
        except Exception as exc:
            logger.warning(
                "EbayPartsAdapter: keyword search failed for '%s': %s",
                query, exc,
            )
            return []

    def _parse_items(self, items: list[dict], part_name: str) -> list[PartResult]:
        """
        Parses eBay item summaries into PartResult objects.
        Skips items with missing price data. Never raises.
        """
        results = []
        for item in items:
            try:
                base_price_pence = int(
                    float(item["price"]["value"]) * 100
                )
                shipping_options = item.get("shippingOptions", [])
                if shipping_options:
                    ship_cost = float(
                        shipping_options[0]
                        .get("shippingCost", {})
                        .get("value", 0)
                    )
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
                logger.debug(
                    "EbayPartsAdapter: skipping item due to parse error: %s", exc
                )
                continue
        return results
