# TASK 001 — Backend Scaffold

**Reference:** `docs/ARCHITECTURE.md`
**Milestone:** 1 of 10
**Engineer:** Claude Code

---

## Objective

Build the complete backend skeleton. No business logic. No live API calls.
Everything must be runnable and testable by the end of this task.

---

## What to Build

### 1. Project structure

Create the exact folder structure defined in `ARCHITECTURE.md` Section 4.
Create `__init__.py` in every Python package directory.
Create empty placeholder files (with a `# TODO` comment) for all modules
listed in the structure that are NOT implemented in this task.

### 2. `config.py` — Application configuration

Location: `backend/config.py`

Use `pydantic-settings` (`BaseSettings`) to load from environment variables.

Must expose:
```python
class Settings(BaseSettings):
    database_url: str
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_stub: bool = True
    linkup_api_key: str = ""
    linkup_stub: bool = True
    anthropic_api_key: str = ""
    environment: str = "development"
    log_level: str = "INFO"
    poll_interval_seconds: int = 180
    opportunity_score_threshold: float = 0.6
    alert_distance_miles: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. `app/core/database.py` — Async database connection

Use `SQLAlchemy` with `asyncpg` driver.
Provide:
- `engine` (async)
- `AsyncSessionLocal` (session factory)
- `get_db()` — async generator for FastAPI dependency injection
- `init_db()` — creates all tables (for development use)

### 4. `app/core/logging.py` — Structured logging

Configure Python's `logging` module with:
- JSON-formatted output in production
- Human-readable in development
- Log level from `settings.log_level`

### 5. `app/models/base.py` — SQLAlchemy declarative base

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### 6. Database models

Implement ALL models exactly as specified in `ARCHITECTURE.md` Section 9.

Location: `app/models/`

One file per model:
- `listing.py` → `Listing`
- `vehicle.py` → `Vehicle`
- `fault.py` → `DetectedFault` and `FaultCache`
- `repair_estimate.py` → `RepairEstimate`
- `market_value.py` → `MarketValue`
- `opportunity.py` → `Opportunity`

Requirements:
- All primary keys are UUID (`uuid.uuid4` as default)
- All timestamps use `datetime.utcnow` as default
- Use `Mapped` and `mapped_column` (SQLAlchemy 2.0 style)
- Add `__repr__` to each model for debugging
- Foreign keys must reference the correct tables

### 7. `app/events/types.py` — Event type definitions

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid

class EventType(str, Enum):
    NEW_LISTING_FOUND = "NEW_LISTING_FOUND"
    VEHICLE_ENRICHED = "VEHICLE_ENRICHED"
    PROBLEMS_DETECTED = "PROBLEMS_DETECTED"
    REPAIR_ESTIMATED = "REPAIR_ESTIMATED"
    MARKET_VALUE_ESTIMATED = "MARKET_VALUE_ESTIMATED"
    OPPORTUNITY_CREATED = "OPPORTUNITY_CREATED"

@dataclass
class Event:
    type: EventType
    payload: dict
    event_id: str = None
    created_at: datetime = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
```

### 8. `app/events/bus.py` — In-process event bus

Requirements:
- `subscribe(event_type: EventType, handler: Callable)` — register async handler
- `emit(event: Event)` — dispatch to all registered handlers for that event type
- Handlers run concurrently via `asyncio.gather`
- If a handler raises an exception: log the error, continue with other handlers
- Do NOT crash the pipeline on handler failure

```python
# Interface contract (implement this):
bus = EventBus()
bus.subscribe(EventType.NEW_LISTING_FOUND, my_handler)
await bus.emit(Event(type=EventType.NEW_LISTING_FOUND, payload={"listing_id": "..."}))
```

### 9. `app/adapters/base.py` — Abstract adapter interfaces

Implement all four abstract base classes exactly as specified in
`ARCHITECTURE.md` Section 5.

Also define the data transfer objects (plain dataclasses, not DB models):

```python
@dataclass
class RawListing:
    external_id: str
    source: str
    title: str
    description: str
    price_pence: int
    postcode: str
    url: str
    raw_json: dict

@dataclass
class SoldListing:
    title: str
    sold_price_pence: int
    year: int
    make: str
    model: str

@dataclass
class PartListing:
    title: str
    price_pence: int
    url: str

@dataclass
class SearchResult:
    query: str
    summary: str
    sources: list[str]
```

### 10. `app/adapters/ebay/stub.py` — eBay stub adapter

Implement all three eBay interfaces (`BaseListingsAdapter`, `BaseSoldAdapter`,
`BasePartsAdapter`) with hardcoded realistic UK data.

Stub data requirements:
- `search_listings`: Return 3 realistic spares/repair car listings
  (e.g. BMW 320d, Ford Focus, VW Golf with realistic titles/descriptions/prices)
- `search_sold`: Return 5 realistic sold listings for any query
- `search_parts`: Return 3 realistic parts listings

All stub data must be UK-specific (postcodes, prices in pence, GBP).

### 11. `app/adapters/linkup/stub.py` — LinkUp stub adapter

Implement `BaseSearchAdapter` with hardcoded search result:

Return a `SearchResult` with a plausible fault diagnosis summary for any query.

### 12. `main.py` — FastAPI application

Location: `backend/main.py`

```python
from fastapi import FastAPI
from app.api.health import router as health_router
# import other routers as they're built

app = FastAPI(title="Flipper API", version="0.1.0")
app.include_router(health_router)

@app.on_event("startup")
async def startup():
    # init logging
    # init db (dev only)
    pass
```

### 13. `app/api/health.py` — Healthcheck endpoint

```
GET /health
Response: {"status": "ok", "version": "0.1.0", "environment": "<env>"}
```

Must also check DB connectivity and return:
```
{"status": "degraded", "db": "unreachable"} with HTTP 503
```
if the database cannot be reached.

---

## Dependencies (`requirements.txt`)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic-settings==2.2.1
anthropic==0.28.0
httpx==0.27.0
python-dotenv==1.0.1
```

---

## `.env.example`

Create this file at repo root:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/flipper
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
EBAY_STUB=true
LINKUP_API_KEY=your_linkup_api_key
LINKUP_STUB=true
ANTHROPIC_API_KEY=your_anthropic_api_key
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## What NOT to Build in This Task

- No ingestion worker logic
- No AI calls
- No LinkUp calls
- No opportunity scoring
- No iOS client
- No Alembic migrations (init_db() is sufficient for now)

---

## Acceptance Criteria

This task is complete when ALL of the following pass:

### 1. Server starts
```bash
cd backend
uvicorn main:app --reload
# Must start without errors
```

### 2. Health endpoint responds
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "0.1.0", "environment": "development"}
```

### 3. DB health check works
```bash
# With a running Postgres:
curl http://localhost:8000/health
# Expected: {"status": "ok", "db": "connected"}

# With no Postgres running:
curl http://localhost:8000/health
# Expected: HTTP 503, {"status": "degraded", "db": "unreachable"}
```

### 4. Models import cleanly
```bash
cd backend
python -c "from app.models.listing import Listing; print('OK')"
python -c "from app.models.opportunity import Opportunity; print('OK')"
# All must print OK with no errors
```

### 5. Event bus works
```bash
cd backend
python -c "
import asyncio
from app.events.bus import EventBus
from app.events.types import EventType, Event

bus = EventBus()
results = []

async def handler(event):
    results.append(event.payload['test'])

bus.subscribe(EventType.NEW_LISTING_FOUND, handler)

async def run():
    await bus.emit(Event(type=EventType.NEW_LISTING_FOUND, payload={'test': 'hello'}))
    print(results)

asyncio.run(run())
# Expected output: ['hello']
"
```

### 6. Stubs satisfy interfaces
```bash
cd backend
python -c "
import asyncio
from app.adapters.ebay.stub import EbayStubAdapter

adapter = EbayStubAdapter()

async def run():
    listings = await adapter.search_listings('spares repair', {})
    print(f'{len(listings)} listings returned')
    print(f'First listing price: £{listings[0].price_pence / 100}')

asyncio.run(run())
# Expected: 3 listings returned, realistic price
"
```

---

## After Completion

Update `ARCHITECTURE.md` Milestone table: mark Milestone 1 as ✅

Output a brief summary:
- Files created
- Any decisions made that deviate from this spec (with justification)
- Proposed next task

---

*Task authored by: Flipper CTO/CPO*
*Depends on: Nothing (first task)*
*Next task: TASK_002 — Ingestion Worker*
