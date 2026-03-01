# TASK 005 — Market Value Service

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 5 of 10
**Depends on:** TASK_001, TASK_002, TASK_003, TASK_004 — all merged to master
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
- `backend/app/models/market_value.py`
- `backend/app/models/listing.py`
- `backend/app/models/exterior_condition.py` — write_off_category lives here
- `backend/app/adapters/ebay/stub.py` — sold comps stub
- `backend/app/adapters/ebay/listings.py` — live adapter pattern
- `backend/app/adapters/base.py` — BaseSoldAdapter interface
- `backend/app/services/search_service.py` — LinkUp fallback
- `backend/app/events/types.py`
- `backend/app/events/bus.py`
- `backend/config.py`

## Do NOT load
- Any task specs prior to this one

---

## Objective

Build the market value service. It subscribes to `REPAIR_ESTIMATED`,
looks up what equivalent vehicles have actually sold for, and produces
a market value estimate for the listing's vehicle.

**The single most important rule:** Sold comps must be **like-for-like
on write-off category**. A Cat N vehicle is never compared against
clean vehicles. A clean vehicle is never compared against Cat S.
Market value is only meaningful when the comparison pool is honest.

Emits `MARKET_VALUE_ESTIMATED` for TASK_006 to consume.

---

## Core Logic

### Write-off category → comp pool mapping

```python
COMP_POOL_MAP = {
    WriteOffCategory.CLEAN:           "clean",
    WriteOffCategory.CAT_N:           "cat_n",
    WriteOffCategory.CAT_S:           "cat_s",
    WriteOffCategory.FLOOD:           "flood",
    WriteOffCategory.FIRE:            "fire",
    WriteOffCategory.UNKNOWN_WRITEOFF: "salvage",
    # CAT_A and CAT_B never reach this service — excluded at detection
}
```

When searching eBay sold comps, the search query includes the
write-off status of the listing:

```python
def build_sold_query(vehicle, write_off_category: WriteOffCategory) -> str:
    base = f"{vehicle.make} {vehicle.model} {vehicle.year}"
    if write_off_category == WriteOffCategory.CAT_N:
        return f"{base} cat n sold"
    elif write_off_category == WriteOffCategory.CAT_S:
        return f"{base} cat s sold"
    elif write_off_category == WriteOffCategory.CLEAN:
        return f"{base} sold"
    elif write_off_category in (WriteOffCategory.FLOOD, WriteOffCategory.FIRE):
        return f"{base} damaged sold"
    return f"{base} salvage sold"
```

### Confidence thresholds

```python
def get_confidence(comp_count: int) -> MarketValueConfidence:
    if comp_count >= 5:
        return MarketValueConfidence.HIGH
    elif comp_count >= 3:
        return MarketValueConfidence.MEDIUM
    else:
        return MarketValueConfidence.LOW
```

### Median value calculation

Always use **median**, not mean. One outlier sale (stolen recovery,
urgent sale) should not skew the market value.

```python
def calculate_median(prices: list[int]) -> int:
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_prices[mid - 1] + sorted_prices[mid]) // 2
    return sorted_prices[mid]
```

### LinkUp fallback — when to trigger

Fire LinkUp fallback if and only if:
- eBay returns fewer than 3 sold comps for this vehicle + write-off category

LinkUp query format:
```
"{make} {model} {year} {write_off_label} sold price UK"
```

Example: `"BMW 3 Series 2010 cat n sold price UK"`

Parse returned prices from LinkUp results. If LinkUp also returns
fewer than 3 prices, mark confidence as LOW and proceed — never block
the pipeline waiting for data.

---

## What to Build

### 1. `backend/app/adapters/ebay/sold.py` — Live sold comps adapter

Replace existing TODO placeholder.

Implement `BaseSoldAdapter` using the eBay Browse API
Marketplace Insights endpoint. If not yet approved, fall back
to the standard search with `filter=soldItems`:

```
GET https://api.ebay.com/buy/browse/v1/item_summary/search
params:
  q: "{make} {model} {year}"
  category_ids: "9801"
  filter: "conditionIds:{3000},soldItems:true"  # Used/sold
  sort: "endTimeSoonest"
  limit: "20"
```

When `EBAY_STUB=true`: use stub sold comps (already in
`EbayStubAdapter.get_sold_comps()`).

Map response to `SoldComp` DTO:
```python
SoldComp(
    external_id=item["itemId"],
    title=item["title"],
    sold_price_pence=int(float(item["price"]["value"]) * 100),
    sold_date=item.get("itemEndDate", ""),
    url=item["itemWebUrl"],
)
```

### 2. Update `backend/app/models/market_value.py`

Replace existing placeholder with full schema:

```python
class MarketValue(Base):
    __tablename__ = "market_values"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id"), unique=True, nullable=False
    )
    write_off_category: Mapped[str] = mapped_column(String(30), nullable=False)
    comp_count: Mapped[int] = mapped_column(Integer, default=0)
    median_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    low_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    high_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    linkup_fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### 3. `backend/app/services/market_valuator.py`

Replace existing TODO placeholder entirely.

```python
"""
market_valuator.py

Estimates market value for a vehicle based on sold comps.

Rules:
- Like-for-like ONLY: comp pool filtered by write-off category
- Median price used (not mean)
- eBay sold comps first, LinkUp fallback if < 3 comps
- Confidence: HIGH (>=5), MEDIUM (3-4), LOW (<3)
- Never blocks pipeline — always produces an estimate even if low confidence
"""
```

#### Main function:

```python
async def estimate_market_value(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus
) -> None:
    """
    1. Load listing + vehicle + exterior_condition (for write_off_category)
    2. Build sold comps query using vehicle spec + write_off_category
    3. Fetch eBay sold comps
    4. If < 3 comps: trigger LinkUp fallback
    5. Calculate median, low, high from all comps
    6. Store MarketValue
    7. Emit MARKET_VALUE_ESTIMATED
    """
```

#### Comp filtering — write-off keyword injection:

When fetching comps for a Cat N listing, the eBay search must
include "cat n" or "cat d" in the query to ensure like-for-like.
Clean listings should explicitly exclude salvage terms:

```python
def build_comp_search_query(
    make: str,
    model: str,
    year: int,
    write_off_category: WriteOffCategory
) -> str:
    """
    Builds eBay search query string ensuring like-for-like comps.
    """
    base = f"{make} {model} {year}"
    category_terms = {
        WriteOffCategory.CLEAN: base,
        WriteOffCategory.CAT_N: f"{base} cat n",
        WriteOffCategory.CAT_S: f"{base} cat s",
        WriteOffCategory.FLOOD: f"{base} flood damaged",
        WriteOffCategory.FIRE: f"{base} fire damaged",
        WriteOffCategory.UNKNOWN_WRITEOFF: f"{base} salvage",
    }
    return category_terms.get(write_off_category, base)
```

#### MARKET_VALUE_ESTIMATED event payload:

```python
await bus.emit(Event(
    type=EventType.MARKET_VALUE_ESTIMATED,
    payload={
        "listing_id": str(listing_id),
        "median_value_pence": market_value.median_value_pence,
        "comp_count": market_value.comp_count,
        "confidence": market_value.confidence,
        "write_off_category": market_value.write_off_category,
        "linkup_fallback_used": market_value.linkup_fallback_used,
    }
))
```

### 4. `backend/app/workers/valuation_worker.py`

Replace existing TODO placeholder.

```python
"""
valuation_worker.py

Subscribes to REPAIR_ESTIMATED.
Calls market_valuator for each listing.
Emits MARKET_VALUE_ESTIMATED on completion.
"""

def register_valuation_worker(bus: EventBus):
    bus.subscribe(EventType.REPAIR_ESTIMATED, handle_repair_estimated)
```

### 5. Update `backend/main.py`

Register valuation worker on startup:

```python
from app.workers.valuation_worker import register_valuation_worker
register_valuation_worker(bus)
```

---

## Stub Behaviour

The eBay stub already has `get_sold_comps()`. Verify it returns
at least 5 sold comps with realistic UK prices.

If not, update `backend/app/adapters/ebay/stub.py` to return:

```python
STUB_SOLD_COMPS = [
    SoldComp(external_id="sold_1", title="BMW 320d SE spares repair",
             sold_price_pence=350000, sold_date="2026-02-01",
             url="https://ebay.co.uk/item/sold_1"),
    SoldComp(external_id="sold_2", title="BMW 320d M Sport cat n",
             sold_price_pence=420000, sold_date="2026-02-05",
             url="https://ebay.co.uk/item/sold_2"),
    SoldComp(external_id="sold_3", title="BMW 320d ES spares",
             sold_price_pence=380000, sold_date="2026-02-10",
             url="https://ebay.co.uk/item/sold_3"),
    SoldComp(external_id="sold_4", title="BMW 320d 2010 repair",
             sold_price_pence=395000, sold_date="2026-02-12",
             url="https://ebay.co.uk/item/sold_4"),
    SoldComp(external_id="sold_5", title="BMW 320d non runner sold",
             sold_price_pence=310000, sold_date="2026-02-15",
             url="https://ebay.co.uk/item/sold_5"),
]
```

Median of these 5 = £3,800 (380000 pence). Used in TASK_006 tests.

---

## What NOT to Build

- No opportunity scoring (TASK_006)
- No REST API endpoints (TASK_007)
- Do NOT implement live eBay Marketplace Insights API —
  use Browse API sold filter or stub

---

## Acceptance Criteria

### 1. Median calculation is correct
```bash
cd backend
python -c "
from app.services.market_valuator import calculate_median
assert calculate_median([310000, 350000, 380000, 395000, 420000]) == 380000
assert calculate_median([300000, 400000]) == 350000
assert calculate_median([500000]) == 500000
print('Median calculation: OK')
"
```

### 2. Comp query builds correctly by write-off category
```bash
cd backend
python -c "
from app.services.market_valuator import build_comp_search_query
from app.models.enums import WriteOffCategory

assert 'cat n' in build_comp_search_query('BMW', '3 Series', 2010, WriteOffCategory.CAT_N)
assert 'cat s' in build_comp_search_query('BMW', '3 Series', 2010, WriteOffCategory.CAT_S)
q = build_comp_search_query('BMW', '3 Series', 2010, WriteOffCategory.CLEAN)
assert 'cat' not in q.lower()
print('Comp query builder: OK')
"
```

### 3. Confidence thresholds correct
```bash
cd backend
python -c "
from app.services.market_valuator import get_confidence
from app.models.enums import MarketValueConfidence
assert get_confidence(5) == MarketValueConfidence.HIGH
assert get_confidence(3) == MarketValueConfidence.MEDIUM
assert get_confidence(2) == MarketValueConfidence.LOW
assert get_confidence(0) == MarketValueConfidence.LOW
print('Confidence thresholds: OK')
"
```

### 4. Market valuator importable
```bash
cd backend
python -c "
from app.services.market_valuator import estimate_market_value
from app.workers.valuation_worker import register_valuation_worker
print('Market valuator: importable OK')
"
```

### 5. All previous smoke tests pass
```bash
cd backend
python -c "from app.models.listing import Listing; print('Listing: OK')"
python -c "from app.models.enums import WriteOffCategory, MarketValueConfidence; print('Enums: OK')"
python -c "from app.services.repair_estimator import search_part_price; print('Repair estimator: OK')"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestone 5 → ✅
- Commit: `feat: TASK_005 — market value service with like-for-like comps`
- Report: files changed, deviations with justification

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001, TASK_002, TASK_003, TASK_004*
*Next task: TASK_006 — Opportunity Scoring*
