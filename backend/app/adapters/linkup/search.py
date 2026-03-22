import asyncio
from datetime import date

from app.adapters.base import SearchResult
from app.adapters.linkup.client import get_client


async def search_market_value(
    make: str,
    model: str,
    year: int,
    write_off_category: str,
) -> SearchResult:
    current_month_year = date.today().strftime("%B %Y")
    label_part = f" {write_off_category}" if write_off_category else ""
    query = f"What do {year} {make} {model}{label_part} cars typically sell for in the UK as of {current_month_year}? Find recent sold prices from eBay, AutoTrader, and car auction sites."
    schema = '{"type":"object","properties":{"median_sold_price_gbp":{"type":"number"},"price_range_low_gbp":{"type":"number"},"price_range_high_gbp":{"type":"number"},"sample_count":{"type":"integer"}},"required":["median_sold_price_gbp","price_range_low_gbp","price_range_high_gbp"]}'
    client = get_client()
    response = await asyncio.to_thread(
        client.search,
        q=query,
        depth="standard",
        output_type="structured",
        structured_output_schema=schema,
    )
    return SearchResult(query=query, summary="", structured_data=response.output)
