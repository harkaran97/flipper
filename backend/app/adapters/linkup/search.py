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
    query = (
        f"You are a UK car market analyst. Find recent sold prices for a {year} {make} {model}{label_part} "
        f"in the UK as of {current_month_year}. "
        f" Search these UK sources: eBay Motors UK completed listings, AutoTrader UK, PistonHeads, "
        f"BCA/Manheim auction results. "
        f" Extract sold prices only (not asking prices). UK sales only. Exclude non-GBP listings."
    )
    schema = '{"type":"object","properties":{"median_sold_price_gbp":{"type":"number"},"price_range_low_gbp":{"type":"number"},"price_range_high_gbp":{"type":"number"},"sample_count":{"type":"integer"}},"required":["median_sold_price_gbp","price_range_low_gbp","price_range_high_gbp"]}'
    client = get_client()
    response = await asyncio.to_thread(
        client.search,
        query=query,
        depth="standard",
        output_type="structured",
        structured_output_schema=schema,
    )
    return SearchResult(query=query, summary="", structured_data=response)
