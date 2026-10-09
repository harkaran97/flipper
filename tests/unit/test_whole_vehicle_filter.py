"""
test_whole_vehicle_filter.py

Unit tests for TASK_040 — parts listings and out-of-band prices never reach the
pipeline.

Run from backend/ directory:
    python -m pytest ../tests/unit/test_whole_vehicle_filter.py -v
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.adapters.base import RawListing
from app.adapters.ebay.listings import EbayListingsAdapter, has_vehicle_aspects
from app.workers import ingestion_worker


def test_no_year_or_mileage_is_not_a_whole_vehicle():
    assert has_vehicle_aspects([]) is False
    assert has_vehicle_aspects([{"name": "Brand", "value": "BMW"}]) is False
    assert has_vehicle_aspects([{"name": "Year", "value": ""}]) is False


def test_year_or_mileage_is_a_whole_vehicle():
    assert has_vehicle_aspects([{"name": "Year", "value": "2015"}]) is True
    assert has_vehicle_aspects([{"name": "Registration Year", "value": "2015"}]) is True
    assert has_vehicle_aspects([{"name": "Mileage", "value": "84,000"}]) is True


class _OneListingAdapter:
    def __init__(self, listing):
        self._listing = listing

    async def search_listings(self, query, filters):
        return [self._listing]


def test_listing_below_price_band_is_dropped_without_touching_the_db():
    wing = RawListing(
        external_id="wing", source="ebay", title="vw golf r mk7.5 wing",
        description="", price_pence=15000, postcode="LE1", url="https://x", raw_json={},
    )
    with patch.object(ingestion_worker.settings, "min_price_pence", 100000):
        # session=None: any DB access would raise, proving the drop happens first
        stats = asyncio.run(ingestion_worker.run_poll_cycle(None, _OneListingAdapter(wing), None))
    assert stats["out_of_price_band"] == 1
    assert stats["passed"] == 0


def test_search_sends_price_currency():
    adapter = EbayListingsAdapter()
    adapter._client.get = AsyncMock(return_value={"itemSummaries": []})
    asyncio.run(adapter.search_listings(query="", filters={}))
    params = adapter._client.get.call_args.args[1]
    assert "priceCurrency:GBP" in params["filter"]
    assert "price:[" in params["filter"]
