"""
carparts4less.py

CarParts4Less (carparts4less.co.uk) pricing adapter.
Scrapes product cards from search results.
Delivery: free over £30 (3000p), else £2.99.
Timeout: 5 seconds. Returns empty list on failure.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.adapters.parts.base import BasePartsSupplierAdapter
from app.schemas.parts_pricing import PartResult

logger = logging.getLogger(__name__)

CP4L_BASE = "https://www.carparts4less.co.uk"
CP4L_PAID_DELIVERY_PENCE = 299  # £2.99
CP4L_FREE_DELIVERY_THRESHOLD_PENCE = 3000  # £30.00
SCRAPER_TIMEOUT = 5.0

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


class CarParts4LessAdapter(BasePartsSupplierAdapter):
    """
    Scrapes carparts4less.co.uk for parts pricing.
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
    ) -> list[PartResult]:
        if not self.VALIDATED:
            logger.debug(
                "CarParts4LessAdapter not yet validated — skipping (returning empty)"
            )
            return []
        try:
            return await self._scrape(part_name, make, model, year)
        except Exception as exc:
            logger.warning("CarParts4LessAdapter error for '%s': %s", part_name, exc)
            return []

    async def _scrape(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        query = f"{part_name} {make} {model}"
        url = f"{CP4L_BASE}/search.aspx?q={query.replace(' ', '+')}"

        async with httpx.AsyncClient(timeout=SCRAPER_TIMEOUT, headers=_HEADERS) as client:
            response = await client.get(url)

        if response.status_code != 200:
            logger.warning("CarParts4LessAdapter: HTTP %d for '%s'", response.status_code, part_name)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        # CP4L uses various product card selectors
        items = (
            soup.select(".product-item")
            or soup.select(".product-card")
            or soup.select(".search-result-item")
        )
        items = items[:3]

        results = []
        for item in items:
            try:
                title_el = item.select_one("h2") or item.select_one("h3") or item.select_one(".product-name")
                title = title_el.get_text(strip=True) if title_el else part_name

                price_el = (
                    item.select_one(".price")
                    or item.select_one(".product-price")
                    or item.select_one("[data-price]")
                )
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if not price_match:
                    continue
                base_price_pence = int(float(price_match.group()) * 100)

                part_num_el = item.select_one(".part-number") or item.select_one("[data-sku]")
                part_number = part_num_el.get_text(strip=True) if part_num_el else None

                link_el = item.select_one("a[href]")
                href = link_el["href"] if link_el else ""
                product_url = href if href.startswith("http") else f"{CP4L_BASE}{href}"

                delivery_pence = (
                    0 if base_price_pence >= CP4L_FREE_DELIVERY_THRESHOLD_PENCE
                    else CP4L_PAID_DELIVERY_PENCE
                )

                results.append(PartResult(
                    supplier="CarParts4Less",
                    supplier_logo_key="carparts4less",
                    part_description=title[:200],
                    part_number=part_number,
                    condition="new",
                    base_price_pence=base_price_pence,
                    delivery_pence=delivery_pence,
                    total_cost_pence=base_price_pence + delivery_pence,
                    availability="in_stock",
                    url=product_url,
                    price_confidence="live",
                ))
            except Exception as exc:
                logger.debug("CarParts4LessAdapter: skipping item: %s", exc)
                continue

        results.sort(key=lambda r: r.total_cost_pence)
        return results[:3]
