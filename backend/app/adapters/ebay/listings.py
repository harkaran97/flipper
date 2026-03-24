"""
eBay Live Listings Adapter

Implements BaseListingsAdapter using the eBay Browse API.
Searches for spares/repair vehicle listings on EBAY_GB.
Only used when EBAY_STUB=false.
"""

import logging
import re
from html.parser import HTMLParser

from app.adapters.base import BaseListingsAdapter, RawListing
from app.adapters.ebay.client import EbayClient
from config import settings

logger = logging.getLogger(__name__)

# Common UK car makes for title-based fallback parsing
_UK_CAR_MAKES = [
    "BMW", "Ford", "Vauxhall", "Volkswagen", "VW", "Audi", "Toyota", "Honda",
    "Nissan", "Peugeot", "Renault", "Citroen", "Skoda", "Seat", "Kia",
    "Hyundai", "Mazda", "Volvo", "Land Rover", "Range Rover", "Mini", "Fiat",
    "Alfa Romeo", "Mercedes", "Jaguar", "Subaru", "Suzuki", "Mitsubishi",
    "Dacia", "MG",
]

# Normalise VW → Volkswagen for consistency
_MAKE_ALIASES = {"VW": "Volkswagen"}


WRITEOFF_ASPECT_NAMES = {
    "insurance write-off category",
    "write-off category",
    "insurance category",
    "salvage category",
}

WRITEOFF_ASPECT_VALUES_EXCLUDE = {
    "cat a", "cat b", "cat c", "cat d",
    "cat s", "cat n",
    "category a", "category b", "category c", "category d",
    "category s", "category n",
    "a", "b", "c", "d", "s", "n",  # shorthand values some sellers use
}


def extract_writeoff_from_aspects(localized_aspects: list) -> str | None:
    """
    Returns the write-off category string if declared in eBay item specifics.
    Returns None if no write-off aspect found (assume clean).
    """
    if not localized_aspects:
        return None

    for aspect in localized_aspects:
        name = aspect.get('name', '').lower().strip()
        value = aspect.get('value', '').lower().strip()

        if name in WRITEOFF_ASPECT_NAMES:
            if value in WRITEOFF_ASPECT_VALUES_EXCLUDE:
                return value  # declared write-off — exclude
            if value in ('none', 'no', 'clean', 'not a write-off', ''):
                return None   # explicitly clean

    return None  # aspect not present — assume clean, keyword check handles the rest


class _HTMLStripper(HTMLParser):
    """Simple HTML tag stripper for seller descriptions."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(part.strip() for part in self._parts if part.strip())


def _parse_engine_cc(value: str) -> int | None:
    """Convert engine size strings like '1998cc' or '2.0L' to integer cc."""
    value = value.strip()
    # Match patterns like "1998cc", "1998 cc", "1998 CC"
    m = re.search(r"(\d+)\s*cc", value, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Match patterns like "2.0L", "2.0 L", "2.0 litre"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:L|litre|liter)", value, re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 1000)
    return None


def _parse_mileage(value: str) -> int | None:
    """Strip commas and parse mileage string to int."""
    cleaned = re.sub(r"[,\s]", "", value)
    m = re.search(r"(\d+)", cleaned)
    return int(m.group(1)) if m else None


def extract_description(item: dict) -> str | None:
    """
    Extract and clean the seller description from a full eBay item dict.

    Strips HTML tags to plain text. Returns None if no description present.
    """
    raw = item.get("description")
    if not raw:
        return None
    stripper = _HTMLStripper()
    stripper.feed(raw)
    text = stripper.get_text()
    return text if text else None


def extract_vehicle_from_item(item: dict) -> tuple[dict, list[str]]:
    """
    Extract vehicle fields from an eBay item dict.

    Attempts to parse localizedAspects first (trusted structured data);
    falls back to title heuristics for make/model/year when aspects are
    absent or incomplete.

    Returns:
        (vehicle_dict, missing_fields) where missing_fields is a list of
        field names that were not obtainable from eBay structured data and
        should be inferred by AI from title + description.
    """
    title = item.get("title", "")
    aspects = item.get("localizedAspects", [])

    # Build a case-insensitive lookup from aspect name → value
    aspect_map: dict[str, str] = {}
    for aspect in aspects:
        name = aspect.get("name", "").strip().lower()
        value = aspect.get("value", "").strip()
        if name and value:
            aspect_map[name] = value

    def get_aspect(*names: str) -> str | None:
        for name in names:
            val = aspect_map.get(name.lower())
            if val:
                return val
        return None

    make = get_aspect("make")
    model = get_aspect("model")
    year_str = get_aspect("year", "registration year")
    fuel_type = get_aspect("fuel type", "engine")
    engine_str = get_aspect("engine size")
    transmission = get_aspect("transmission")
    mileage_str = get_aspect("mileage", "vehicle mileage")
    body_type = get_aspect("body type", "body style")
    colour = get_aspect("colour", "color", "exterior colour", "exterior color")

    # Parse year
    year: int = 0
    if year_str:
        m = re.search(r"(20\d{2}|19\d{2})", year_str)
        if m:
            year = int(m.group(1))

    # Parse engine cc
    engine_cc: int | None = None
    if engine_str:
        engine_cc = _parse_engine_cc(engine_str)

    # Parse mileage
    mileage: int | None = None
    if mileage_str:
        mileage = _parse_mileage(mileage_str)
    if mileage and mileage > 500000:
        logger.warning(
            "[INGESTION] Implausible mileage %d — ignoring (raw=%r)",
            mileage, mileage_str,
        )
        mileage = None

    # Fallback: extract make/model/year from title when aspects incomplete
    if not make or not model or not year:
        make, model, year = _parse_from_title(title, make, model, year)

    # Normalise make aliases
    if make:
        make = _MAKE_ALIASES.get(make.upper(), make)

    # Track which fields are present vs missing AFTER all extraction
    # (aspects + title heuristics). This reflects what AI actually needs to infer.
    _from_specifics: list[str] = []
    _missing: list[str] = []

    for field_name, final_val in [
        ("make", make if make and make != "Unknown" else None),
        ("model", model if model and model != "Unknown" else None),
        ("year", year or None),
        ("engine_cc", engine_cc),
        ("mileage", mileage),
        ("fuel_type", fuel_type),
        ("transmission", transmission),
        ("body_type", body_type),
    ]:
        if final_val:
            _from_specifics.append(field_name)
        else:
            _missing.append(field_name)

    logger.info(
        "[INGESTION] eBay specifics: make=%s model=%s year=%s engine_cc=%s mileage=%s fuel=%s "
        "transmission=%s body_type=%s — missing: %s",
        make, model, year or None, engine_cc, mileage, fuel_type,
        transmission, body_type,
        ", ".join(_missing) if _missing else "none",
    )

    vehicle_dict = {
        "make": make or "Unknown",
        "model": model or "Unknown",
        "year": year or 0,
        "fuel_type": fuel_type,
        "engine_cc": engine_cc,
        "transmission": transmission,
        "mileage": mileage,
        "body_type": body_type,
        "colour": colour,
    }
    return vehicle_dict, _missing


def _parse_from_title(
    title: str,
    existing_make: str | None,
    existing_model: str | None,
    existing_year: int,
) -> tuple[str | None, str | None, int]:
    """Heuristic extraction of make/model/year from a listing title."""
    make = existing_make
    model = existing_model
    year = existing_year

    # Extract year (4-digit, 2000–2025)
    if not year:
        m = re.search(r"\b(20(?:0[0-9]|1[0-9]|2[0-5]))\b", title)
        if m:
            year = int(m.group(1))

    # Extract make from hardcoded list (longest match first to prefer "Land Rover" over "Land")
    if not make:
        title_upper = title.upper()
        for candidate in sorted(_UK_CAR_MAKES, key=len, reverse=True):
            if candidate.upper() in title_upper:
                make = candidate
                break

    # Extract model: first word after make that isn't a year
    if make and not model:
        pattern = re.escape(make)
        m = re.search(pattern + r"\s+(\S+)", title, re.IGNORECASE)
        if m:
            word = m.group(1)
            if not re.match(r"^(20\d{2}|19\d{2})$", word):
                model = word

    return make, model, year


class EbayListingsAdapter(BaseListingsAdapter):
    """Fetches spares/repair vehicle listings from the eBay Browse API."""

    def __init__(self) -> None:
        self._client = EbayClient()

    async def fetch_item(self, item_id: str) -> dict:
        """Fetch full item data for a single eBay listing."""
        return await self._client.get_item(item_id)

    async def search_listings(self, query: str, filters: dict) -> list[RawListing]:
        """Search eBay for used vehicle listings — broad fetch, no keyword restriction."""
        postcode = settings.user_postcode
        min_price = settings.min_price_pence // 100
        max_price = settings.max_price_pence // 100
        params = {
            "category_ids": "9801",
            "filter": (
                f"conditionIds:{{2500|3000|4000|5000|6000|7000}},"
                f"price:[{min_price}..{max_price}],"
                f"itemLocationCountry:GB,"
                f"maxDeliveryDistance:{{80|km}}"
            ),
            "buyerPostalCode": postcode,
            "sort": "newlyListed",
            "limit": "50",
            "fieldgroups": "MATCHING_ITEMS",
        }

        data = await self._client.get("/item_summary/search", params)
        items = data.get("itemSummaries", [])

        listings = []
        for item in items:
            try:
                price_value = item.get("price", {}).get("value", "0")
                listing = RawListing(
                    external_id=item["itemId"],
                    source="ebay",
                    title=item["title"],
                    description=item.get("shortDescription", ""),
                    price_pence=int(float(price_value) * 100),
                    postcode=item.get("itemLocation", {}).get("postalCode", ""),
                    url=item["itemWebUrl"],
                    raw_json=item,
                )
                listings.append(listing)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed eBay item: %s", e)
                continue

        logger.info("eBay Browse API returned %d listings", len(listings))
        return listings
