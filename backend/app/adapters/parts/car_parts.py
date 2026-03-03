"""
car_parts.py

car-parts.co.uk adapter — used/reconditioned parts from UK breakers yards.
Scrapes breaker listings from car-parts.co.uk.
Condition: always "used" or "reconditioned".
Timeout: 5 seconds. Returns empty list on failure.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

from app.adapters.parts.base import BasePartsSupplierAdapter
from app.schemas.parts_pricing import PartResult

logger = logging.getLogger(__name__)

CAR_PARTS_BASE = "https://www.car-parts.co.uk"
SCRAPER_TIMEOUT = 5.0

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}


def _slugify(text: str) -> str:
    """Convert part name to URL slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


class CarPartsAdapter(BasePartsSupplierAdapter):
    """
    Scrapes car-parts.co.uk for used and reconditioned parts from UK breakers.
    Returns up to 3 results sorted by total cost.
    Falls back to empty list on any error or timeout.
    """

    async def search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        try:
            return await self._scrape(part_name, make, model, year)
        except Exception as exc:
            logger.warning("CarPartsAdapter error for '%s': %s", part_name, exc)
            return []

    async def _scrape(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        part_slug = _slugify(part_name)
        make_slug = _slugify(make)
        model_slug = _slugify(model)
        url = f"{CAR_PARTS_BASE}/parts/{part_slug}/{make_slug}/{model_slug}/{year}/"

        async with httpx.AsyncClient(timeout=SCRAPER_TIMEOUT, headers=_HEADERS) as client:
            response = await client.get(url)

        if response.status_code != 200:
            logger.warning("CarPartsAdapter: HTTP %d for '%s'", response.status_code, part_name)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        items = (
            soup.select(".part-listing")
            or soup.select(".listing-item")
            or soup.select(".result-item")
        )
        items = items[:3]

        results = []
        for item in items:
            try:
                title_el = item.select_one("h2") or item.select_one("h3") or item.select_one(".part-name")
                title = title_el.get_text(strip=True) if title_el else f"Used {part_name}"

                price_el = (
                    item.select_one(".price")
                    or item.select_one(".part-price")
                    or item.select_one("[data-price]")
                )
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
                if not price_match:
                    continue
                base_price_pence = int(float(price_match.group()) * 100)

                delivery_el = item.select_one(".delivery") or item.select_one(".postage")
                if delivery_el:
                    delivery_text = delivery_el.get_text(strip=True)
                    delivery_match = re.search(r"[\d,]+\.?\d*", delivery_text.replace(",", ""))
                    delivery_pence = int(float(delivery_match.group()) * 100) if delivery_match else 0
                else:
                    delivery_pence = 0

                supplier_el = item.select_one(".seller") or item.select_one(".breaker-name")
                supplier_name = supplier_el.get_text(strip=True) if supplier_el else "Breaker"

                link_el = item.select_one("a[href]")
                href = link_el["href"] if link_el else ""
                product_url = href if href.startswith("http") else f"{CAR_PARTS_BASE}{href}"

                # Determine if reconditioned or used from title
                condition = "reconditioned" if "recon" in title.lower() else "used"

                results.append(PartResult(
                    supplier=f"car-parts.co.uk ({supplier_name})",
                    supplier_logo_key="car_parts",
                    part_description=title[:200],
                    part_number=None,
                    condition=condition,
                    base_price_pence=base_price_pence,
                    delivery_pence=delivery_pence,
                    total_cost_pence=base_price_pence + delivery_pence,
                    availability="in_stock",
                    url=product_url,
                    price_confidence="live",
                ))
            except Exception as exc:
                logger.debug("CarPartsAdapter: skipping item: %s", exc)
                continue

        results.sort(key=lambda r: r.total_cost_pence)
        return results[:3]
