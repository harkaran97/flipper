"""
repair_estimator.py

Produces repair estimates for a listing.

Logic:
1. Load detected faults for this listing
2. For each fault:
   a. Look up fault_parts — get parts list
   b. For each part: search LinkUp for live price
      (check parts_search_results cache first — TTL 24h)
   c. Sum parts cost across all faults
3. Look up labour_days from cars_common_problems (override)
   or common_problems (default)
4. Sum total man days
5. Store RepairEstimate
6. Store PartsSearchResult rows

Parts search query format:
"{make} {model} {year} {part_name} buy UK"

Suppliers to search (in priority order):
1. GSF Car Parts (gsf.co.uk)
2. Euro Car Parts (eurocarparts.com)
3. The Parts People (thepartspeople.co.uk)
4. Autodoc (autodoc.co.uk)
5. eBay Motors Parts
6. Andrew Page (andrewpage.co.uk)
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.car import Car
from app.models.cars_common_problems import CarsCommonProblem
from app.models.common_problem import CommonProblem
from app.models.fault import DetectedFault
from app.models.fault_part import FaultPart
from app.models.listing import Listing
from app.models.parts_search_result import PartsSearchResult
from app.models.repair_estimate import RepairEstimate
from app.models.vehicle import Vehicle
from app.services.search_service import search_parts_price as _search_parts_price

logger = logging.getLogger(__name__)

# Cost ceiling: only search parts prices if listing is below £10,000
_PRICE_CEILING_PENCE = 1_000_000


async def estimate_repairs(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus,
) -> None:
    """
    Full repair estimation pipeline for one listing.
    1. Load listing + vehicle + detected faults
    2. For each fault → get parts list from fault_parts
    3. For each part → search LinkUp (cache-first, TTL 24h)
    4. Sum parts cost + man days
    5. Store RepairEstimate + PartsSearchResult rows
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
        logger.info("estimate_repairs: no detected faults for listing %s — emitting zero estimate",
                    listing_id)

    # Resolve car_id for labour days lookup
    car_id = await _resolve_car_id(session, vehicle)

    total_parts_min = 0
    total_parts_max = 0
    total_man_days = 0.0
    unpriced_fault_types: list[str] = []

    for fault in faults:
        fault_type = fault.issue

        # Get parts list for this fault
        result = await session.execute(
            select(FaultPart).where(FaultPart.fault_type == fault_type)
        )
        parts = result.scalars().all()

        if not parts:
            logger.info("No parts defined for fault '%s' — marking as unpriced", fault_type)
            unpriced_fault_types.append(fault_type)
        else:
            # Only search parts prices if listing is below plausibility ceiling
            if listing.price_pence <= _PRICE_CEILING_PENCE:
                cached = await get_cached_parts_results(session, listing_id, fault_type)
                cached_names = {r.part_name for r in cached}

                for part in parts:
                    if part.part_name not in cached_names:
                        raw_results = await search_part_price(
                            make=vehicle.make,
                            model=vehicle.model,
                            year=vehicle.year,
                            part_name=part.part_name,
                        )
                        for r in raw_results:
                            session.add(PartsSearchResult(
                                listing_id=listing_id,
                                fault_type=fault_type,
                                part_name=part.part_name,
                                supplier=r["supplier"],
                                price_pence=r["price_pence"],
                                url=r["url"],
                                in_stock=r.get("in_stock", True),
                            ))

        # Sum parts costs from cached (or freshly stored) results
        await session.flush()
        fresh_results = await get_cached_parts_results(session, listing_id, fault_type)
        if fresh_results:
            prices = [r.price_pence for r in fresh_results if r.in_stock]
            if prices:
                total_parts_min += min(prices)
                total_parts_max += max(prices)

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


async def get_cached_parts_results(
    session: AsyncSession,
    listing_id: uuid.UUID,
    fault_type: str,
) -> list[PartsSearchResult]:
    """
    Returns fresh parts search results for this listing+fault
    if they exist and are < 24 hours old.
    Returns empty list if cache miss or stale.
    """
    result = await session.execute(
        select(PartsSearchResult).where(
            PartsSearchResult.listing_id == listing_id,
            PartsSearchResult.fault_type == fault_type,
        )
    )
    rows = result.scalars().all()
    return [r for r in rows if r.is_fresh]


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


async def search_part_price(
    make: str,
    model: str,
    year: int,
    part_name: str,
) -> list[dict]:
    """
    Searches LinkUp for current UK parts prices.
    Query: "{make} {model} {year} {part_name} buy UK"
    Returns list of {supplier, price_pence, url, in_stock}
    Returns empty list on failure — never crashes estimation.

    Cost control: Only fires for listings where listing_price_pence
    is below a plausibility threshold (market value not yet known,
    so use a generous ceiling of £10,000 / 1,000,000 pence).
    """
    try:
        return await _search_parts_price(make=make, model=model, year=year, part_name=part_name)
    except Exception:
        logger.error("Parts price search failed for '%s' — returning empty", part_name, exc_info=True)
        return []


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
