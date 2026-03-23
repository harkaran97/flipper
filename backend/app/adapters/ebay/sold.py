"""
eBay Live Sold Comps Adapter

Implements BaseSoldAdapter using the eBay Browse API.
Searches for completed/sold vehicle listings on EBAY_GB for price benchmarking.
Only used when EBAY_STUB=false.

Note: Full sold price data requires Marketplace Insights API approval.
Fallback: Browse API with conditionIds:{3000} (Used) + soldItems filter.
"""

import logging

from app.adapters.base import BaseSoldAdapter, SoldListing
from app.adapters.ebay.client import EbayClient

logger = logging.getLogger(__name__)

EBAY_MOTORS_CATEGORY = "9801"


class EbaySoldAdapter(BaseSoldAdapter):
    """Fetches sold vehicle comps from the eBay Browse API."""

    def __init__(self) -> None:
        self._client = EbayClient()

    async def search_sold(self, make: str, model: str, year: int) -> list[SoldListing]:
        """
        Search eBay for sold vehicle listings matching make/model/year.
        Uses Browse API with used condition and sold filter.
        Omits Unknown make/model and year=0/implausible from query.
        Returns up to 20 sold comps.
        """
        query_parts = []
        if make and make.lower() != "unknown":
            query_parts.append(make)
        if model and model.lower() != "unknown":
            query_parts.append(model)
        if year and year > 2000:
            query_parts.append(str(year))
        query_str = " ".join(query_parts)

        if not query_str:
            logger.warning("eBay sold comps skipped — no usable vehicle fields (make=%s, model=%s, year=%d)", make, model, year)
            return []

        params = {
            "q": query_str,
            "category_ids": EBAY_MOTORS_CATEGORY,
            "filter": "conditionIds:{3000},soldItems:true",
            "sort": "endTimeSoonest",
            "limit": "20",
        }

        data = await self._client.get("/item_summary/search", params)
        items = data.get("itemSummaries", [])

        listings = []
        for item in items:
            try:
                price_value = item.get("price", {}).get("value", "0")
                listing = SoldListing(
                    title=item["title"],
                    sold_price_pence=int(float(price_value) * 100),
                    year=year,
                    make=make,
                    model=model,
                )
                listings.append(listing)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed eBay sold item: %s", e)
                continue

        logger.info(
            "eBay sold comps returned %d results for query=%r",
            len(listings), query_str,
        )
        return listings
