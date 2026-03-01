# TASK 004 — Repair Estimation Service

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 4 of 10
**Depends on:** TASK_001, TASK_002, TASK_003 — all merged to master
**Engineer:** Claude Code

---

## Before you start

Before writing any code, review this spec against `docs/ARCHITECTURE.md`
and all existing models/services. Flag any of the following:

- Conflicts with existing DB models or event types
- Missing dependencies from previous tasks
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
- `backend/app/models/enums.py`
- `backend/app/models/common_problem.py`
- `backend/app/models/cars_common_problems.py`
- `backend/app/models/fault.py` — detected_faults table
- `backend/app/models/repair_estimate.py` — existing placeholder
- `backend/app/services/search_service.py` — LinkUp integration
- `backend/app/events/types.py`
- `backend/app/events/bus.py`
- `backend/app/workers/detection_worker.py` — pattern to follow
- `backend/config.py`
- `backend/main.py`

## Do NOT load
- Any task specs prior to this one
- `backend/app/workers/enrichment_worker.py`

---

## Objective

Build the repair estimation service. It subscribes to `PROBLEMS_DETECTED`,
looks up the parts required for each detected fault, searches for live parts
pricing via LinkUp, and produces a complete repair estimate with:

- Itemised parts list with supplier links
- Total parts cost range
- Total man days (effort estimate)
- Total effort cost (man days × user day rate)

Emits `REPAIR_ESTIMATED` for TASK_006 to consume.

---

## Schema Changes First

### 1. Update `common_problems` table

Add `labour_days_default` — baseline effort estimate for this fault type
regardless of car. Float, 0.5 increments.

```python
labour_days_default: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
```

### 2. Update `cars_common_problems` table

Rename `repair_min_pence` → `repair_parts_min_pence`
Rename `repair_max_pence` → `repair_parts_max_pence`

Add `labour_days_override` — nullable, overrides `common_problems.labour_days_default`
for this specific car when set.

```python
repair_parts_min_pence: Mapped[int] = mapped_column(Integer, nullable=False)
repair_parts_max_pence: Mapped[int] = mapped_column(Integer, nullable=False)
labour_days_override: Mapped[float] = mapped_column(Float, nullable=True)
```

### 3. New `fault_parts` table

Maps fault types to the parts required to fix them.
Pre-seeded. Manually maintained by us.

```python
class FaultPart(Base):
    __tablename__ = "fault_parts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    fault_type: Mapped[str] = mapped_column(String(100), nullable=False)
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_category: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "1", "5L", "1 set"
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### 4. New `parts_search_results` table

Stores live parts pricing from LinkUp. TTL 24 hours — parts prices change.

```python
class PartsSearchResult(Base):
    __tablename__ = "parts_search_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), nullable=False)
    fault_type: Mapped[str] = mapped_column(String(100), nullable=False)
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier: Mapped[str] = mapped_column(String(100), nullable=False)
    price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    searched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # TTL check helper
    @property
    def is_fresh(self) -> bool:
        return (datetime.utcnow() - self.searched_at).seconds < 86400  # 24h
```

### 5. New `user_settings` table

Single row for personal use. Structured for multi-user later.

```python
class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    day_rate_pence: Mapped[int] = mapped_column(Integer, default=15000)  # £150/day
    min_profit_margin_pct: Mapped[float] = mapped_column(Float, default=20.0)
    max_budget_pence: Mapped[int] = mapped_column(Integer, nullable=True)
    max_man_days: Mapped[float] = mapped_column(Float, nullable=True)
    distance_radius_miles: Mapped[int] = mapped_column(Integer, nullable=True)
    home_postcode: Mapped[str] = mapped_column(String(10), default="LE4")
    home_lat: Mapped[float] = mapped_column(Float, default=52.6450)
    home_lng: Mapped[float] = mapped_column(Float, default=-1.1237)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

### 6. Update `repair_estimates` table

Replace the existing placeholder entirely:

```python
class RepairEstimate(Base):
    __tablename__ = "repair_estimates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id"), unique=True, nullable=False
    )
    total_parts_min_pence: Mapped[int] = mapped_column(Integer, default=0)
    total_parts_max_pence: Mapped[int] = mapped_column(Integer, default=0)
    total_man_days: Mapped[float] = mapped_column(Float, default=0.0)
    has_unpriced_faults: Mapped[bool] = mapped_column(Boolean, default=False)
    unpriced_fault_types: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

---

## Seed Data — `backend/app/core/seed_data.py`

Add the following to the existing `seed_reference_data()` function.

### Update `common_problems` with `labour_days_default`

```python
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
```

### `fault_parts` seed data

```python
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
```

---

## What to Build

### 1. `backend/app/models/fault_part.py`

Create using the schema defined above.

### 2. `backend/app/models/parts_search_result.py`

Create using the schema defined above.

### 3. `backend/app/models/user_settings.py`

Create using the schema defined above.

### 4. Update `backend/app/models/repair_estimate.py`

Replace existing placeholder with schema defined above.

### 5. Update `backend/app/core/seed_data.py`

Add `LABOUR_DAYS_DEFAULTS` and `FAULT_PARTS_SEED` to existing
`seed_reference_data()` function. Update `common_problems` rows
with labour_days_default values. Insert `fault_parts` rows.

Create default `user_settings` row on first seed:
```python
async def seed_user_settings(session: AsyncSession):
    """Creates default user settings row if none exists."""
    result = await session.execute(select(UserSettings))
    if not result.scalar_one_or_none():
        session.add(UserSettings())
        await session.commit()
        logger.info("Default user settings created")
```

### 6. `backend/app/services/repair_estimator.py`

Replace existing TODO placeholder entirely.

```python
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
```

#### Main function:

```python
async def estimate_repairs(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus
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
```

#### Parts cache check:

```python
async def get_cached_parts_results(
    session: AsyncSession,
    listing_id: uuid.UUID,
    fault_type: str
) -> list[PartsSearchResult]:
    """
    Returns fresh parts search results for this listing+fault
    if they exist and are < 24 hours old.
    Returns empty list if cache miss or stale.
    """
```

#### Labour days resolution:

```python
async def get_labour_days(
    session: AsyncSession,
    fault_type: str,
    car_id: uuid.UUID
) -> float:
    """
    Returns labour_days for this fault:
    1. Check cars_common_problems.labour_days_override for this car
    2. Fall back to common_problems.labour_days_default
    3. Fall back to 1.0 if neither found
    """
```

#### Parts search via LinkUp:

```python
async def search_part_price(
    make: str,
    model: str,
    year: int,
    part_name: str
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
```

#### REPAIR_ESTIMATED event payload:

```python
await bus.emit(Event(
    type=EventType.REPAIR_ESTIMATED,
    payload={
        "listing_id": str(listing_id),
        "total_parts_min_pence": estimate.total_parts_min_pence,
        "total_parts_max_pence": estimate.total_parts_max_pence,
        "total_man_days": estimate.total_man_days,
        "has_unpriced_faults": estimate.has_unpriced_faults,
    }
))
```

### 7. `backend/app/workers/estimation_worker.py`

Replace existing TODO placeholder.

```python
"""
estimation_worker.py

Subscribes to PROBLEMS_DETECTED.
Calls repair_estimator for each listing.
Emits REPAIR_ESTIMATED on completion.
"""

def register_estimation_worker(bus: EventBus):
    bus.subscribe(EventType.PROBLEMS_DETECTED, handle_problems_detected)
```

### 8. Update `backend/app/events/types.py`

Add new event types:

```python
REPAIR_ESTIMATED = "repair_estimated"
MARKET_VALUE_ESTIMATED = "market_value_estimated"
OPPORTUNITY_CREATED = "opportunity_created"
```

### 9. Update `backend/app/core/database.py`

Register new models: `FaultPart`, `PartsSearchResult`, `UserSettings`,
updated `RepairEstimate`.

### 10. Update `backend/main.py`

Register estimation worker on startup:

```python
from app.workers.estimation_worker import register_estimation_worker
register_estimation_worker(bus)
```

---

## What NOT to Build

- No market value logic (TASK_005)
- No opportunity scoring (TASK_006)
- No REST API endpoints (TASK_007)
- Do NOT implement live LinkUp parts search — stub returns
  plausible prices for the 6 suppliers listed above

---

## LinkUp Stub for Parts Search

Update `backend/app/adapters/linkup/stub.py` to handle parts search queries.

Return plausible stub data for a timing chain kit search:

```python
PARTS_STUB_RESULTS = {
    "timing chain kit": [
        {"supplier": "GSF Car Parts", "price_pence": 8700,
         "url": "https://www.gsf.co.uk/timing-chain-kit", "in_stock": True},
        {"supplier": "Euro Car Parts", "price_pence": 9400,
         "url": "https://www.eurocarparts.com/timing-chain-kit", "in_stock": True},
        {"supplier": "The Parts People", "price_pence": 8200,
         "url": "https://thepartspeople.co.uk/timing-chain-kit", "in_stock": True},
    ],
    "engine oil": [
        {"supplier": "GSF Car Parts", "price_pence": 2200,
         "url": "https://www.gsf.co.uk/engine-oil", "in_stock": True},
        {"supplier": "Euro Car Parts", "price_pence": 2400,
         "url": "https://www.eurocarparts.com/engine-oil", "in_stock": True},
    ],
}
# For any part not in the stub dict, return a single generic result
PARTS_STUB_DEFAULT = [
    {"supplier": "GSF Car Parts", "price_pence": 5000,
     "url": "https://www.gsf.co.uk/parts", "in_stock": True},
]
```

---

## Acceptance Criteria

### 1. New models import cleanly
```bash
cd backend
python -c "
from app.models.fault_part import FaultPart
from app.models.parts_search_result import PartsSearchResult
from app.models.user_settings import UserSettings
from app.models.repair_estimate import RepairEstimate
print('New models: OK')
"
```

### 2. Event types complete
```bash
cd backend
python -c "
from app.events.types import EventType
assert hasattr(EventType, 'REPAIR_ESTIMATED')
assert hasattr(EventType, 'MARKET_VALUE_ESTIMATED')
assert hasattr(EventType, 'OPPORTUNITY_CREATED')
print('Event types: OK')
"
```

### 3. Labour days resolution correct
```bash
cd backend
python -c "
import asyncio
from app.services.repair_estimator import get_labour_days
print('Labour days function: importable OK')
"
```

### 4. Parts stub returns results
```bash
cd backend
python -c "
import asyncio
from app.services.repair_estimator import search_part_price

async def run():
    results = await search_part_price(
        make='BMW',
        model='3 Series',
        year=2010,
        part_name='timing chain kit'
    )
    assert len(results) > 0
    assert all('supplier' in r for r in results)
    assert all('price_pence' in r for r in results)
    assert all('url' in r for r in results)
    print(f'Parts search stub: OK — {len(results)} results')

asyncio.run(run())
"
```

### 5. All previous smoke tests pass
```bash
cd backend
python -c "from app.models.listing import Listing; print('Listing: OK')"
python -c "from app.models.enums import WriteOffCategory; print('Enums: OK')"
python -c "from app.services.problem_detector import detect_writeoff_from_text; print('Problem detector: OK')"
python -c "from app.services.ai_service import select_model; print('AI service: OK')"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestone 4 → ✅
- Commit: `feat: TASK_004 — repair estimation service with live parts pricing`
- Report: files changed, deviations with justification

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001, TASK_002, TASK_003*
*Next task: TASK_005 — Market Value Service*
