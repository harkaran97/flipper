# TASK 002 — Ingestion Worker

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 2 of 10
**Depends on:** TASK_001 (scaffold) — merged to master
**Engineer:** Claude Code

---

## Context to load
- `docs/GLOBAL_INSTRUCTIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/PRD.md`
- `backend/app/adapters/base.py` — adapter interfaces and DTOs
- `backend/app/adapters/ebay/stub.py` — existing stub to reference
- `backend/app/events/types.py` — existing event types
- `backend/app/events/bus.py` — existing event bus
- `backend/app/models/listing.py` — existing Listing model
- `backend/app/core/database.py` — DB session management
- `backend/config.py` — settings

## Do NOT load
- `docs/tasks/TASK_001_scaffold.md` — previous task, ignore
- `backend/app/workers/enrichment_worker.py` — not relevant yet
- Any other worker files

---

## Before you start

Before writing any code, review this spec against `docs/ARCHITECTURE.md` and flag
any of the following if they apply:

- Anything in this spec that conflicts with ARCHITECTURE.md or existing code
- Any dependency on TASK_001 that appears missing or incomplete
- Any ambiguity that could lead to two valid implementations
- Any approach you would recommend changing, with clear reasoning

State concerns explicitly. Propose an alternative if you have one.
Wait for confirmation before proceeding.

If everything looks good, say "Spec reviewed — no issues found" and proceed
with the plan.

---

## Objective

Build the ingestion worker — the entry point of the entire pipeline. It polls eBay
for new spares/repair listings, deduplicates against the database, applies a keyword
pre-filter, stores new listings, and emits `NEW_LISTING_FOUND` events.

At the end of this task, the pipeline has its first heartbeat: every 3 minutes,
new listings enter the system and trigger the event chain.

---

## What to Build

### 1. `backend/app/adapters/ebay/client.py` — eBay OAuth client

Implement the eBay OAuth 2.0 client credentials flow.

Requirements:
- On first call, fetch a token from eBay's OAuth endpoint
- Cache the token in memory with expiry tracking
- Auto-refresh the token when it's within 60 seconds of expiry
- All requests use `EBAY-GB` marketplace header
- Raise a clear `EbayAuthError` if credentials are missing or auth fails
- When `EBAY_STUB=true`, this client is never instantiated — stub bypasses it entirely

```python
# Interface contract:
class EbayClient:
    async def get_token(self) -> str:
        """Returns a valid Bearer token, refreshing if needed."""

    async def get(self, path: str, params: dict) -> dict:
        """Authenticated GET against the eBay Browse API."""
```

eBay OAuth endpoint:
```
POST https://api.ebay.com/identity/v1/oauth2/token
Headers:
  Authorization: Basic base64(client_id:client_secret)
  Content-Type: application/x-www-form-urlencoded
Body:
  grant_type=client_credentials
  &scope=https://api.ebay.com/oauth/api_scope
```

### 2. `backend/app/adapters/ebay/listings.py` — Live listings adapter

Implement `BaseListingsAdapter` using the real eBay Browse API.

```
GET https://api.ebay.com/buy/browse/v1/item_summary/search
```

Parameters to use:
```python
params = {
    "q": "spares or repair",
    "category_ids": "9801",        # Cars & Trucks
    "filter": "conditionIds:{7000}", # For Parts or Not Working
    "sort": "newlyListed",
    "limit": "50",
    "fieldgroups": "MATCHING_ITEMS"
}
headers = {
    "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB"
}
```

Response mapping — map eBay response fields to `RawListing` DTO:
```python
RawListing(
    external_id=item["itemId"],
    source="ebay",
    title=item["title"],
    description=item.get("shortDescription", ""),
    price_pence=int(float(item["price"]["value"]) * 100),
    postcode=item.get("itemLocation", {}).get("postalCode", ""),
    url=item["itemWebUrl"],
    raw_json=item
)
```

When `EBAY_STUB=true`: use `EbayStubAdapter` instead. The toggle logic lives in
the worker (see below), not in this file.

### 3. `backend/app/adapters/ebay/stub.py` — Update existing stub

The existing stub is fine. Make one addition only:

Add a `call_count` property that increments each time `search_listings` is called.
This is used in smoke tests to verify the worker is polling correctly.

Do NOT change any existing stub data or interfaces.

### 4. `backend/app/workers/ingestion_worker.py` — Main worker

This is the core of this task. Replace the existing TODO placeholder entirely.

```python
"""
Ingestion Worker

Polls eBay for new spares/repair listings on a fixed interval.
Deduplicates against the database.
Applies keyword pre-filter.
Stores new listings.
Emits NEW_LISTING_FOUND events.
"""
```

#### Adapter selection (stub vs live)

```python
from backend.config import settings
from app.adapters.ebay.stub import EbayStubAdapter
from app.adapters.ebay.listings import EbayListingsAdapter

def get_listings_adapter():
    if settings.ebay_stub:
        return EbayStubAdapter()
    return EbayListingsAdapter()
```

#### Keyword pre-filter

Define this constant at module level — do not hardcode inline:

```python
OPPORTUNITY_KEYWORDS = [
    "spares", "repair", "non-runner", "non runner", "fault", "issue",
    "damage", "blown", "seized", "knocking", "smoking", "misfire",
    "gearbox", "clutch", "timing", "needs work", "project", "salvage"
]

def passes_keyword_filter(listing: RawListing) -> bool:
    """Returns True if listing title or description contains at least one keyword."""
    text = f"{listing.title} {listing.description}".lower()
    return any(keyword in text for keyword in OPPORTUNITY_KEYWORDS)
```

#### Deduplication

Before storing, check if `external_id` + `source` already exists in the DB:

```python
async def is_duplicate(session, external_id: str, source: str) -> bool:
    result = await session.execute(
        select(Listing).where(
            Listing.external_id == external_id,
            Listing.source == source
        )
    )
    return result.scalar_one_or_none() is not None
```

#### Main poll cycle

```python
async def run_poll_cycle(session, adapter, bus):
    """
    Single poll cycle:
    1. Fetch listings from adapter
    2. For each listing:
       a. Check duplicate — skip if seen
       b. Apply keyword filter — skip if no match
       c. Store in DB
       d. Emit NEW_LISTING_FOUND event
    Returns: dict with counts for logging
    """
```

#### Worker entrypoint

```python
async def start_ingestion_worker(bus: EventBus):
    """
    Runs indefinitely. Polls every settings.poll_interval_seconds.
    Handles exceptions gracefully — logs error, continues polling.
    Never crashes the worker on a single failed cycle.
    """
    logger.info(f"Ingestion worker starting. Interval: {settings.poll_interval_seconds}s")
    adapter = get_listings_adapter()

    while True:
        try:
            async with AsyncSessionLocal() as session:
                stats = await run_poll_cycle(session, adapter, bus)
                logger.info(f"Poll cycle complete: {stats}")
        except Exception as e:
            logger.error(f"Poll cycle failed: {e}", exc_info=True)

        await asyncio.sleep(settings.poll_interval_seconds)
```

#### Event payload for NEW_LISTING_FOUND

```python
await bus.emit(Event(
    type=EventType.NEW_LISTING_FOUND,
    payload={
        "listing_id": str(listing.id),
        "source": listing.source,
        "title": listing.title,
        "price_pence": listing.price_pence,
        "postcode": listing.postcode
    }
))
```

### 5. `backend/main.py` — Wire worker into startup

Update `main.py` to start the ingestion worker as a background task on startup.

```python
from app.events.bus import EventBus
from app.workers.ingestion_worker import start_ingestion_worker

bus = EventBus()  # Single shared bus instance

@app.on_event("startup")
async def startup():
    # existing DB init (keep as-is)
    # Start ingestion worker as background task
    asyncio.create_task(start_ingestion_worker(bus))
    logger.info("Ingestion worker scheduled")
```

The `bus` instance must be module-level so future workers can subscribe to it.

### 6. `backend/app/api/health.py` — Add worker status

Update the health endpoint to report whether the ingestion worker has completed
at least one poll cycle.

Add to health response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "db": "connected",
  "last_poll": "2026-03-01T18:00:00Z"  // or null if not yet polled
}
```

Track `last_poll` as a module-level variable updated by the worker after each
successful cycle.

---

## What NOT to Build in This Task

- No enrichment logic (TASK_003)
- No AI calls
- No repair estimation
- No opportunity scoring
- Do NOT implement `enrichment_worker.py` — it subscribes to `NEW_LISTING_FOUND`
  but that is the next task

---

## Acceptance Criteria

All of the following must pass before committing.

### 1. Keyword filter works correctly
```bash
cd backend
python -c "
from app.workers.ingestion_worker import passes_keyword_filter
from app.adapters.base import RawListing

# Should PASS
listing_pass = RawListing(
    external_id='1', source='ebay',
    title='BMW 320d spares or repair',
    description='engine fault',
    price_pence=150000, postcode='SW1A1AA',
    url='http://test.com', raw_json={}
)

# Should FAIL
listing_fail = RawListing(
    external_id='2', source='ebay',
    title='BMW 320d 2019 full service history',
    description='excellent condition',
    price_pence=1500000, postcode='SW1A1AA',
    url='http://test.com', raw_json={}
)

assert passes_keyword_filter(listing_pass) == True, 'Should pass'
assert passes_keyword_filter(listing_fail) == False, 'Should fail'
print('Keyword filter: OK')
"
```

### 2. Poll cycle runs and emits events (stub mode)
```bash
cd backend
python -c "
import asyncio
from app.events.bus import EventBus
from app.events.types import EventType, Event
from app.adapters.ebay.stub import EbayStubAdapter

bus = EventBus()
received_events = []

async def capture(event):
    received_events.append(event)

bus.subscribe(EventType.NEW_LISTING_FOUND, capture)

async def run():
    from app.workers.ingestion_worker import run_poll_cycle
    # Use in-memory session mock — or real DB if available
    adapter = EbayStubAdapter()
    # Run one cycle
    # Events should fire for listings that pass keyword filter
    print(f'Stub listings available: 3')
    print('Poll cycle logic: OK')

asyncio.run(run())
"
```

### 3. Server starts with worker running
```bash
cd backend
timeout 8 uvicorn main:app --host 127.0.0.1 --port 8000 &
sleep 4
curl -s http://127.0.0.1:8000/health
# Expected: server starts, health returns 200 or 503 (no crash)
echo ""
```

### 4. Deduplication logic is correct
```bash
cd backend
python -c "
# Verify the deduplication query is importable and correct
from app.workers.ingestion_worker import is_duplicate
print('Deduplication function: importable OK')
"
```

### 5. All existing TASK_001 smoke tests still pass
```bash
cd backend
python -c "from app.models.listing import Listing; print('Models: OK')"
python -c "from app.models.opportunity import Opportunity; print('Opportunity: OK')"
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
    assert results == ['hello'], f'Expected hello, got {results}'
    print('Event bus: OK')
asyncio.run(run())
"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestone 2 → ✅
- Commit message: `feat: TASK_002 — ingestion worker with keyword pre-filter and deduplication`
- Report: files changed, any deviations with justification, proposed next task

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001*
*Next task: TASK_003 — AI Problem Detection Service*
