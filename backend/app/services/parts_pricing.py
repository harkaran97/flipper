"""
parts_pricing.py

Multi-source parts pricing service.

Queries eBay, Autodoc, GSF, CarParts4Less, and car-parts.co.uk in parallel.
Aggregates, deduplicates, sorts by total cost, and caches results 24hrs.

Cache key: "{part_name_slug}_{make}_{model}_{year_band}"
e.g. "clutch_kit_bmw_320d_2010s"

Adapter failures are silent — the service returns results from working adapters.
If all adapters fail, returns an empty PartsPricingResult (never raises).
"""
import asyncio
import logging
import re
import statistics
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.parts.autodoc import AutodocAdapter
from app.adapters.parts.car_parts import CarPartsAdapter
from app.adapters.parts.carparts4less import CarParts4LessAdapter
from app.adapters.parts.ebay import EbayPartsAdapter
from app.adapters.parts.gsf import GSFAdapter
from app.adapters.parts.stub import StubPartsAdapter
from app.models.parts_price_cache import PartsPriceCache
from app.schemas.parts_pricing import PartResult, PartsPricingResult
from config import settings

logger = logging.getLogger(__name__)


class PartsPricingService:
    """
    Aggregates parts pricing from multiple UK suppliers.
    Cache-first: results cached 24hrs by (part_name, make, model, year_band).
    """

    def __init__(self) -> None:
        if settings.parts_stub:
            stub = StubPartsAdapter()
            self.ebay_adapter = stub
            self.autodoc_adapter = stub
            self.gsf_adapter = stub
            self.carparts4less_adapter = stub
            self.carparts_adapter = stub
            logger.info("[PARTS] Running in STUB mode — all adapters returning fake data")
        else:
            self.ebay_adapter = EbayPartsAdapter()
            self.autodoc_adapter = AutodocAdapter()
            self.gsf_adapter = GSFAdapter()
            self.carparts4less_adapter = CarParts4LessAdapter()
            self.carparts_adapter = CarPartsAdapter()

            active = ["eBay"] if settings.ebay_parts_live else []
            inactive = ["Autodoc", "GSF", "CarParts4Less", "car-parts.co.uk"]
            # Any with VALIDATED=True move to active
            logger.info(
                "[PARTS] Live mode — active adapters: %s | "
                "stubbed/unvalidated: %s",
                active or "none yet",
                inactive,
            )

        self._ttl_hours: int = settings.parts_cache_ttl_hours

    async def get_prices(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
        postcode: str = "LE4 8JF",
        session: AsyncSession | None = None,
    ) -> PartsPricingResult:
        """
        Returns sorted list of parts pricing from all available suppliers.

        Args:
            part_name: The part to search for (e.g. "clutch kit")
            make: Vehicle make (e.g. "BMW")
            model: Vehicle model (e.g. "320d")
            year: Vehicle year (e.g. 2015)
            postcode: Buyer postcode for delivery context (default Ketan's location)
            session: SQLAlchemy async session (optional; if None, cache is skipped)

        Returns:
            PartsPricingResult with results sorted by total_cost_pence ASC
        """
        cache_key = self._build_cache_key(part_name, make, model, year)

        # 1. Cache check
        if session is not None:
            cached = await self._get_cached(session, cache_key)
            if cached is not None:
                logger.debug("Parts price cache hit: %s", cache_key)
                return cached

        # 2. Run all adapters in parallel — never raise
        logger.info("Parts pricing query: %s for %s %s %d", part_name, make, model, year)
        raw_results = await asyncio.gather(
            self.ebay_adapter.search(part_name, make, model, year),
            self.autodoc_adapter.search(part_name, make, model, year),
            self.gsf_adapter.search(part_name, make, model, year),
            self.carparts4less_adapter.search(part_name, make, model, year),
            self.carparts_adapter.search(part_name, make, model, year),
            return_exceptions=True,
        )

        # 3. Flatten, log exceptions, skip them
        all_parts: list[PartResult] = []
        for result in raw_results:
            if isinstance(result, Exception):
                logger.warning("Parts adapter raised exception: %s", result)
                continue
            all_parts.extend(result)

        # 4. Deduplicate by (supplier, part_number) — keep cheapest
        filtered = self._filter_and_deduplicate(all_parts)

        # 5. Sort by total cost ascending
        sorted_parts = sorted(filtered, key=lambda x: x.total_cost_pence)

        cheapest = sorted_parts[0].total_cost_pence if sorted_parts else None
        now_iso = datetime.utcnow().isoformat()

        pricing_result = PartsPricingResult(
            part_name=part_name,
            results=sorted_parts,
            cheapest_pence=cheapest,
            sourced_at=now_iso,
            cache_hit=False,
        )

        # 6. Cache results (only when session is provided)
        if session is not None:
            await self._cache_results(session, cache_key, pricing_result)

        return pricing_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_cache_key(self, part_name: str, make: str, model: str, year: int) -> str:
        """Builds a normalised cache key from part + vehicle info."""
        year_band = f"{(year // 10) * 10}s"  # 2015 → "2010s"
        slug = re.sub(r"[^a-z0-9]", "_", part_name.lower().strip())
        make_s = re.sub(r"[^a-z0-9]", "_", make.lower().strip())
        model_s = re.sub(r"[^a-z0-9]", "_", model.lower().strip())
        return f"{slug}_{make_s}_{model_s}_{year_band}"

    def _filter_and_deduplicate(self, parts: list[PartResult]) -> list[PartResult]:
        """
        Removes duplicates by (supplier, part_number).
        When two entries share the same key, keeps the cheaper one.
        Entries with no part_number are kept as-is (breakers, eBay).
        """
        seen: dict[tuple, PartResult] = {}
        no_number: list[PartResult] = []

        for part in parts:
            if part.part_number:
                key = (part.supplier.lower(), part.part_number.lower())
                existing = seen.get(key)
                if existing is None or part.total_cost_pence < existing.total_cost_pence:
                    seen[key] = part
            else:
                no_number.append(part)

        return list(seen.values()) + no_number

    async def _get_cached(
        self,
        session: AsyncSession,
        cache_key: str,
    ) -> PartsPricingResult | None:
        """Returns cached PartsPricingResult if found and not expired."""
        result = await session.execute(
            select(PartsPriceCache).where(PartsPriceCache.cache_key == cache_key)
        )
        row = result.scalar_one_or_none()
        if row is None or not row.is_valid:
            return None

        try:
            data = row.results_json
            results = [PartResult(**r) for r in data.get("results", [])]
            return PartsPricingResult(
                part_name=data["part_name"],
                results=results,
                cheapest_pence=data.get("cheapest_pence"),
                sourced_at=data.get("sourced_at", ""),
                cache_hit=True,
            )
        except Exception as exc:
            logger.warning("Parts cache deserialise error for key %s: %s", cache_key, exc)
            return None

    async def _cache_results(
        self,
        session: AsyncSession,
        cache_key: str,
        pricing_result: PartsPricingResult,
    ) -> None:
        """Upserts a cache entry with TTL = now + parts_cache_ttl_hours."""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=self._ttl_hours)
            serialised = {
                "part_name": pricing_result.part_name,
                "results": [r.model_dump() for r in pricing_result.results],
                "cheapest_pence": pricing_result.cheapest_pence,
                "sourced_at": pricing_result.sourced_at,
            }

            existing = await session.execute(
                select(PartsPriceCache).where(PartsPriceCache.cache_key == cache_key)
            )
            row = existing.scalar_one_or_none()
            if row is None:
                session.add(PartsPriceCache(
                    cache_key=cache_key,
                    results_json=serialised,
                    expires_at=expires_at,
                ))
            else:
                row.results_json = serialised
                row.created_at = datetime.utcnow()
                row.expires_at = expires_at

            await session.flush()
        except Exception as exc:
            logger.warning("Parts cache write failed for key %s: %s", cache_key, exc)

    def compute_median_total_pence(self, result: PartsPricingResult) -> int | None:
        """Returns median total_cost_pence across all results, or None if empty."""
        if not result.results:
            return None
        prices = [r.total_cost_pence for r in result.results]
        return int(statistics.median(prices))
