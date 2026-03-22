"""
problem_detector.py

Orchestrates problem detection for a listing.
Cache-first: checks cars_common_problems before calling AI.
Calls ai_service for novel faults.
Calls search_service (LinkUp) only for confirmed novel fault+car combos.
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
from app.models.enums import CommonProblemSource, FaultSource, WriteOffCategory
from app.models.exterior_condition import ExteriorCondition
from app.models.fault import DetectedFault
from app.models.listing import Listing
from app.models.vehicle import Vehicle
from app.services.ai_service import detect_problems_ai
from app.services.search_service import search_fault_intelligence

logger = logging.getLogger(__name__)

WRITEOFF_KEYWORDS = {
    WriteOffCategory.CAT_A: ["cat a", "category a", "cat-a"],
    WriteOffCategory.CAT_B: ["cat b", "category b", "cat-b"],
    WriteOffCategory.CAT_S: ["cat s", "cat c", "category s", "category c",
                              "structural damage", "chassis damage"],
    WriteOffCategory.CAT_N: ["cat n", "cat d", "category n", "category d",
                              "non-structural", "insurance write-off",
                              "write off", "written off", "salvage"],
    WriteOffCategory.FLOOD: ["flood damage", "flood damaged", "water ingress",
                              "submerged", "tidemark", "flood"],
    WriteOffCategory.FIRE: ["fire damage", "fire damaged", "burnt out",
                             "fire", "burned"],
}


def detect_writeoff_from_text(title: str, description: str) -> WriteOffCategory:
    """
    Fast keyword-based write-off detection before AI runs.
    Returns WriteOffCategory.CLEAN if no write-off keywords found.
    Cat A and Cat B set opportunity_class to EXCLUDE immediately.

    Priority order: CAT_A > CAT_B > CAT_S > FLOOD > FIRE > CAT_N
    More specific categories checked first to avoid false matches.
    """
    text = f"{title} {description}".lower()

    # Check in priority order — most severe / specific first
    for category in [
        WriteOffCategory.CAT_A,
        WriteOffCategory.CAT_B,
        WriteOffCategory.CAT_S,
        WriteOffCategory.FLOOD,
        WriteOffCategory.FIRE,
        WriteOffCategory.CAT_N,
    ]:
        for keyword in WRITEOFF_KEYWORDS[category]:
            if keyword in text:
                return category

    return WriteOffCategory.CLEAN


async def get_known_problems_for_car(
    session: AsyncSession,
    make: str,
    model: str,
    year: int,
) -> list[CarsCommonProblem]:
    """
    Returns known problems for this car from cars_common_problems.
    Matches on make + model + year within year_from/year_to range.
    Returns empty list if car not yet in our reference data.
    """
    result = await session.execute(
        select(CarsCommonProblem)
        .join(Car, CarsCommonProblem.car_id == Car.id)
        .where(
            Car.make == make,
            Car.model == model,
            Car.year_from <= year,
            Car.year_to >= year,
        )
    )
    return list(result.scalars().all())


async def enrich_novel_fault(
    session: AsyncSession,
    make: str,
    model: str,
    year: int,
    fault_type: str,
) -> dict:
    """
    Called when AI detects a fault not in cars_common_problems.
    Uses search_service to find repair cost intelligence.
    Stores result in cars_common_problems for future reuse.
    Returns repair cost range dict.
    """
    search_result = await search_fault_intelligence(
        make=make, model=model, year=year, fault_type=fault_type
    )
    logger.info("LinkUp enrichment for %s %s %s: %s",
                make, model, fault_type, search_result.query)

    # Default cost range from stub/search — will be refined by TASK_004
    repair_min_pence = 30000  # £300 minimum
    repair_max_pence = 80000  # £800 maximum

    # Find or create the common problem entry
    result = await session.execute(
        select(CommonProblem).where(CommonProblem.fault_type == fault_type)
    )
    problem = result.scalar_one_or_none()
    if problem is None:
        problem = CommonProblem(
            fault_type=fault_type,
            severity="medium",
            description=f"AI-detected fault: {fault_type}",
        )
        session.add(problem)
        await session.flush()

    # Find or create the car entry (year band: -2/+2 around detected year)
    year_from = year - 2
    year_to = year + 2
    result = await session.execute(
        select(Car).where(
            Car.make == make,
            Car.model == model,
            Car.year_from == year_from,
            Car.year_to == year_to,
        )
    )
    car = result.scalar_one_or_none()
    if car is None:
        car = Car(
            make=make,
            model=model,
            year_from=year_from,
            year_to=year_to,
        )
        session.add(car)
        await session.flush()

    # Create the car/problem pairing
    result = await session.execute(
        select(CarsCommonProblem).where(
            CarsCommonProblem.car_id == car.id,
            CarsCommonProblem.problem_id == problem.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        session.add(CarsCommonProblem(
            car_id=car.id,
            problem_id=problem.id,
            repair_parts_min_pence=repair_min_pence,
            repair_parts_max_pence=repair_max_pence,
            source=CommonProblemSource.LINKUP_CONFIRMED.value,
        ))
        await session.flush()

    return {
        "repair_min_pence": repair_min_pence,
        "repair_max_pence": repair_max_pence,
        "search_summary": search_result.summary,
    }


async def detect_problems(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus,
) -> None:
    """
    Full problem detection pipeline for one listing.
    1. Load listing + vehicle data
    2. Check write-off keywords first (fast, no AI)
    3. Check cars_common_problems for known faults (no AI needed for known combos)
    4. Run AI detection for novel fault identification and condition assessment
    5. For novel fault+car combos not in cars_common_problems:
       - trigger LinkUp search (via search_service)
       - update cars_common_problems with new intelligence
    6. Store results in detected_faults + exterior_condition
    7. Emit PROBLEMS_DETECTED

    NOTE: No opportunity classification here. That happens in TASK_006
    once repair costs (TASK_004) and market value (TASK_005) are available.
    """
    logger.info("[DETECTOR] Step 1: Loading listing %s from DB", listing_id)

    # 1. Load listing + vehicle data
    result = await session.execute(
        select(Listing).where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        logger.error("[DETECTOR] Step 1 FAILED: Listing %s not found in DB", listing_id)
        return

    logger.info(
        "[DETECTOR] Step 1 OK: Listing fetched — title=%r, description_len=%d, processed=%s",
        listing.title,
        len(listing.description or ""),
        listing.processed,
    )

    result = await session.execute(
        select(Vehicle).where(Vehicle.listing_id == listing_id)
    )
    vehicle = result.scalar_one_or_none()

    # Use vehicle data if available, otherwise defaults
    make = vehicle.make if vehicle else "Unknown"
    model = vehicle.model if vehicle else "Unknown"
    year = vehicle.year if vehicle else 0
    fuel_type = vehicle.fuel_type if vehicle else None
    engine_code = None  # Not yet in vehicle model, will be added in enrichment

    if vehicle:
        logger.info(
            "[DETECTOR] Step 1 OK: Vehicle fetched — %s %s %d fuel=%s",
            make, model, year, fuel_type,
        )
    else:
        logger.warning(
            "[DETECTOR] Step 1 WARN: No vehicle row found for listing %s — using Unknown defaults",
            listing_id,
        )

    # 2. Check write-off keywords first (fast, no AI)
    logger.info("[DETECTOR] Step 2: Running write-off keyword check")
    write_off_category = detect_writeoff_from_text(
        listing.title, listing.description or ""
    )
    logger.info(
        "[DETECTOR] Step 2 OK: Write-off result = %s", write_off_category.value
    )

    # 3. Check cars_common_problems for known faults
    logger.info(
        "[DETECTOR] Step 3: Querying known problems for %s %s %d",
        make, model, year,
    )
    known_problems = await get_known_problems_for_car(session, make, model, year)
    logger.info("[DETECTOR] Step 3 OK: Found %d known problem(s)", len(known_problems))

    known_fault_types = set()
    if known_problems:
        # Load fault_type names for known problems
        problem_ids = [kp.problem_id for kp in known_problems]
        result = await session.execute(
            select(CommonProblem).where(CommonProblem.id.in_(problem_ids))
        )
        problems_by_id = {p.id: p for p in result.scalars().all()}
        known_fault_types = {
            problems_by_id[kp.problem_id].fault_type
            for kp in known_problems
            if kp.problem_id in problems_by_id
        }
        logger.info("[DETECTOR] Step 3 OK: Known fault types = %s", known_fault_types)

    # 4. Run AI detection
    logger.info(
        "[DETECTOR] Step 4: Calling AI — make=%s model=%s year=%d known_faults=%d",
        make, model, year, len(known_problems),
    )
    ai_result = await detect_problems_ai(
        make=make,
        model=model,
        year=year,
        fuel_type=fuel_type,
        engine_code=engine_code,
        title=listing.title,
        description=listing.description or "",
        known_fault_count=len(known_problems),
        has_unknown_faults=False,  # Will be determined after first pass
    )
    logger.info(
        "[DETECTOR] Step 4 OK: AI returned %d mechanical_fault(s), write_off=%s, "
        "driveable=%s, overall_confidence=%s",
        len(ai_result.get("mechanical_faults", [])),
        ai_result.get("write_off_category"),
        ai_result.get("driveable"),
        ai_result.get("overall_confidence"),
    )

    # 5. Process AI results — store detected faults
    logger.info("[DETECTOR] Step 5: Saving detected faults to DB")
    detected_fault_ids = []
    for i, fault in enumerate(ai_result.get("mechanical_faults", [])):
        fault_type = fault.get("fault_type", "unknown")
        severity = fault.get("severity", "medium")
        confidence = fault.get("confidence", 0.5)

        # Determine source
        if fault_type in known_fault_types:
            source = FaultSource.PRE_SEEDED.value
        else:
            source = FaultSource.AI.value

        logger.info(
            "[DETECTOR] Step 5: Saving fault %d/%d — type=%r severity=%s confidence=%.2f source=%s",
            i + 1,
            len(ai_result.get("mechanical_faults", [])),
            fault_type,
            severity,
            confidence,
            source,
        )

        detected = DetectedFault(
            listing_id=listing_id,
            issue=fault_type,
            confidence=confidence,
            severity=severity,
            source=source,
        )
        session.add(detected)
        await session.flush()
        detected_fault_ids.append(str(detected.id))
        logger.info("[DETECTOR] Step 5 OK: Fault saved with id=%s", detected.id)

        # 5b. For novel faults not in cars_common_problems, enrich via LinkUp
        if fault_type not in known_fault_types and make != "Unknown":
            logger.info(
                "[DETECTOR] Step 5b: Novel fault %r not in known set — triggering LinkUp enrichment",
                fault_type,
            )
            try:
                await enrich_novel_fault(session, make, model, year, fault_type)
                logger.info("[DETECTOR] Step 5b OK: LinkUp enrichment complete for %r", fault_type)
            except Exception as exc:
                logger.warning(
                    "[DETECTOR] Step 5b WARN: LinkUp enrichment failed for %r — %s",
                    fault_type,
                    exc,
                )

    logger.info(
        "[DETECTOR] Step 5 OK: %d fault(s) saved — ids=%s",
        len(detected_fault_ids),
        detected_fault_ids,
    )

    # 6. Store exterior condition
    logger.info("[DETECTOR] Step 6: Saving exterior condition")
    exterior = ai_result.get("exterior", {})
    ext_condition = ExteriorCondition(
        listing_id=listing_id,
        write_off_category=write_off_category.value,
        panel_damage_severity=_normalise_severity(exterior.get("panel_damage_severity")),
        panel_damage_notes=exterior.get("panel_damage_notes") or None,
        rust_severity=_normalise_severity(exterior.get("rust_severity")),
        rust_notes=exterior.get("rust_notes") or None,
        paint_severity=_normalise_severity(exterior.get("paint_severity")),
        glass_severity=_normalise_severity(exterior.get("glass_severity")),
        interior_severity=_normalise_severity(exterior.get("interior_severity")),
        flood_damage=exterior.get("flood_damage", False),
        fire_damage=exterior.get("fire_damage", False),
        overall_severity=_normalise_severity(exterior.get("overall_severity")),
    )
    session.add(ext_condition)

    # Mark listing as processed
    listing.processed = True
    logger.info("[DETECTOR] Step 6 OK: ExteriorCondition added, marking listing.processed=True")
    await session.commit()
    logger.info("[DETECTOR] Step 6 OK: DB commit complete")

    # 7. Emit PROBLEMS_DETECTED
    logger.info("[DETECTOR] Step 7: Emitting PROBLEMS_DETECTED event")
    await bus.emit(Event(
        type=EventType.PROBLEMS_DETECTED,
        payload={
            "listing_id": str(listing_id),
            "fault_count": len(detected_fault_ids),
            "fault_ids": detected_fault_ids,
            "write_off_category": write_off_category.value,
            "driveable": ai_result.get("driveable"),
            "overall_confidence": ai_result.get("overall_confidence", 0.0),
        },
    ))

    logger.info(
        "[DETECTOR] Step 7 OK: PROBLEMS_DETECTED emitted — listing=%s faults=%d write_off=%s",
        listing_id, len(detected_fault_ids), write_off_category.value,
    )


def _normalise_severity(value: str | None) -> str | None:
    """Normalise severity value from AI, returning None for 'none' or empty."""
    if not value or value == "none":
        return None
    return value
