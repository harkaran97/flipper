# TASK 007 — REST API Endpoints

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 7 of 10
**Depends on:** TASK_001 through TASK_006 — all merged to master
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
- `backend/app/models/opportunity.py`
- `backend/app/models/listing.py`
- `backend/app/models/vehicle.py`
- `backend/app/models/fault.py`
- `backend/app/models/repair_estimate.py`
- `backend/app/models/market_value.py`
- `backend/app/models/parts_search_result.py`
- `backend/app/models/fault_part.py`
- `backend/app/models/exterior_condition.py`
- `backend/app/models/enums.py`
- `backend/app/events/bus.py`
- `backend/app/events/types.py`
- `backend/main.py`
- `backend/config.py`

## Do NOT load
- Any task specs prior to this one

---

## Objective

Build the REST API layer. Four endpoints total. No new models, no new
workers — this task is pure FastAPI routing and response shaping on
top of what already exists.

The API is consumed by the iOS app. Every response must be clean,
consistent, and contain exactly what the app needs — nothing more.

---

## Response Models (Pydantic)

Create `backend/app/api/schemas.py` with all response models.

### Opportunity card (feed item)

```python
class OpportunityCard(BaseModel):
    id: str
    listing_id: str

    # Vehicle
    title: str
    make: str
    model: str
    year: int | None
    listing_url: str

    # Financials
    listing_price_pence: int
    parts_cost_min_pence: int
    parts_cost_max_pence: int
    market_value_pence: int
    true_profit_pence: int
    true_margin_pct: float

    # Effort
    total_man_days: float

    # Classification
    opportunity_class: str  # strong / speculative / worth_a_look
    risk_level: str         # low / medium / high
    write_off_category: str

    # Data quality
    has_unpriced_faults: bool
    profit_is_floor_estimate: bool
    market_value_confidence: str
    market_value_comp_count: int

    created_at: str  # ISO8601
```

### Fault detail (used in opportunity detail)

```python
class FaultDetail(BaseModel):
    fault_type: str
    severity: str
    description: str | None
    labour_days: float
```

### Part result (used in parts breakdown)

```python
class PartResult(BaseModel):
    part_name: str
    part_category: str
    quantity: str
    is_consumable: bool
    suppliers: list[SupplierPrice]

class SupplierPrice(BaseModel):
    supplier: str
    price_pence: int
    url: str
    in_stock: bool
```

### Parts breakdown per fault (used in opportunity detail)

```python
class FaultPartsBreakdown(BaseModel):
    fault_type: str
    parts: list[PartResult]
    fault_parts_total_min_pence: int  # min price across all parts
    fault_parts_total_max_pence: int  # max price across all parts
```

### Full opportunity detail

```python
class OpportunityDetail(BaseModel):
    # Everything in OpportunityCard
    id: str
    listing_id: str
    title: str
    make: str
    model: str
    year: int | None
    listing_url: str
    listing_price_pence: int
    parts_cost_min_pence: int
    parts_cost_max_pence: int
    market_value_pence: int
    true_profit_pence: int
    true_margin_pct: float
    total_man_days: float
    opportunity_class: str
    risk_level: str
    write_off_category: str
    has_unpriced_faults: bool
    unpriced_fault_types: list[str]
    profit_is_floor_estimate: bool
    market_value_confidence: str
    market_value_comp_count: int
    created_at: str

    # Detail-only fields
    faults: list[FaultDetail]
    parts_breakdown: list[FaultPartsBreakdown]
    effort_cost_pence: int
    day_rate_pence: int
    linkup_fallback_used: bool
```

### Feed response

```python
class OpportunityFeedResponse(BaseModel):
    opportunities: list[OpportunityCard]
    total: int
    has_more: bool
```

### Refresh responses

```python
class RefreshResponse(BaseModel):
    job_id: str
    status: str  # pending / running / complete / failed

class RefreshStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    listings_found: int | None
    error: str | None
```

---

## What to Build

### 1. `backend/app/api/__init__.py`
Empty init file.

### 2. `backend/app/api/schemas.py`
All Pydantic response models defined above.

### 3. `backend/app/api/opportunities.py`

```python
"""
opportunities.py

GET /opportunities  — ranked opportunity feed
GET /opportunities/{id}  — full opportunity detail
"""
```

#### `GET /opportunities`

```python
@router.get("/opportunities", response_model=OpportunityFeedResponse)
async def get_opportunities(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    min_margin_pct: float = Query(default=0.0, ge=0.0),
    max_man_days: float = Query(default=None),
    max_listing_price_pence: int = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
```

**Ordering — strictly enforced:**

```python
OPPORTUNITY_CLASS_ORDER = {
    "strong": 0,
    "speculative": 1,
    "worth_a_look": 2,
}
```

Sort by: `(class_order ASC, true_margin_pct DESC)`

EXCLUDE class is never returned — filter it out at query level.

**Filters applied when provided:**
- `min_margin_pct` — filters out opportunities below threshold
- `max_man_days` — filters out opportunities above effort ceiling
- `max_listing_price_pence` — filters out listings above budget

**Joins required:**
Opportunity → Listing → Vehicle (for title, make, model, year, url)

#### `GET /opportunities/{opportunity_id}`

```python
@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
async def get_opportunity_detail(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
):
```

**Loads and assembles:**
1. Opportunity row
2. Listing (title, url, price)
3. Vehicle (make, model, year)
4. DetectedFault rows for this listing
5. For each fault: FaultPart rows + PartsSearchResult rows
6. MarketValue row (for linkup_fallback_used)
7. UserSettings (for day_rate_pence display)

**Parts breakdown assembly:**

```python
# For each detected fault:
#   1. Get FaultPart rows for this fault_type
#   2. Get PartsSearchResult rows for this listing + fault_type
#   3. Group PartsSearchResult by part_name
#   4. For each FaultPart, find matching PartsSearchResult rows
#   5. Return PartResult with suppliers list
#   6. Calculate fault_parts_total_min/max from cheapest supplier per part
```

Returns 404 if opportunity not found.
Returns 404 if opportunity has class EXCLUDE.

### 4. `backend/app/api/refresh.py`

```python
"""
refresh.py

POST /refresh  — trigger manual ingestion cycle
GET /refresh/{job_id}  — check job status
"""
```

#### In-memory job store

Simple dict — no Redis, no DB table. Jobs are ephemeral.

```python
# In-memory job store — fine for single-process personal use
_jobs: dict[str, dict] = {}
```

#### `POST /refresh`

```python
@router.post("/refresh", response_model=RefreshResponse)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    bus: EventBus = Depends(get_bus),
):
```

1. Generate `job_id = str(uuid.uuid4())`
2. Store job: `_jobs[job_id] = {"status": "pending", "started_at": None, ...}`
3. Add background task: runs one ingestion cycle, updates job status
4. Return `{"job_id": job_id, "status": "pending"}`

Background task:
```python
async def _run_ingestion(job_id: str, bus: EventBus):
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        from app.workers.ingestion_worker import run_once
        result = await run_once(bus)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["listings_found"] = result.get("listings_found", 0)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
```

Note: `run_once()` may not exist yet in `ingestion_worker.py`. If it
doesn't, add a minimal `run_once()` that runs one poll cycle and
returns `{"listings_found": n}`.

#### `GET /refresh/{job_id}`

```python
@router.get("/refresh/{job_id}", response_model=RefreshStatusResponse)
async def get_refresh_status(job_id: str):
```

Returns job from `_jobs` dict.
Returns 404 if job_id not found.

### 5. `backend/app/api/deps.py`

FastAPI dependencies:

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

def get_bus() -> EventBus:
    from main import bus
    return bus
```

### 6. Update `backend/main.py`

Include routers:

```python
from app.api.opportunities import router as opportunities_router
from app.api.refresh import router as refresh_router

app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(refresh_router, prefix="/api/v1")
```

Update healthcheck to include pipeline status:

```python
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "pipeline": {
            "ingestion": "running",
            "detection": "running",
            "estimation": "running",
            "valuation": "running",
            "scoring": "running",
        }
    }
```

---

## What NOT to Build

- No authentication (Phase 2)
- No push notifications (Phase 2)
- No eBay OAuth / messaging (Phase 2)
- No pagination beyond limit/offset (sufficient for personal use)
- No WebSocket / real-time updates

---

## Acceptance Criteria

### 1. Feed endpoint returns correct structure
```bash
cd backend
python -c "
from app.api.schemas import OpportunityFeedResponse, OpportunityCard
# Verify all required fields present
import inspect
card_fields = OpportunityCard.model_fields.keys()
required = ['id', 'listing_id', 'title', 'true_profit_pence',
            'true_margin_pct', 'total_man_days', 'opportunity_class',
            'risk_level', 'listing_url']
for f in required:
    assert f in card_fields, f'Missing field: {f}'
print('Feed schema: OK')
"
```

### 2. Detail endpoint schema complete
```bash
cd backend
python -c "
from app.api.schemas import OpportunityDetail, FaultPartsBreakdown, PartResult
detail_fields = OpportunityDetail.model_fields.keys()
required = ['faults', 'parts_breakdown', 'effort_cost_pence', 'unpriced_fault_types']
for f in required:
    assert f in detail_fields, f'Missing field: {f}'
print('Detail schema: OK')
"
```

### 3. Routers register without error
```bash
cd backend
python -c "
from app.api.opportunities import router as opp_router
from app.api.refresh import router as ref_router
routes = [r.path for r in opp_router.routes] + [r.path for r in ref_router.routes]
assert '/opportunities' in routes
assert '/opportunities/{opportunity_id}' in routes
assert '/refresh' in routes
assert '/refresh/{job_id}' in routes
print(f'Routes registered: {routes}')
print('Router registration: OK')
"
```

### 4. Opportunity ordering logic correct
```bash
cd backend
python -c "
from app.api.opportunities import OPPORTUNITY_CLASS_ORDER
assert OPPORTUNITY_CLASS_ORDER['strong'] < OPPORTUNITY_CLASS_ORDER['speculative']
assert OPPORTUNITY_CLASS_ORDER['speculative'] < OPPORTUNITY_CLASS_ORDER['worth_a_look']
assert 'exclude' not in OPPORTUNITY_CLASS_ORDER
print('Opportunity ordering: OK')
"
```

### 5. All previous smoke tests pass
```bash
cd backend
python -c "from app.models.enums import OpportunityClass; print('Enums: OK')"
python -c "from app.services.opportunity_scorer import calculate_true_profit; print('Scorer: OK')"
python -c "from app.services.market_valuator import calculate_median; print('Valuator: OK')"
python -c "from app.services.repair_estimator import estimate_repairs; print('Estimator: OK')"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestone 7 → ✅
- Commit: `feat: TASK_007 — REST API endpoints`
- Report must include:
  - All 5 smoke test results
  - Full list of routes registered (from test 3 output)
  - Any deviations with justification

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001 through TASK_006*
*Next task: TASK_008 — iOS App (SwiftUI)*
