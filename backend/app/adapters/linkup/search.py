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

    vehicle_parts = []
    if make and make.lower() != "unknown":
        vehicle_parts.append(make)
    if model and model.lower() != "unknown":
        vehicle_parts.append(model)
    if year and year > 2000:
        vehicle_parts.insert(0, str(year))

    spec_parts = []
    if trim and trim.lower() not in ("unknown", "none"):
        spec_parts.append(trim)
    if fuel_type:
        spec_parts.append(fuel_type)
    if engine_cc:
        spec_parts.append(f"{engine_cc}cc")
    spec_str = " ".join(spec_parts)

    vehicle_str = " ".join(vehicle_parts)
    query = (
        f"You are a UK car market analyst. Find recent sold prices for a "
        f"{vehicle_str} {spec_str}{label_part} in the UK as of {current_month_year}. "
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
