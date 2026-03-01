# TASK 003 — AI Problem Detection Service

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`, `docs/UK_COLLOQUIAL_FAULT_KEYWORDS.md`
**Milestone:** 3 of 10
**Depends on:** TASK_001 (scaffold), TASK_002 (ingestion worker) — both merged to master
**Engineer:** Claude Code

---

## Before you start

Before writing any code, review this spec against `docs/ARCHITECTURE.md`
and all existing models/services. Flag any of the following:

- Conflicts with existing DB models or event types
- Missing dependencies from TASK_001 or TASK_002
- Any ambiguity that could lead to two valid implementations
- Any approach you would recommend changing, with clear reasoning

State concerns explicitly. Propose an alternative if you have one.
Wait for confirmation before proceeding.

If everything looks good, say "Spec reviewed — no issues found" and proceed
with the plan.

---

## Context to load

- `docs/GLOBAL_INSTRUCTIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/PRD.md`
- `docs/UK_COLLOQUIAL_FAULT_KEYWORDS.md` — canonical keyword reference
- `backend/app/models/` — all existing models
- `backend/app/events/types.py`
- `backend/app/events/bus.py`
- `backend/app/workers/ingestion_worker.py` — pattern to follow
- `backend/config.py`
- `backend/app/adapters/linkup/stub.py`

## Do NOT load
- `docs/tasks/TASK_001_scaffold.md`
- `docs/tasks/TASK_002_ingestion_worker.md`
- `backend/app/workers/enrichment_worker.py` — not relevant yet

---

## Objective

Build the AI problem detection service — the intelligence core of Flipper.

When a `NEW_LISTING_FOUND` event fires, this service:
1. Checks `cars_common_problems` for known faults on that vehicle (cache-first)
2. Runs the listing through the AI to detect faults and assess condition
3. Detects write-off category and flags accordingly
4. Assesses mechanical condition across all subsystems
5. Assesses exterior condition separately
6. Stores all findings — ready for TASK_004 (repair estimation) to consume
7. Emits `PROBLEMS_DETECTED`

**Out of scope for this task:** Opportunity classification, scoring, and profit
calculation. These depend on repair costs (TASK_004) and market value (TASK_005)
which are not yet built. Classification lives in TASK_006.

---

## What to Build

### 1. `backend/app/models/enums.py` — All enum types

Create this file first. All models import from here. No raw strings anywhere.

```python
"""
enums.py — Single source of truth for all enum types.
All models and services import enums from here.
"""
from enum import Enum

class FaultSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class FaultSource(str, Enum):
    AI = "ai"
    KEYWORD = "keyword"
    PRE_SEEDED = "pre_seeded"

class WriteOffCategory(str, Enum):
    CLEAN = "clean"
    CAT_N = "cat_n"           # Non-structural damage (formerly Cat D)
    CAT_S = "cat_s"           # Structural damage (formerly Cat C)
    CAT_A = "cat_a"           # Exclude — cannot be repaired
    CAT_B = "cat_b"           # Exclude — cannot be repaired
    FLOOD = "flood"           # Flood damage flag
    FIRE = "fire"             # Fire damage flag
    UNKNOWN_WRITEOFF = "unknown_writeoff"  # Write-off mentioned but category unclear

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MarketValueSource(str, Enum):
    EBAY_SOLD = "ebay_sold"
    LINKUP_FALLBACK = "linkup_fallback"

class MarketValueConfidence(str, Enum):
    HIGH = "high"     # >= 5 sold comps
    MEDIUM = "medium" # 3-4 sold comps
    LOW = "low"       # < 3 sold comps

class ListingSource(str, Enum):
    EBAY = "ebay"
    GUMTREE = "gumtree"
    AUTOTRADER = "autotrader"

class FuelType(str, Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    MILD_HYBRID = "mild_hybrid"
    ELECTRIC = "electric"

class CommonProblemSource(str, Enum):
    PRE_SEEDED = "pre_seeded"
    SYSTEM_OBSERVED = "system_observed"
    LINKUP_CONFIRMED = "linkup_confirmed"
```

---

### 2. New DB Models

#### `backend/app/models/common_problem.py`

```python
"""
common_problem.py

Master reference table of fault types.
Generic — not tied to any specific car.
Costs are NOT stored here (costs are car-specific, stored in cars_common_problems).
"""
class CommonProblem(Base):
    __tablename__ = "common_problems"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fault_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # FaultSeverity enum
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

#### `backend/app/models/car.py`

```python
"""
car.py

Vehicle reference table.
Represents a make/model/year_range/engine combination.
Populated by the system as new vehicles are encountered.
Can also be pre-seeded.
"""
class Car(Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    make: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_code: Mapped[str] = mapped_column(String(50), nullable=True)
    fuel_type: Mapped[str] = mapped_column(String(20), nullable=True)  # FuelType enum

    __table_args__ = (
        UniqueConstraint('make', 'model', 'year_from', 'year_to', 'engine_code',
                        name='uq_car_identity'),
    )
```

#### `backend/app/models/cars_common_problems.py`

```python
"""
cars_common_problems.py

Cross table linking cars to their known common problems.
Repair costs live here because cost is car-specific.
Populated via pre-seeding AND system observation.
"""
class CarsCommonProblem(Base):
    __tablename__ = "cars_common_problems"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    car_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cars.id"), nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("common_problems.id"), nullable=False)
    repair_min_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_max_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # CommonProblemSource enum
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('car_id', 'problem_id', name='uq_car_problem'),
    )
```

#### `backend/app/models/exterior_condition.py`

```python
"""
exterior_condition.py

Stores exterior/bodywork assessment separate from mechanical faults.
Each facet assessed independently.
"""
class ExteriorCondition(Base):
    __tablename__ = "exterior_conditions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), nullable=False)

    # Write-off / damage category
    write_off_category: Mapped[str] = mapped_column(String(30), nullable=False,
                                                      default="clean")  # WriteOffCategory enum

    # Panel damage
    panel_damage_severity: Mapped[str] = mapped_column(String(20), nullable=True)
    panel_damage_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Rust
    rust_severity: Mapped[str] = mapped_column(String(20), nullable=True)
    rust_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Paint
    paint_severity: Mapped[str] = mapped_column(String(20), nullable=True)
    paint_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Glass
    glass_severity: Mapped[str] = mapped_column(String(20), nullable=True)
    glass_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Interior
    interior_severity: Mapped[str] = mapped_column(String(20), nullable=True)
    interior_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Flood / fire flags (separate from write-off category)
    flood_damage: Mapped[bool] = mapped_column(Boolean, default=False)
    fire_damage: Mapped[bool] = mapped_column(Boolean, default=False)

    # Overall exterior severity
    overall_severity: Mapped[str] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

---

### 3. Update existing models to use `enums.py`

Update these existing models to import and use enum values from `enums.py`:
- `detected_faults` → use `FaultSeverity`, `FaultSource`
- `market_values` → use `MarketValueSource`, `MarketValueConfidence`
- `opportunities` → use `RiskLevel` (OpportunityClass added in TASK_006)
- `listings` → use `ListingSource`

Do NOT change column names or table structure — only add enum imports.
Maintain full backward compatibility.

---

### 4. DB Seed Data — `backend/app/core/seed_data.py`

Create this file. It pre-seeds `common_problems` and `cars_common_problems`
with the most common UK fault/car pairings.

Pre-seed the following common problems:

```python
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
]
```

Pre-seed the following known car/problem pairings in `cars_common_problems`:

```python
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
```

Seed function:
```python
async def seed_reference_data(session: AsyncSession):
    """
    Seeds common_problems and cars_common_problems tables.
    Safe to run multiple times — uses upsert pattern (insert if not exists).
    """
```

Call `seed_reference_data()` from `main.py` startup, after `init_db()`.
Only runs in development or when `SEED_DATA=true` env var is set.

---

### 5. `backend/app/services/ai_service.py` — Implement AI service

Replace the existing TODO placeholder entirely.

```python
"""
ai_service.py

ALL Anthropic API calls go through this module. No exceptions.
Enforces cost controls: model selection, token limits, caching.
"""
```

#### Cost control — model selection rule:
```python
def select_model(fault_count: int, has_unknown_faults: bool) -> str:
    """
    Use Haiku for simple/known fault classification.
    Use Sonnet only when listing has 3+ potential faults OR unknown fault types.
    """
    if fault_count >= 3 or has_unknown_faults:
        return "claude-sonnet-4-5"
    return "claude-haiku-4-5-20251001"
```

#### Primary prompt — problem detection:

```python
PROBLEM_DETECTION_PROMPT = """You are an expert UK automotive mechanic and car assessor
with 20 years experience buying and selling used cars at auction and privately.

You are assessing a vehicle listing to identify ALL likely faults and issues.
Be thorough. UK sellers often use slang and colloquial terms.

Common UK terms to recognise:
- "mayo/mayonnaise under cap" = coolant in oil = head gasket failure
- "lump" = engine
- "box knackered/gone" = gearbox failure
- "cambelt" = timing belt
- "lumpy/hunting idle" = rough running, possible injector/misfire
- "chucking out smoke" = excessive exhaust smoke
- "blowing" = exhaust leak or head gasket
- "needs a lump" = needs a replacement engine
- "nearside" = left (driver's side UK), "offside" = right (passenger side UK)
- "NSF/NSR/OSF/OSR" = nearside/offside front/rear panels
- "sills" = panels below doors, rust here is serious
- "arches" = wheel arches, common rust location
- "fettling" = minor repair work needed
- "ran when parked" = unknown current condition
- "barn find/been sitting" = unknown condition after storage
- "sold as seen" = seller disclaiming responsibility

Vehicle: {make} {model} {year} {fuel_type}
{engine_code_line}
Listing title: {title}
Listing description: {description}

Assess across ALL these dimensions:

1. WRITE-OFF STATUS: Is there any mention of Cat A, B, S, N, C, D, write-off,
   salvage, insurance claim, flood, fire? Map old Cat C → cat_s, Cat D → cat_n.

2. MECHANICAL FAULTS: For each subsystem, identify any mentioned or implied faults:
   powertrain, transmission, cooling, electrical, brakes, suspension/steering,
   AC/climate, exhaust, fuel system, hydraulics.

3. EXTERIOR CONDITION: Panel damage, rust (note: sill/arch/floor rust is serious),
   paint issues, glass damage, accident damage indicators.

4. INTERIOR CONDITION: Seat condition, dashboard warnings, odour, water damage signs.

5. VAGUENESS SIGNALS: Does the listing use phrases like "sold as seen", "needs TLC",
   "ran when parked", "project car" without specifying what's wrong?

Return ONLY valid JSON, no other text:
{
  "write_off_category": "clean|cat_n|cat_s|cat_a|cat_b|flood|fire|unknown_writeoff",
  "mechanical_faults": [
    {
      "fault_type": "<normalised_fault_type>",
      "severity": "critical|high|medium|low",
      "evidence": "<exact phrase from listing that indicates this fault>",
      "confidence": 0.0-1.0
    }
  ],
  "exterior": {
    "panel_damage_severity": "critical|high|medium|low|none",
    "panel_damage_notes": "<description>",
    "rust_severity": "critical|high|medium|low|none",
    "rust_notes": "<description>",
    "paint_severity": "critical|high|medium|low|none",
    "glass_severity": "critical|high|medium|low|none",
    "interior_severity": "critical|high|medium|low|none",
    "flood_damage": true|false,
    "fire_damage": true|false,
    "overall_severity": "critical|high|medium|low|none"
  },
  "driveable": true|false|null,
  "vagueness_signals": ["<phrase_1>", "<phrase_2>"],
  "overall_confidence": 0.0-1.0
}

Rules:
- Never guess fault_type — only include faults with evidence from the listing
- Use normalised fault type names matching the common_problems table
- overall_confidence reflects how much useful signal the listing contains,
  not how good an opportunity it is (that is determined later in TASK_006)
"""
```

---

### 6. `backend/app/services/problem_detector.py` — Detection orchestrator

Replace the existing TODO placeholder entirely.

```python
"""
problem_detector.py

Orchestrates problem detection for a listing.
Cache-first: checks cars_common_problems before calling AI.
Calls ai_service for novel faults.
Calls search_service (LinkUp) only for confirmed novel fault+car combos.
"""
```

#### Main function:

```python
async def detect_problems(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus
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
```

#### Write-off pre-check (before AI):

```python
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
    """
```

#### Cars_common_problems lookup:

```python
async def get_known_problems_for_car(
    session: AsyncSession,
    make: str,
    model: str,
    year: int
) -> list[CarsCommonProblem]:
    """
    Returns known problems for this car from cars_common_problems.
    Matches on make + model + year within year_from/year_to range.
    Returns empty list if car not yet in our reference data.
    """
```

#### LinkUp enrichment for novel faults:

```python
async def enrich_novel_fault(
    session: AsyncSession,
    make: str,
    model: str,
    year: int,
    fault_type: str
) -> dict:
    """
    Called when AI detects a fault not in cars_common_problems.
    Uses search_service to find repair cost intelligence.
    Stores result in cars_common_problems for future reuse.
    Returns repair cost range dict.
    """
```

---

### 7. `backend/app/workers/detection_worker.py` — Event-driven worker

Replace the existing TODO placeholder entirely.

```python
"""
detection_worker.py

Subscribes to NEW_LISTING_FOUND.
Calls problem_detector for each new listing.
Emits PROBLEMS_DETECTED on completion.
"""
```

```python
async def handle_new_listing(event: Event, session: AsyncSession, bus: EventBus):
    """
    Handler for NEW_LISTING_FOUND events.
    Calls detect_problems() for the listing.
    On failure: logs error, does NOT crash the worker.
    """

def register_detection_worker(bus: EventBus):
    """
    Registers the detection worker handler with the event bus.
    Called from main.py on startup.
    """
    bus.subscribe(EventType.NEW_LISTING_FOUND, handle_new_listing)
```

---

### 8. `backend/app/services/search_service.py` — Implement search service

Replace existing TODO placeholder.

```python
"""
search_service.py

ALL LinkUp web search calls go through this module. No exceptions.

LinkUp fires ONLY when:
1. AI detects a fault not in cars_common_problems for this vehicle
2. eBay sold comps < 3 (market value fallback — TASK_005)

Never called for:
- Opportunity discovery
- Parts pricing primary lookup
- Any fault already in cars_common_problems
"""
```

Implement the stub toggle pattern matching eBay adapter:
```python
def get_search_adapter():
    if settings.linkup_stub:
        return LinkUpStubAdapter()
    return LinkUpSearchAdapter()
```

Implement one function for TASK_003 use:
```python
async def search_fault_intelligence(
    make: str,
    model: str,
    year: int,
    fault_type: str
) -> SearchResult:
    """
    Searches for repair cost and fault intelligence for a specific
    fault on a specific vehicle model.

    Query format: "{make} {model} {year} {fault_type} repair cost UK common problem"
    """
```

---

### 9. `backend/main.py` — Register detection worker

Add detection worker registration to startup:

```python
from app.workers.detection_worker import register_detection_worker

@app.on_event("startup")
async def startup():
    # existing code...
    register_detection_worker(bus)
    logger.info("Detection worker registered")
```

---

## Seed Data Execution

The seed data must run automatically on first startup.
Add to `main.py` startup after `init_db()`:

```python
if settings.environment == "development" or settings.seed_data:
    async with AsyncSessionLocal() as session:
        await seed_reference_data(session)
        logger.info("Reference data seeded")
```

Add to `config.py`:
```python
seed_data: bool = False
```

Add to `.env.example`:
```
SEED_DATA=false
```

---

## What NOT to Build in This Task

- No repair cost estimation (TASK_004)
- No market value lookups (TASK_005)
- No opportunity scoring or classification (TASK_006) — requires repair costs
  and market value which don't exist yet
- No REST API endpoints (TASK_007)
- Do NOT implement live LinkUp API client — stub only
- Do NOT implement DVLA/MOT lookup — Phase 2

---

## Acceptance Criteria

### 1. All new models import cleanly
```bash
cd backend
python -c "
from app.models.enums import FaultSeverity, WriteOffCategory, RiskLevel
from app.models.common_problem import CommonProblem
from app.models.car import Car
from app.models.cars_common_problems import CarsCommonProblem
from app.models.exterior_condition import ExteriorCondition
print('All new models: OK')
"
```

### 2. Enums are consistent
```bash
cd backend
python -c "
from app.models.enums import WriteOffCategory, FaultSeverity, CommonProblemSource
assert WriteOffCategory.CAT_A.value == 'cat_a'
assert WriteOffCategory.CLEAN.value == 'clean'
assert FaultSeverity.CRITICAL.value == 'critical'
assert CommonProblemSource.PRE_SEEDED.value == 'pre_seeded'
assert CommonProblemSource.SYSTEM_OBSERVED.value == 'system_observed'
assert CommonProblemSource.LINKUP_CONFIRMED.value == 'linkup_confirmed'
print('Enums: OK')
"
```

### 3. Write-off detection works
```bash
cd backend
python -c "
from app.services.problem_detector import detect_writeoff_from_text
from app.models.enums import WriteOffCategory

assert detect_writeoff_from_text('BMW 320d cat s', '') == WriteOffCategory.CAT_S
assert detect_writeoff_from_text('VW Golf flood damaged', '') == WriteOffCategory.FLOOD
assert detect_writeoff_from_text('Ford Focus spares repair', '') == WriteOffCategory.CLEAN
assert detect_writeoff_from_text('Audi A4 cat d write off', '') == WriteOffCategory.CAT_N
assert detect_writeoff_from_text('BMW 1 Series cat a', '') == WriteOffCategory.CAT_A
print('Write-off detection: OK')
"
```

### 4. Search service stub works
```bash
cd backend
python -c "
import asyncio
from app.services.search_service import search_fault_intelligence

async def run():
    result = await search_fault_intelligence(
        make='BMW',
        model='3 Series',
        year=2010,
        fault_type='timing_chain_failure'
    )
    assert result.query is not None
    assert len(result.sources) > 0
    print(f'Search service stub: OK — query: {result.query}')

asyncio.run(run())
"
```

### 5. AI service imports and model selection works
```bash
cd backend
python -c "
from app.services.ai_service import select_model
assert select_model(fault_count=1, has_unknown_faults=False) == 'claude-haiku-4-5-20251001'
assert select_model(fault_count=3, has_unknown_faults=False) == 'claude-sonnet-4-5'
assert select_model(fault_count=1, has_unknown_faults=True) == 'claude-sonnet-4-5'
print('AI model selection: OK')
"
```

### 6. All TASK_001 and TASK_002 smoke tests still pass
```bash
cd backend
python -c "from app.models.listing import Listing; print('Listing model: OK')"
python -c "from app.models.opportunity import Opportunity; print('Opportunity model: OK')"
python -c "
import asyncio
from app.events.bus import EventBus
from app.events.types import EventType, Event
bus = EventBus()
results = []
async def handler(event): results.append(event.payload['test'])
bus.subscribe(EventType.NEW_LISTING_FOUND, handler)
async def run():
    await bus.emit(Event(type=EventType.NEW_LISTING_FOUND, payload={'test': 'hello'}))
    assert results == ['hello']
    print('Event bus: OK')
asyncio.run(run())
"
python -c "
from app.workers.ingestion_worker import passes_keyword_filter
from app.adapters.base import RawListing
listing = RawListing(external_id='1', source='ebay',
    title='BMW spares repair', description='engine fault',
    price_pence=150000, postcode='SW1', url='http://x.com', raw_json={})
assert passes_keyword_filter(listing) == True
print('Keyword filter: OK')
"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestone 3 → ✅
- Commit: `feat: TASK_003 — AI problem detection service with vehicle assessment matrix`
- Report: files changed, deviations with justification, proposed next task

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001, TASK_002*
*Next task: TASK_004 — Repair Estimation Service*
