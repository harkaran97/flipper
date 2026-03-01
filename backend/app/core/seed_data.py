"""
seed_data.py

Pre-seeds common_problems and cars_common_problems tables with the most
common UK fault/car pairings. Safe to run multiple times — uses upsert
pattern (insert if not exists).
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common_problem import CommonProblem
from app.models.car import Car
from app.models.cars_common_problems import CarsCommonProblem
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

CARS_COMMON_PROBLEMS_SEED = [
    # BMW N47 diesel — notorious timing chain
    {"make": "BMW", "model": "3 Series", "year_from": 2007, "year_to": 2013,
     "engine_code": "N47", "fuel_type": "diesel",
     "fault_type": "timing_chain_failure",
     "repair_min_pence": 80000, "repair_max_pence": 150000},

    # BMW N47 diesel — head gasket
    {"make": "BMW", "model": "3 Series", "year_from": 2007, "year_to": 2013,
     "engine_code": "N47", "fuel_type": "diesel",
     "fault_type": "head_gasket_failure",
     "repair_min_pence": 60000, "repair_max_pence": 120000},

    # VW Golf 7 DSG — auto gearbox shudder
    {"make": "VW", "model": "Golf", "year_from": 2012, "year_to": 2019,
     "engine_code": "DQ200", "fuel_type": "petrol",
     "fault_type": "auto_gearbox_fault",
     "repair_min_pence": 60000, "repair_max_pence": 130000},

    # Ford Focus EcoBoost — timing chain
    {"make": "Ford", "model": "Focus", "year_from": 2011, "year_to": 2018,
     "engine_code": "EcoBoost", "fuel_type": "petrol",
     "fault_type": "timing_chain_failure",
     "repair_min_pence": 60000, "repair_max_pence": 120000},

    # Range Rover L322 — air suspension
    {"make": "Land Rover", "model": "Range Rover", "year_from": 2002, "year_to": 2012,
     "engine_code": None, "fuel_type": "diesel",
     "fault_type": "air_suspension_fault",
     "repair_min_pence": 50000, "repair_max_pence": 200000},

    # Vauxhall Astra/Vectra 1.9CDTi — turbo
    {"make": "Vauxhall", "model": "Astra", "year_from": 2004, "year_to": 2010,
     "engine_code": "Z19DTH", "fuel_type": "diesel",
     "fault_type": "turbo_failure",
     "repair_min_pence": 50000, "repair_max_pence": 100000},

    # Audi A4 2.0TDI — timing chain
    {"make": "Audi", "model": "A4", "year_from": 2008, "year_to": 2015,
     "engine_code": "CAGA", "fuel_type": "diesel",
     "fault_type": "timing_chain_failure",
     "repair_min_pence": 70000, "repair_max_pence": 140000},

    # Mercedes C-Class W204 — injector
    {"make": "Mercedes", "model": "C-Class", "year_from": 2007, "year_to": 2014,
     "engine_code": "OM651", "fuel_type": "diesel",
     "fault_type": "injector_failure",
     "repair_min_pence": 80000, "repair_max_pence": 180000},

    # Toyota Prius — catalytic converter theft
    {"make": "Toyota", "model": "Prius", "year_from": 2004, "year_to": 2022,
     "engine_code": None, "fuel_type": "hybrid",
     "fault_type": "cat_fault",
     "repair_min_pence": 100000, "repair_max_pence": 250000},
]


async def seed_reference_data(session: AsyncSession) -> None:
    """
    Seeds common_problems and cars_common_problems tables.
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
        if result.scalar_one_or_none() is None:
            session.add(CommonProblem(
                fault_type=problem_data["fault_type"],
                severity=problem_data["severity"],
                description=problem_data["description"],
            ))
            problems_created += 1

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
                repair_min_pence=entry["repair_min_pence"],
                repair_max_pence=entry["repair_max_pence"],
                source=CommonProblemSource.PRE_SEEDED.value,
            ))
            pairings_created += 1

    await session.commit()
    logger.info("Car/problem pairings seeded: %d new (of %d total)",
                pairings_created, len(CARS_COMMON_PROBLEMS_SEED))
