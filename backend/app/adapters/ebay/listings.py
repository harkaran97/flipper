"""
eBay Live Listings Adapter

Implements BaseListingsAdapter using the eBay Browse API.
Searches for spares/repair vehicle listings on EBAY_GB.
Only used when EBAY_STUB=false.
"""

import logging

from app.adapters.base import BaseListingsAdapter, RawListing
from app.adapters.ebay.client import EbayClient
from config import settings

logger = logging.getLogger(__name__)


class EbayListingsAdapter(BaseListingsAdapter):
    """Fetches spares/repair vehicle listings from the eBay Browse API."""

    def __init__(self) -> None:
        self._client = EbayClient()

    async def search_listings(self, query: str, filters: dict) -> list[RawListing]:
        """Search eBay for spares/repair vehicle listings."""
        postcode = settings.user_postcode
        params = {
            "q": query or "spares or repair",
            "category_ids": "9801",
            "filter": f"conditionIds:{{7000}},maxDeliveryDistance:{{80|km}},itemLocationCountry:GB",
            "buyerPostalCode": postcode,
            "sort": "newlyListed",
            "limit": "50",
            "fieldgroups": "MATCHING_ITEMS",
        }

        data = await self._client.get("/item_summary/search", params)
        items = data.get("itemSummaries", [])

        listings = []
        for item in items:
            try:
                price_value = item.get("price", {}).get("value", "0")
                listing = RawListing(
                    external_id=item["itemId"],
                    source="ebay",
                    title=item["title"],
                    description=item.get("shortDescription", ""),
                    price_pence=int(float(price_value) * 100),
                    postcode=item.get("itemLocation", {}).get("postalCode", ""),
                    url=item["itemWebUrl"],
                    raw_json=item,
                )
                listings.append(listing)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed eBay item: %s", e)
                continue

        logger.info("eBay Browse API returned %d listings", len(listings))
        return listings
