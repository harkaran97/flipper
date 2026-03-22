"""
repair_estimator.py

Produces repair estimates for a listing.

Logic:
1. Load detected faults for this listing
2. For each fault:
   a. Check fault_cache for a valid TTL entry keyed by
      {make}_{model}_{year_band}_{fault_type} — use cached costs on hit
   b. On miss: look up fault_parts, call PartsPricingService
      (cache-first, multi-source, TTL 24h), write result to fault_cache
   c. Use cheapest_pence for repair_cost_min, median for repair_cost_max
3. Look up labour_days from cars_common_problems (override)
   or common_problems (default)
4. Sum total man days
5. Store RepairEstimate
6. Emit REPAIR_ESTIMATED
"""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.car import Car
from app.models.cars_common_problems import CarsCommonProblem
from app.models.common_problem import CommonProblem
from app.models.fault import DetectedFault, FaultCache
from app.models.fault_part import FaultPart
from app.models.listing import Listing
from app.models.repair_estimate import RepairEstimate
from app.models.vehicle import Vehicle
from app.services.parts_pricing import PartsPricingService
from config import settings

logger = logging.getLogger(__name__)

# Cost ceiling: only search parts prices if listing is below £10,000
_PRICE_CEILING_PENCE = 1_000_000

_parts_pricing_service = PartsPricingService()

_FAULT_CACHE_TTL_DAYS = 30


def _year_band(year: int) -> int:
    """Returns 5-year band start (e.g., 2019 → 2015, 2023 → 2020)."""
    return (year // 5) * 5


def _fault_cache_key(make: str, model: str, year: int, fault_type: str) -> str:
    """Builds fault_cache key: {make}_{model}_{year_band}_{fault_type}."""
    return f"{make.lower()}_{model.lower()}_{_year_band(year)}_{fault_type}"


def _is_cache_valid(entry: FaultCache) -> bool:
    """Returns True if the cache entry is within its TTL."""
    return datetime.utcnow() < entry.created_at + timedelta(days=entry.ttl_days)


async def _read_fault_cache(
    session: AsyncSession, cache_key: str
) -> FaultCache | None:
    """Returns a valid (non-expired) FaultCache entry, or None on miss/expiry."""
    result = await session.execute(
        select(FaultCache).where(FaultCache.cache_key == cache_key)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None
    if not _is_cache_valid(entry):
        logger.info(
            "[ESTIMATOR] fault_cache EXPIRED for key=%r (created=%s ttl=%dd)",
            cache_key, entry.created_at, entry.ttl_days,
        )
        return None
    return entry


async def _write_fault_cache(
    session: AsyncSession,
    cache_key: str,
    repair_min_pence: int,
    repair_max_pence: int,
) -> None:
    """
    Upserts repair cost data into fault_cache under cache_key.
    Resets created_at on update so the TTL window slides forward.
    """
    result = await session.execute(
        select(FaultCache).where(FaultCache.cache_key == cache_key)
    )
    entry = result.scalar_one_or_none()
    if entry is not None:
        entry.repair_min_pence = repair_min_pence
        entry.repair_max_pence = repair_max_pence
        entry.created_at = datetime.utcnow()
        logger.info("[ESTIMATOR] fault_cache UPDATED for key=%r", cache_key)
    else:
        session.add(FaultCache(
            cache_key=cache_key,
            repair_min_pence=repair_min_pence,
            repair_max_pence=repair_max_pence,
            ttl_days=_FAULT_CACHE_TTL_DAYS,
        ))
        logger.info("[ESTIMATOR] fault_cache CREATED for key=%r", cache_key)
    await session.flush()


async def estimate_repairs(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus,
) -> None:
    """
    Full repair estimation pipeline for one listing.
    1. Load listing + vehicle + detected faults
    2. For each fault → check fault_cache; on hit use cached costs directly
    3. On miss → get parts list from fault_parts, call PartsPricingService,
       write result back to fault_cache (TTL 30 days)
    4. Sum parts cost (cheapest for min, median for max) + man days
    5. Store RepairEstimate
    6. Emit REPAIR_ESTIMATED
    """
    # Load listing
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None:
        logger.error("estimate_repairs: listing %s not found", listing_id)
        return

    # Load vehicle
    result = await session.execute(select(Vehicle).where(Vehicle.listing_id == listing_id))
    vehicle = result.scalar_one_or_none()
    if vehicle is None:
        logger.warning("estimate_repairs: no vehicle for listing %s — skipping", listing_id)
        return

    # Load detected faults
    result = await session.execute(
        select(DetectedFault).where(DetectedFault.listing_id == listing_id)
    )
    faults = result.scalars().all()
    if not faults:
        logger.info(
            "estimate_repairs: no detected faults for listing %s — emitting zero estimate",
            listing_id,
        )

    # Resolve car_id for labour days lookup
    car_id = await _resolve_car_id(session, vehicle)

    total_parts_min = 0
    total_parts_max = 0
    total_man_days = 0.0
    unpriced_fault_types: list[str] = []

    for fault in faults:
        fault_type = fault.issue

        # Check fault_cache before calling PartsPricingService
        fc_key = _fault_cache_key(vehicle.make, vehicle.model, vehicle.year, fault_type)
        cache_entry = await _read_fault_cache(session, fc_key)

        if cache_entry is not None:
            logger.info(
                "[ESTIMATOR] fault_cache HIT for key=%r — min=%dp max=%dp",
                fc_key, cache_entry.repair_min_pence, cache_entry.repair_max_pence,
            )
            total_parts_min += cache_entry.repair_min_pence
            total_parts_max += cache_entry.repair_max_pence
        else:
            logger.info("[ESTIMATOR] fault_cache MISS for key=%r — querying parts pricing", fc_key)

            # Get parts list for this fault
            result = await session.execute(
                select(FaultPart).where(FaultPart.fault_type == fault_type)
            )
            parts = result.scalars().all()

            if not parts:
                logger.info("No parts defined for fault '%s' — marking as unpriced", fault_type)
                unpriced_fault_types.append(fault_type)
            elif listing.price_pence <= _PRICE_CEILING_PENCE:
                # Search prices for each part via the multi-source service
                fault_cheapest_sum = 0
                fault_median_sum = 0

                for part in parts:
                    try:
                        pricing = await _parts_pricing_service.get_prices(
                            part_name=part.part_name,
                            make=vehicle.make,
                            model=vehicle.model,
                            year=vehicle.year,
                            postcode=settings.user_postcode,
                            session=session,
                        )
                        if pricing.results:
                            cheapest = pricing.cheapest_pence or 0
                            median = _parts_pricing_service.compute_median_total_pence(pricing) or cheapest
                            fault_cheapest_sum += cheapest
                            fault_median_sum += median
                            logger.debug(
                                "Part '%s': cheapest=%dp, median=%dp",
                                part.part_name, cheapest, median,
                            )
                    except Exception:
                        logger.warning(
                            "Parts pricing failed for '%s' — skipping", part.part_name, exc_info=True
                        )

                total_parts_min += fault_cheapest_sum
                total_parts_max += fault_median_sum

                # Write result to fault_cache for future reuse
                if fault_cheapest_sum > 0 or fault_median_sum > 0:
                    try:
                        await _write_fault_cache(
                            session, fc_key, fault_cheapest_sum, fault_median_sum
                        )
                    except Exception:
                        logger.warning(
                            "[ESTIMATOR] Could not write fault_cache for key=%r", fc_key, exc_info=True
                        )

        # Add labour days
        labour = await get_labour_days(session, fault_type, car_id)
        total_man_days += labour

    has_unpriced = len(unpriced_fault_types) > 0

    # Upsert RepairEstimate (unique per listing)
    result = await session.execute(
        select(RepairEstimate).where(RepairEstimate.listing_id == listing_id)
    )
    estimate = result.scalar_one_or_none()
    if estimate is None:
        estimate = RepairEstimate(
            listing_id=listing_id,
            total_parts_min_pence=total_parts_min,
            total_parts_max_pence=total_parts_max,
            total_man_days=total_man_days,
            has_unpriced_faults=has_unpriced,
            unpriced_fault_types=unpriced_fault_types,
        )
        session.add(estimate)
    else:
        estimate.total_parts_min_pence = total_parts_min
        estimate.total_parts_max_pence = total_parts_max
        estimate.total_man_days = total_man_days
        estimate.has_unpriced_faults = has_unpriced
        estimate.unpriced_fault_types = unpriced_fault_types

    await session.commit()

    logger.info(
        "Repair estimate stored for listing %s: parts £%d–£%d, %.1f man days",
        listing_id,
        total_parts_min // 100,
        total_parts_max // 100,
        total_man_days,
    )

    await bus.emit(Event(
        type=EventType.REPAIR_ESTIMATED,
        payload={
            "listing_id": str(listing_id),
            "total_parts_min_pence": estimate.total_parts_min_pence,
            "total_parts_max_pence": estimate.total_parts_max_pence,
            "total_man_days": estimate.total_man_days,
            "has_unpriced_faults": estimate.has_unpriced_faults,
        },
    ))


async def get_labour_days(
    session: AsyncSession,
    fault_type: str,
    car_id: uuid.UUID | None,
) -> float:
    """
    Returns labour_days for this fault:
    1. Check cars_common_problems.labour_days_override for this car
    2. Fall back to common_problems.labour_days_default
    3. Fall back to 1.0 if neither found
    """
    if car_id is not None:
        result = await session.execute(
            select(CarsCommonProblem).join(
                CommonProblem,
                CarsCommonProblem.problem_id == CommonProblem.id,
            ).where(
                CarsCommonProblem.car_id == car_id,
                CommonProblem.fault_type == fault_type,
            )
        )
        ccp = result.scalar_one_or_none()
        if ccp is not None and ccp.labour_days_override is not None:
            return ccp.labour_days_override

    # Fall back to common_problems default
    result = await session.execute(
        select(CommonProblem).where(CommonProblem.fault_type == fault_type)
    )
    problem = result.scalar_one_or_none()
    if problem is not None:
        return problem.labour_days_default

    return 1.0


async def _resolve_car_id(
    session: AsyncSession,
    vehicle: Vehicle,
) -> uuid.UUID | None:
    """
    Finds the best matching Car record for a Vehicle instance.
    Matches by make/model/year range. Returns None if no match.
    """
    result = await session.execute(
        select(Car).where(
            Car.make == vehicle.make,
            Car.model == vehicle.model,
            Car.year_from <= vehicle.year,
            Car.year_to >= vehicle.year,
        )
    )
    car = result.scalars().first()
    return car.id if car else None
