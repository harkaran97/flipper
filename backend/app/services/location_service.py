"""
location_service.py

ALL postcode lookups go through this module. No exceptions.
Turns an eBay item postcode (usually masked to its outward code, e.g. "LE4****")
into a distance in miles from the user's postcode.

Coordinates come from postcodes.io (free, no API key) and are cached in memory
for the life of the process. When EBAY_STUB=true, built-in coordinates are used
and no network call is made. Any failure returns None — a missing distance must
never block ingestion.
"""
import logging
import math
import re
import time

import httpx

from config import settings

logger = logging.getLogger(__name__)

POSTCODES_IO_BASE = "https://api.postcodes.io"
_EARTH_RADIUS_MILES = 3958.8
_OUTWARD_RE = re.compile(r"^([A-Z]{1,2}\d[A-Z\d]?)")
_FULL_NO_SPACE_RE = re.compile(r"^([A-Z]{1,2}\d[A-Z\d]?)\d[A-Z]{2}$")
_RETRY_AFTER_FAILURE_SECONDS = 3600

# Outward-code centroids used in stub mode (approximate, for tests and local runs).
STUB_COORDINATES: dict[str, tuple[float, float]] = {
    "LE4": (52.6620, -1.1180),
    "LE1": (52.6350, -1.1330),
    "B15": (52.4680, -1.9200),
    "M4": (53.4840, -2.2300),
    "LS1": (53.7970, -1.5480),
    "CV1": (52.4080, -1.5100),
    "NG1": (52.9540, -1.1500),
}

_cache: dict[str, tuple[float, float] | None] = {}
_failed_at: dict[str, float] = {}


def outward_code(postcode: str | None) -> str | None:
    """Return the outward code ("LE4") from a full, partial or masked postcode."""
    if not postcode:
        return None
    cleaned = postcode.upper().replace("*", "").strip()
    first = cleaned.split(" ")[0]
    full = _FULL_NO_SPACE_RE.match(first)
    if full:
        return full.group(1)
    m = _OUTWARD_RE.match(first)
    return m.group(1) if m else None


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in miles between two (lat, lon) points."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


async def _lookup_outcode(outcode: str) -> tuple[float, float] | None:
    """Return (lat, lon) for an outward code, cached; stub coordinates in stub mode."""
    if outcode in _cache:
        return _cache[outcode]
    # After a network failure, don't retry this outcode for an hour — a down
    # postcodes.io must not add a timeout to every listing in a poll.
    failed_at = _failed_at.get(outcode)
    if failed_at is not None and time.monotonic() - failed_at < _RETRY_AFTER_FAILURE_SECONDS:
        return None

    if settings.ebay_stub:
        coords = STUB_COORDINATES.get(outcode)
    else:
        coords = None
        try:
            async with httpx.AsyncClient(timeout=settings.scraper_timeout_seconds) as client:
                response = await client.get(f"{POSTCODES_IO_BASE}/outcodes/{outcode}")
            if response.status_code == 200:
                result = response.json().get("result") or {}
                if result.get("latitude") is not None and result.get("longitude") is not None:
                    coords = (float(result["latitude"]), float(result["longitude"]))
            elif response.status_code != 404:
                # Transient (5xx, 429): retry later rather than caching "unknown"
                logger.warning(
                    "[LOCATION] postcodes.io returned %d for outcode %s",
                    response.status_code, outcode,
                )
                _failed_at[outcode] = time.monotonic()
                return None
        except Exception as exc:
            logger.warning("[LOCATION] Lookup failed for outcode %s — %s", outcode, exc)
            _failed_at[outcode] = time.monotonic()
            return None

    _cache[outcode] = coords
    return coords


async def distance_from_user_miles(postcode: str | None) -> float | None:
    """Distance in miles from settings.user_postcode to the given postcode, or None."""
    listing_outcode = outward_code(postcode)
    user_outcode = outward_code(settings.user_postcode)
    if not listing_outcode or not user_outcode:
        return None

    listing_coords = await _lookup_outcode(listing_outcode)
    user_coords = await _lookup_outcode(user_outcode)
    if listing_coords is None or user_coords is None:
        return None

    return round(haversine_miles(user_coords, listing_coords), 1)
