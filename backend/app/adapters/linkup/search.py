import asyncio

from app.adapters.base import SearchResult
from app.adapters.linkup.client import get_client


async def search_fault_intelligence(
    make: str,
    model: str,
    year: int,
    fault_type: str,
) -> SearchResult:
    query = f"{make} {model} {year} {fault_type} repair cost common problem UK"
    client = get_client()
    response = await asyncio.to_thread(
        client.search,
        q=query,
        depth="standard",
        output_type="sourcedAnswer",
    )
    sources = [s.url for s in (response.sources or [])]
    return SearchResult(query=query, summary=response.answer, sources=sources)


async def search_market_value(
    make: str,
    model: str,
    year: int,
    write_off_category: str,
) -> SearchResult:
    label_part = f" {write_off_category}" if write_off_category else ""
    query = f"{make} {model} {year}{label_part} sold price UK"
    client = get_client()
    response = await asyncio.to_thread(
        client.search,
        q=query,
        depth="standard",
        output_type="sourcedAnswer",
    )
    sources = [s.url for s in (response.sources or [])]
    return SearchResult(query=query, summary=response.answer, sources=sources)
