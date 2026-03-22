import asyncio
from datetime import date

from app.adapters.base import SearchResult
from app.adapters.linkup.client import get_client


async def search_market_value(
    make: str,
    model: str,
    year: int,
    write_off_label: str,
    fuel_type: str | None = None,
    trim: str | None = None,
    engine_cc: int | None = None,
) -> SearchResult:
    current_month_year = date.today().strftime("%B %Y")
    label_part = f" {write_off_label}" if write_off_label else ""
    spec_parts = list(filter(None, [trim, fuel_type, f"{engine_cc}cc" if engine_cc else None]))
    spec_str = " ".join(spec_parts)
    query = (
        f"You are a UK car market analyst. Find recent sold prices for a "
        f"{year} {make} {model} {spec_str}{label_part} in the UK as of {current_month_year}. "
        f"Search these UK sources: eBay Motors UK completed listings, AutoTrader UK, "
        f"PistonHeads, BCA and Manheim auction results. "
        f"Extract sold prices only, not asking prices. UK sales only. Exclude non-GBP listings."
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
