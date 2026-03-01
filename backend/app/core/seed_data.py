"""
seed_data.py

Pre-seeds common_problems, cars_common_problems, fault_parts, and user_settings
tables. Safe to run multiple times — uses upsert pattern (insert if not exists).
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common_problem import CommonProblem
from app.models.car import Car
from app.models.cars_common_problems import CarsCommonProblem
from app.models.fault_part import FaultPart
from app.models.user_settings import UserSettings
from app.models.enums import CommonProblemSource

logger = logging.getLogger(__name__)

COMMON_PROBLEMS_SEED = [
    {"fault_type": "timing_chain_failure", "severity": "critical",
     "description": "Timing chain or belt failure, stretch, or jumped timing"},
    {"fault_type": "head_gasket_failure", "severity": "high",
     "description": "Head gasket blown or failing, coolant/oil mixing"},
    {"fault_type": "turbo_failure", "severity": "high",
     "description": "Turbocharger failure, damage, or oil seal failure"},
    {"fault_type": "injector_failure", "severity": "medium",
     "description": "Fuel injector failure, leak, or coding issue"},
    {"fault_type": "gearbox_failure", "severity": "critical",
     "description": "Gearbox failure, synchromesh, or selector failure"},
    {"fault_type": "clutch_failure", "severity": "medium",
     "description": "Clutch slip, judder, or failure"},
    {"fault_type": "dmf_failure", "severity": "medium",
     "description": "Dual mass flywheel failure or wear"},
    {"fault_type": "dpf_fault", "severity": "medium",
     "description": "Diesel particulate filter blocked or failed"},
    {"fault_type": "egr_fault", "severity": "medium",
     "description": "EGR valve blocked, stuck, or failed"},
    {"fault_type": "auto_gearbox_fault", "severity": "high",
     "description": "Automatic or DSG gearbox fault, slip, or shudder"},
    {"fault_type": "suspension_failure", "severity": "medium",
     "description": "Shock absorber, spring, or strut failure"},
    {"fault_type": "air_suspension_fault", "severity": "high",
     "description": "Air suspension compressor, bag, or sensor failure"},
    {"fault_type": "overheating", "severity": "high",
     "description": "Engine overheating, coolant loss, or temperature warning"},
    {"fault_type": "ecu_failure", "severity": "high",
     "description": "ECU, BCM, or engine management failure"},
    {"fault_type": "wiring_fault", "severity": "high",
     "description": "Wiring loom damage, short circuit, or electrical gremlins"},
    {"fault_type": "rust", "severity": "medium",
     "description": "Structural or cosmetic rust on body, sills, arches, or chassis"},
    {"fault_type": "accident_damage", "severity": "medium",
     "description": "Accident damage, collision repair, or Cat S/N status"},
    {"fault_type": "flood_damage", "severity": "critical",
     "description": "Flood or water ingress damage"},
    {"fault_type": "engine_failure", "severity": "critical",
     "description": "Engine seizure, bearing failure, or catastrophic engine damage"},
    {"fault_type": "fuel_pump_failure", "severity": "medium",
     "description": "Fuel pump failure, HPFP, or fuel delivery issue"},
    {"fault_type": "cat_fault", "severity": "high",
     "description": "Catalytic converter theft, failure, or damage"},
]

LABOUR_DAYS_DEFAULTS = {
    "timing_chain_failure": 3.5,
    "head_gasket_failure":  4.0,
    "turbo_failure":        1.5,
    "injector_failure":     1.0,
    "gearbox_failure":      2.5,
    "clutch_failure":       1.0,
    "dmf_failure":          1.5,
    "dpf_fault":            0.5,
    "egr_fault":            0.5,
    "auto_gearbox_fault":   1.0,
    "suspension_failure":   1.0,
    "air_suspension_fault": 2.0,
    "overheating":          0.5,
    "ecu_failure":          0.5,
    "wiring_fault":         3.0,
    "rust":                 5.0,
    "accident_damage":      5.0,
    "flood_damage":         7.0,
    "engine_failure":       6.0,
    "fuel_pump_failure":    1.0,
    "cat_fault":            0.5,
}

CARS_COMMON_PROBLEMS_SEED = [
    # BMW N47 diesel — notorious timing chain
    {"make": "BMW", "model": "3 Series", "year_from": 2007, "year_to": 2013,
     "engine_code": "N47", "fuel_type": "diesel",
     "fault_type": "timing_chain_failure",
     "repair_parts_min_pence": 80000, "repair_parts_max_pence": 150000},

    # BMW N47 diesel — head gasket
    {"make": "BMW", "model": "3 Series", "year_from": 2007, "year_to": 2013,
     "engine_code": "N47", "fuel_type": "diesel",
     "fault_type": "head_gasket_failure",
     "repair_parts_min_pence": 60000, "repair_parts_max_pence": 120000},

    # VW Golf 7 DSG — auto gearbox shudder
    {"make": "VW", "model": "Golf", "year_from": 2012, "year_to": 2019,
     "engine_code": "DQ200", "fuel_type": "petrol",
     "fault_type": "auto_gearbox_fault",
     "repair_parts_min_pence": 60000, "repair_parts_max_pence": 130000},

    # Ford Focus EcoBoost — timing chain
    {"make": "Ford", "model": "Focus", "year_from": 2011, "year_to": 2018,
     "engine_code": "EcoBoost", "fuel_type": "petrol",
     "fault_type": "timing_chain_failure",
     "repair_parts_min_pence": 60000, "repair_parts_max_pence": 120000},

    # Range Rover L322 — air suspension
    {"make": "Land Rover", "model": "Range Rover", "year_from": 2002, "year_to": 2012,
     "engine_code": None, "fuel_type": "diesel",
     "fault_type": "air_suspension_fault",
     "repair_parts_min_pence": 50000, "repair_parts_max_pence": 200000},

    # Vauxhall Astra/Vectra 1.9CDTi — turbo
    {"make": "Vauxhall", "model": "Astra", "year_from": 2004, "year_to": 2010,
     "engine_code": "Z19DTH", "fuel_type": "diesel",
     "fault_type": "turbo_failure",
     "repair_parts_min_pence": 50000, "repair_parts_max_pence": 100000},

    # Audi A4 2.0TDI — timing chain
    {"make": "Audi", "model": "A4", "year_from": 2008, "year_to": 2015,
     "engine_code": "CAGA", "fuel_type": "diesel",
     "fault_type": "timing_chain_failure",
     "repair_parts_min_pence": 70000, "repair_parts_max_pence": 140000},

    # Mercedes C-Class W204 — injector
    {"make": "Mercedes", "model": "C-Class", "year_from": 2007, "year_to": 2014,
     "engine_code": "OM651", "fuel_type": "diesel",
     "fault_type": "injector_failure",
     "repair_parts_min_pence": 80000, "repair_parts_max_pence": 180000},

    # Toyota Prius — catalytic converter theft
    {"make": "Toyota", "model": "Prius", "year_from": 2004, "year_to": 2022,
     "engine_code": None, "fuel_type": "hybrid",
     "fault_type": "cat_fault",
     "repair_parts_min_pence": 100000, "repair_parts_max_pence": 250000},
]

FAULT_PARTS_SEED = [
    # Timing chain failure
    {"fault_type": "timing_chain_failure", "part_name": "Timing chain kit",
     "part_category": "drivetrain", "quantity": "1",
     "notes": "Kit includes chain, guides, tensioner", "is_consumable": False},
    {"fault_type": "timing_chain_failure", "part_name": "Engine oil",
     "part_category": "consumable", "quantity": "5L",
     "notes": "Replace on reassembly", "is_consumable": True},
    {"fault_type": "timing_chain_failure", "part_name": "Oil filter",
     "part_category": "consumable", "quantity": "1",
     "notes": "Replace on reassembly", "is_consumable": True},
    {"fault_type": "timing_chain_failure", "part_name": "Rocker cover gasket",
     "part_category": "engine", "quantity": "1",
     "notes": "Often damaged on removal", "is_consumable": False},

    # Head gasket failure
    {"fault_type": "head_gasket_failure", "part_name": "Head gasket set",
     "part_category": "engine", "quantity": "1",
     "notes": "Full set including manifold gaskets", "is_consumable": False},
    {"fault_type": "head_gasket_failure", "part_name": "Head bolts",
     "part_category": "engine", "quantity": "1 set",
     "notes": "Non-reusable, must replace", "is_consumable": True},
    {"fault_type": "head_gasket_failure", "part_name": "Coolant",
     "part_category": "consumable", "quantity": "2L",
     "notes": "OAT or HOAT depending on make", "is_consumable": True},
    {"fault_type": "head_gasket_failure", "part_name": "Engine oil",
     "part_category": "consumable", "quantity": "5L",
     "notes": "Replace on reassembly", "is_consumable": True},
    {"fault_type": "head_gasket_failure", "part_name": "Oil filter",
     "part_category": "consumable", "quantity": "1",
     "notes": "Replace on reassembly", "is_consumable": True},
    {"fault_type": "head_gasket_failure", "part_name": "Thermostat",
     "part_category": "cooling", "quantity": "1",
     "notes": "Replace while accessible", "is_consumable": False},

    # Turbo failure
    {"fault_type": "turbo_failure", "part_name": "Turbocharger",
     "part_category": "forced_induction", "quantity": "1",
     "notes": "Remanufactured unit acceptable", "is_consumable": False},
    {"fault_type": "turbo_failure", "part_name": "Turbo oil feed pipe",
     "part_category": "forced_induction", "quantity": "1",
     "notes": "Replace on fit", "is_consumable": False},
    {"fault_type": "turbo_failure", "part_name": "Turbo oil return pipe",
     "part_category": "forced_induction", "quantity": "1",
     "notes": "Replace on fit", "is_consumable": False},
    {"fault_type": "turbo_failure", "part_name": "Turbo gasket set",
     "part_category": "forced_induction", "quantity": "1",
     "notes": "Inlet and exhaust gaskets", "is_consumable": True},
    {"fault_type": "turbo_failure", "part_name": "Engine oil",
     "part_category": "consumable", "quantity": "5L",
     "notes": "Flush and replace after turbo fit", "is_consumable": True},

    # Clutch failure
    {"fault_type": "clutch_failure", "part_name": "Clutch kit",
     "part_category": "transmission", "quantity": "1",
     "notes": "3-piece: plate, cover, release bearing", "is_consumable": False},
    {"fault_type": "clutch_failure", "part_name": "Dual mass flywheel",
     "part_category": "transmission", "quantity": "1",
     "notes": "Check DMF condition — replace if worn", "is_consumable": False},
    {"fault_type": "clutch_failure", "part_name": "Gearbox oil",
     "part_category": "consumable", "quantity": "2L",
     "notes": "Replace on gearbox refitting", "is_consumable": True},

    # DMF failure
    {"fault_type": "dmf_failure", "part_name": "Dual mass flywheel",
     "part_category": "transmission", "quantity": "1",
     "notes": "Replace clutch kit at same time", "is_consumable": False},
    {"fault_type": "dmf_failure", "part_name": "Clutch kit",
     "part_category": "transmission", "quantity": "1",
     "notes": "Replace while gearbox is out", "is_consumable": False},

    # Gearbox failure
    {"fault_type": "gearbox_failure", "part_name": "Reconditioned gearbox",
     "part_category": "transmission", "quantity": "1",
     "notes": "Recon unit — specify exact ratio", "is_consumable": False},
    {"fault_type": "gearbox_failure", "part_name": "Gearbox oil",
     "part_category": "consumable", "quantity": "2L",
     "notes": "Correct spec critical", "is_consumable": True},
    {"fault_type": "gearbox_failure", "part_name": "Driveshaft oil seals",
     "part_category": "transmission", "quantity": "2",
     "notes": "Replace on refitting", "is_consumable": True},

    # DPF fault
    {"fault_type": "dpf_fault", "part_name": "DPF cleaning service",
     "part_category": "exhaust", "quantity": "1",
     "notes": "Chemical clean or ultrasonic — try before replacing", "is_consumable": False},
    {"fault_type": "dpf_fault", "part_name": "DPF filter",
     "part_category": "exhaust", "quantity": "1",
     "notes": "OEM or quality aftermarket", "is_consumable": False},

    # EGR fault
    {"fault_type": "egr_fault", "part_name": "EGR valve",
     "part_category": "engine", "quantity": "1",
     "notes": "Clean first — replace if seized", "is_consumable": False},
    {"fault_type": "egr_fault", "part_name": "EGR gasket",
     "part_category": "engine", "quantity": "1",
     "notes": "Replace on refitting", "is_consumable": True},

    # Air suspension fault
    {"fault_type": "air_suspension_fault", "part_name": "Air suspension compressor",
     "part_category": "suspension", "quantity": "1",
     "notes": "Common failure point", "is_consumable": False},
    {"fault_type": "air_suspension_fault", "part_name": "Air spring / air bag",
     "part_category": "suspension", "quantity": "1-4",
     "notes": "Replace failed corners", "is_consumable": False},
    {"fault_type": "air_suspension_fault", "part_name": "Air line connectors",
     "part_category": "suspension", "quantity": "1 set",
     "notes": "Check all lines while accessible", "is_consumable": False},

    # Engine failure
    {"fault_type": "engine_failure", "part_name": "Reconditioned engine",
     "part_category": "engine", "quantity": "1",
     "notes": "Recon or used low-mileage unit", "is_consumable": False},
    {"fault_type": "engine_failure", "part_name": "Engine oil",
     "part_category": "consumable", "quantity": "5L",
     "notes": "Fresh fill on install", "is_consumable": True},
    {"fault_type": "engine_failure", "part_name": "Oil filter",
     "part_category": "consumable", "quantity": "1", "is_consumable": True},
    {"fault_type": "engine_failure", "part_name": "Coolant",
     "part_category": "consumable", "quantity": "2L", "is_consumable": True},
    {"fault_type": "engine_failure", "part_name": "Engine mount set",
     "part_category": "engine", "quantity": "1 set",
     "notes": "Replace while engine is out", "is_consumable": False},

    # Fuel pump failure
    {"fault_type": "fuel_pump_failure", "part_name": "High pressure fuel pump",
     "part_category": "fuel", "quantity": "1",
     "notes": "HPFP — model specific", "is_consumable": False},
    {"fault_type": "fuel_pump_failure", "part_name": "Fuel filter",
     "part_category": "consumable", "quantity": "1",
     "notes": "Replace at same time", "is_consumable": True},

    # Auto gearbox fault
    {"fault_type": "auto_gearbox_fault", "part_name": "DSG / auto service kit",
     "part_category": "transmission", "quantity": "1",
     "notes": "Fluid + filter — try service before replacement", "is_consumable": True},
    {"fault_type": "auto_gearbox_fault", "part_name": "Reconditioned auto gearbox",
     "part_category": "transmission", "quantity": "1",
     "notes": "Only if service does not resolve", "is_consumable": False},

    # Injector failure
    {"fault_type": "injector_failure", "part_name": "Fuel injector",
     "part_category": "fuel", "quantity": "1-4",
     "notes": "Replace faulty cylinders — code to car", "is_consumable": False},
    {"fault_type": "injector_failure", "part_name": "Injector seal kit",
     "part_category": "fuel", "quantity": "1",
     "notes": "Replace on refitting", "is_consumable": True},

    # Suspension failure
    {"fault_type": "suspension_failure", "part_name": "Shock absorber",
     "part_category": "suspension", "quantity": "1-2",
     "notes": "Replace in axle pairs", "is_consumable": False},
    {"fault_type": "suspension_failure", "part_name": "Coil spring",
     "part_category": "suspension", "quantity": "1-2",
     "notes": "Replace in axle pairs", "is_consumable": False},
    {"fault_type": "suspension_failure", "part_name": "Strut top mount",
     "part_category": "suspension", "quantity": "1-2",
     "notes": "Replace while strut is off", "is_consumable": False},
]


async def seed_reference_data(session: AsyncSession) -> None:
    """
    Seeds common_problems, cars_common_problems, fault_parts, and user_settings tables.
    Safe to run multiple times — uses upsert pattern (insert if not exists).
    """
    # Seed common problems
    problems_created = 0
    for problem_data in COMMON_PROBLEMS_SEED:
        result = await session.execute(
            select(CommonProblem).where(
                CommonProblem.fault_type == problem_data["fault_type"]
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(CommonProblem(
                fault_type=problem_data["fault_type"],
                severity=problem_data["severity"],
                description=problem_data["description"],
                labour_days_default=LABOUR_DAYS_DEFAULTS.get(problem_data["fault_type"], 1.0),
            ))
            problems_created += 1
        elif existing.labour_days_default == 1.0 and problem_data["fault_type"] in LABOUR_DAYS_DEFAULTS:
            existing.labour_days_default = LABOUR_DAYS_DEFAULTS[problem_data["fault_type"]]

    await session.flush()
    logger.info("Common problems seeded: %d new (of %d total)",
                problems_created, len(COMMON_PROBLEMS_SEED))

    # Seed car/problem pairings
    pairings_created = 0
    for entry in CARS_COMMON_PROBLEMS_SEED:
        # Find or create the car
        result = await session.execute(
            select(Car).where(
                Car.make == entry["make"],
                Car.model == entry["model"],
                Car.year_from == entry["year_from"],
                Car.year_to == entry["year_to"],
                Car.engine_code == entry["engine_code"] if entry["engine_code"] else Car.engine_code.is_(None),
            )
        )
        car = result.scalar_one_or_none()
        if car is None:
            car = Car(
                make=entry["make"],
                model=entry["model"],
                year_from=entry["year_from"],
                year_to=entry["year_to"],
                engine_code=entry["engine_code"],
                fuel_type=entry["fuel_type"],
            )
            session.add(car)
            await session.flush()

        # Find the problem
        result = await session.execute(
            select(CommonProblem).where(
                CommonProblem.fault_type == entry["fault_type"]
            )
        )
        problem = result.scalar_one_or_none()
        if problem is None:
            logger.warning("Problem type %s not found in common_problems — skipping",
                           entry["fault_type"])
            continue

        # Create pairing if not exists
        result = await session.execute(
            select(CarsCommonProblem).where(
                CarsCommonProblem.car_id == car.id,
                CarsCommonProblem.problem_id == problem.id,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(CarsCommonProblem(
                car_id=car.id,
                problem_id=problem.id,
                repair_parts_min_pence=entry["repair_parts_min_pence"],
                repair_parts_max_pence=entry["repair_parts_max_pence"],
                source=CommonProblemSource.PRE_SEEDED.value,
            ))
            pairings_created += 1

    await session.flush()
    logger.info("Car/problem pairings seeded: %d new (of %d total)",
                pairings_created, len(CARS_COMMON_PROBLEMS_SEED))

    # Seed fault parts
    await _seed_fault_parts(session)

    # Seed user settings
    await seed_user_settings(session)

    await session.commit()


async def _seed_fault_parts(session: AsyncSession) -> None:
    """Seeds fault_parts table. Insert-if-not-exists by fault_type + part_name."""
    parts_created = 0
    for entry in FAULT_PARTS_SEED:
        result = await session.execute(
            select(FaultPart).where(
                FaultPart.fault_type == entry["fault_type"],
                FaultPart.part_name == entry["part_name"],
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(FaultPart(
                fault_type=entry["fault_type"],
                part_name=entry["part_name"],
                part_category=entry["part_category"],
                quantity=entry["quantity"],
                notes=entry.get("notes"),
                is_consumable=entry.get("is_consumable", False),
            ))
            parts_created += 1

    await session.flush()
    logger.info("Fault parts seeded: %d new (of %d total)", parts_created, len(FAULT_PARTS_SEED))


async def seed_user_settings(session: AsyncSession) -> None:
    """Creates default user settings row if none exists."""
    result = await session.execute(select(UserSettings))
    if not result.scalar_one_or_none():
        session.add(UserSettings())
        await session.flush()
        logger.info("Default user settings created")
