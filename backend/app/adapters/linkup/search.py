import asyncio
import logging
from datetime import date

from app.adapters.base import SearchResult
from app.adapters.linkup.client import get_client

logger = logging.getLogger(__name__)


def build_linkup_query(
    make: str,
    model: str,
    year: int,
    trim: str,
    fuel_type: str,
    write_off: str,
) -> str:
    vehicle_parts = [p for p in [
        str(year) if year and year > 2000 else None,
        make if make and make.lower() != "unknown" else None,
        model if model and model.lower() != "unknown" else None,
        trim if trim and trim.lower() not in ("unknown", "none") else None,
        fuel_type if fuel_type else None,
    ] if p]
    vehicle_str = " ".join(vehicle_parts)

    write_off_note = ""
    if write_off and write_off not in ("clean", "unknown_writeoff"):
        write_off_note = f" (Category {write_off} write-off)"

    return (
        f"What is the current UK market value of a {vehicle_str}{write_off_note}? "
        f"Search AutoTrader UK, PistonHeads, eBay Motors UK completed listings, "
        f"and BCA/Manheim auction results. "
        f"Return only SOLD prices in GBP from the last 6 months. "
        f"Exclude listings with no sale price. "
        f"Provide: median sold price, price range low, price range high, sample count."
    )


async def search_market_value(
    make: str,
    model: str,
    year: int,
    write_off_label: str,
    fuel_type: str | None = None,
    trim: str | None = None,
    engine_cc: int | None = None,
) -> SearchResult:
    query = build_linkup_query(
        make=make,
        model=model,
        year=year,
        trim=trim or "",
        fuel_type=fuel_type or "",
        write_off=write_off_label or "",
    )
    schema = '{"type":"object","properties":{"median_sold_price_gbp":{"type":"number"},"price_range_low_gbp":{"type":"number"},"price_range_high_gbp":{"type":"number"},"sample_count":{"type":"integer"}},"required":["median_sold_price_gbp","price_range_low_gbp","price_range_high_gbp","sample_count"]}'

    logger.info(
        f"[LINKUP] Querying: query='{query}' depth=standard "
        f"make={make} model={model} year={year} trim={trim}"
    )

    client = get_client()
    raw_response = await asyncio.to_thread(
        client.search,
        query=query,
        depth="standard",
        output_type="structured",
        structured_output_schema=schema,
    )

    if raw_response and raw_response.get("median_sold_price_gbp"):
        logger.info(
            f"[LINKUP] Response: median=£{raw_response.get('median_sold_price_gbp')} "
            f"low=£{raw_response.get('price_range_low_gbp')} "
            f"high=£{raw_response.get('price_range_high_gbp')} "
            f"sample_count={raw_response.get('sample_count')}"
        )
    else:
        logger.warning(
            f"[LINKUP] Empty/invalid response for query='{query}' — "
            f"raw={raw_response}"
        )

    return SearchResult(query=query, summary="", structured_data=raw_response)
