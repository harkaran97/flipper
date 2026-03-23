"""
autodoc.py

Autodoc (autodoc.co.uk) parts pricing adapter.
Scrapes product listings from Autodoc's search page.
Delivery: £3.99 standard UK — hardcoded.
Timeout: 5 seconds. Returns empty list on failure.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.adapters.parts.base import BasePartsSupplierAdapter
from app.schemas.parts_pricing import PartResult

logger = logging.getLogger(__name__)

AUTODOC_BASE = "https://www.autodoc.co.uk"
AUTODOC_DELIVERY_PENCE = 399  # £3.99
SCRAPER_TIMEOUT = 5.0

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


class AutodocAdapter(BasePartsSupplierAdapter):
    """
    Scrapes autodoc.co.uk for parts pricing.
    Returns up to 3 results sorted by total cost.
    Falls back to empty list on any error or timeout.
    """

    # Not yet validated against live site HTML — returns empty until verified
    VALIDATED = False

    async def search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
        session=None,  # ignored
    ) -> list[PartResult]:
        if not self.VALIDATED:
            logger.debug(
                "AutodocAdapter not yet validated — skipping (returning empty)"
            )
            return []
        try:
            return await self._scrape(part_name, make, model, year)
        except Exception as exc:
            logger.warning("AutodocAdapter error for '%s': %s", part_name, exc)
            return []

    async def _scrape(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        query = f"{part_name} {make} {model} {year}"
        url = f"{AUTODOC_BASE}/search?query={query.replace(' ', '+')}"

        async with httpx.AsyncClient(timeout=SCRAPER_TIMEOUT, headers=_HEADERS) as client:
            response = await client.get(url)

        if response.status_code != 200:
            logger.warning("AutodocAdapter: HTTP %d for '%s'", response.status_code, part_name)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.select(".listing-item")[:3]

        results = []
        for item in items:
            try:
                title_el = item.select_one(".product-title") or item.select_one("h2") or item.select_one("h3")
                title = title_el.get_text(strip=True) if title_el else part_name

                price_el = item.select_one(".product-price__value") or item.select_one(".price")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if not price_match:
                    continue
                base_price_pence = int(float(price_match.group()) * 100)

                part_num_el = item.select_one(".product-number") or item.select_one("[data-art-number]")
                part_number = part_num_el.get_text(strip=True) if part_num_el else None

                link_el = item.select_one("a[href]")
                href = link_el["href"] if link_el else ""
                product_url = href if href.startswith("http") else f"{AUTODOC_BASE}{href}"

                results.append(PartResult(
                    supplier="Autodoc",
                    supplier_logo_key="autodoc",
                    part_description=title[:200],
                    part_number=part_number,
                    condition="new",
                    base_price_pence=base_price_pence,
                    delivery_pence=AUTODOC_DELIVERY_PENCE,
                    total_cost_pence=base_price_pence + AUTODOC_DELIVERY_PENCE,
                    availability="in_stock",
                    url=product_url,
                    price_confidence="live",
                ))
            except Exception as exc:
                logger.debug("AutodocAdapter: skipping item: %s", exc)
                continue

        results.sort(key=lambda r: r.total_cost_pence)
        return results[:3]
