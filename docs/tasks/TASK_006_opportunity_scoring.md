# TASK 006 — Opportunity Scoring

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 6 of 10
**Depends on:** TASK_001 through TASK_005 — all merged to master
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
- `backend/app/models/opportunity.py`
- `backend/app/models/repair_estimate.py`
- `backend/app/models/market_value.py`
- `backend/app/models/listing.py`
- `backend/app/models/exterior_condition.py`
- `backend/app/models/user_settings.py`
- `backend/app/events/types.py`
- `backend/app/events/bus.py`
- `backend/config.py`

## Do NOT load
- Any task specs prior to this one

---

## Objective

Build the opportunity scoring service — the final step in the pipeline.

It subscribes to `MARKET_VALUE_ESTIMATED`, pulls together everything
the pipeline has gathered, and produces the definitive opportunity
assessment for each listing.

This is the output your dad sees. Every number must be honest,
traceable, and based on real data — never a guess.

Emits `OPPORTUNITY_CREATED`.

---

## The Profit Calculation — Canonical Definition

This is the single source of truth. Implement exactly this:

```python
# All values in pence
parts_cost_mid = (repair_estimate.total_parts_min_pence +
                  repair_estimate.total_parts_max_pence) // 2

effort_cost = int(repair_estimate.total_man_days *
                  user_settings.day_rate_pence)

true_profit_pence = (market_value.median_value_pence
                     - listing.price_pence
                     - parts_cost_mid
                     - effort_cost)

true_margin_pct = (true_profit_pence / market_value.median_value_pence) * 100
```

**If `market_value.median_value_pence` is 0:** Do not divide.
Set `true_margin_pct = 0.0` and `opportunity_class = SPECULATIVE`.

**If `repair_estimate.has_unpriced_faults` is True:**
The profit figure is a floor estimate only — real cost could be higher.
Flag this clearly. Never present it as definitive.

---

## Opportunity Classification — Canonical Definition

```python
def classify_opportunity(
    true_margin_pct: float,
    true_profit_pence: int,
    market_value_confidence: str,
    has_unpriced_faults: bool,
    write_off_category: str,
    vagueness_signals: list,
    listing_price_pence: int,
    market_value_pence: int,
) -> OpportunityClass:
    """
    Canonical opportunity classification.
    Order of evaluation matters — check EXCLUDE conditions first.
    """

    # 1. Hard excludes — never surface these
    if write_off_category in ("cat_a", "cat_b"):
        return OpportunityClass.EXCLUDE

    if true_profit_pence < 0:
        return OpportunityClass.EXCLUDE

    if true_margin_pct < 5.0:
        return OpportunityClass.EXCLUDE

    # 2. Worth a look — vague listings where margin is unknown
    # Market value is 0 or confidence is LOW with unpriced faults
    if market_value_pence == 0 or (
        market_value_confidence == "low" and
        has_unpriced_faults and
        len(vagueness_signals) >= 2
    ):
        return OpportunityClass.WORTH_A_LOOK

    # 3. Strong — clean data, good margin
    if (true_margin_pct >= 40.0 and
        market_value_confidence in ("high", "medium") and
        not has_unpriced_faults):
        return OpportunityClass.STRONG

    # 4. Speculative — margin present but data incomplete
    if true_margin_pct >= 20.0:
        return OpportunityClass.SPECULATIVE

    # 5. Everything else with positive margin but below threshold
    return OpportunityClass.WORTH_A_LOOK
```

---

## Risk Level — Canonical Definition

Risk is separate from opportunity class. It reflects uncertainty
and danger signals, not profit. Your dad sees both.

```python
def calculate_risk(
    write_off_category: str,
    has_unpriced_faults: bool,
    market_value_confidence: str,
    flood_damage: bool,
    fire_damage: bool,
    vagueness_signal_count: int,
) -> RiskLevel:
    """
    HIGH risk if any of:
    - Cat S write-off
    - Flood or fire damage
    - Has unpriced faults AND low market value confidence

    MEDIUM risk if any of:
    - Cat N write-off
    - Has unpriced faults
    - Low market value confidence
    - 3+ vagueness signals

    LOW risk otherwise.
    """
    if (write_off_category == "cat_s" or
        flood_damage or fire_damage or
        (has_unpriced_faults and market_value_confidence == "low")):
        return RiskLevel.HIGH

    if (write_off_category == "cat_n" or
        has_unpriced_faults or
        market_value_confidence == "low" or
        vagueness_signal_count >= 3):
        return RiskLevel.MEDIUM

    return RiskLevel.LOW
```

---

## Add `OpportunityClass` to enums.py

This was deliberately deferred from TASK_003. Add it now:

```python
class OpportunityClass(str, Enum):
    STRONG = "strong"
    SPECULATIVE = "speculative"
    WORTH_A_LOOK = "worth_a_look"
    EXCLUDE = "exclude"
```

---

## Schema — Update `opportunities` table

Replace the existing placeholder entirely:

```python
class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listings.id"), unique=True, nullable=False
    )

    # Core financials — all pence
    listing_price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    parts_cost_min_pence: Mapped[int] = mapped_column(Integer, default=0)
    parts_cost_max_pence: Mapped[int] = mapped_column(Integer, default=0)
    parts_cost_mid_pence: Mapped[int] = mapped_column(Integer, default=0)
    effort_cost_pence: Mapped[int] = mapped_column(Integer, default=0)
    market_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    true_profit_pence: Mapped[int] = mapped_column(Integer, default=0)
    true_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Effort
    total_man_days: Mapped[float] = mapped_column(Float, default=0.0)
    day_rate_pence: Mapped[int] = mapped_column(Integer, default=15000)

    # Classification
    opportunity_class: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)

    # Data quality flags
    has_unpriced_faults: Mapped[bool] = mapped_column(Boolean, default=False)
    unpriced_fault_types: Mapped[list] = mapped_column(JSON, default=list)
    market_value_confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    market_value_comp_count: Mapped[int] = mapped_column(Integer, default=0)
    profit_is_floor_estimate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Write-off
    write_off_category: Mapped[str] = mapped_column(String(30), nullable=False,
                                                      default="clean")

    # Alert
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

---

## What to Build

### 1. Add `OpportunityClass` to `backend/app/models/enums.py`

As defined above. Do not change any existing enum values.

### 2. Update `backend/app/models/opportunity.py`

Replace existing placeholder with schema above.

### 3. `backend/app/services/opportunity_scorer.py`

Replace existing TODO placeholder entirely.

```python
"""
opportunity_scorer.py

Produces the final opportunity assessment for a listing.

Inputs:
- listing (price, title, source)
- repair_estimate (parts cost, man days, unpriced faults)
- market_value (median, confidence, comp count, write-off category)
- exterior_condition (write_off_category, flood, fire flags)
- detected_faults (vagueness signals)
- user_settings (day_rate_pence)

Output:
- Opportunity row with true_profit, true_margin, man_days,
  opportunity_class, risk_level

Never makes any external calls. Pure calculation + DB reads/writes.
"""
```

#### Main function:

```python
async def score_opportunity(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus
) -> None:
    """
    1. Load all required data for this listing
    2. Load user_settings (single row)
    3. Run canonical profit calculation
    4. Run opportunity classification
    5. Run risk calculation
    6. Store Opportunity row
    7. Emit OPPORTUNITY_CREATED
    """
```

#### Data loading helper:

```python
async def load_opportunity_inputs(
    session: AsyncSession,
    listing_id: uuid.UUID
) -> dict:
    """
    Loads all required data in one place:
    - listing
    - repair_estimate
    - market_value
    - exterior_condition
    - detected_faults (for vagueness signals)
    - user_settings

    Raises ValueError if any required data is missing.
    All pipeline steps must have completed before this runs.
    """
```

#### OPPORTUNITY_CREATED event payload:

```python
await bus.emit(Event(
    type=EventType.OPPORTUNITY_CREATED,
    payload={
        "listing_id": str(listing_id),
        "opportunity_class": opportunity.opportunity_class,
        "risk_level": opportunity.risk_level,
        "true_profit_pence": opportunity.true_profit_pence,
        "true_margin_pct": round(opportunity.true_margin_pct, 1),
        "total_man_days": opportunity.total_man_days,
        "market_value_pence": opportunity.market_value_pence,
        "listing_price_pence": opportunity.listing_price_pence,
        "write_off_category": opportunity.write_off_category,
        "has_unpriced_faults": opportunity.has_unpriced_faults,
        "profit_is_floor_estimate": opportunity.profit_is_floor_estimate,
    }
))
```

### 4. `backend/app/workers/scoring_worker.py`

Replace existing TODO placeholder.

```python
"""
scoring_worker.py

Subscribes to MARKET_VALUE_ESTIMATED.
Calls opportunity_scorer for each listing.
Emits OPPORTUNITY_CREATED on completion.
"""

def register_scoring_worker(bus: EventBus):
    bus.subscribe(EventType.MARKET_VALUE_ESTIMATED, handle_market_value_estimated)
```

### 5. Update `backend/main.py`

Register scoring worker on startup:

```python
from app.workers.scoring_worker import register_scoring_worker
register_scoring_worker(bus)
```

---

## Complete Pipeline — Verify Event Chain

At the end of this task, the full pipeline fires end-to-end:

```
NEW_LISTING_FOUND
  → detection_worker → PROBLEMS_DETECTED
  → estimation_worker → REPAIR_ESTIMATED
  → valuation_worker → MARKET_VALUE_ESTIMATED
  → scoring_worker → OPPORTUNITY_CREATED
```

Write a pipeline integration test that verifies all four events
fire in sequence using stub data:

```python
async def test_full_pipeline():
    """
    Fires NEW_LISTING_FOUND and verifies OPPORTUNITY_CREATED
    is eventually emitted.
    Uses in-memory event bus and stub adapters.
    No DB required for this test.
    """
```

---

## What NOT to Build

- No REST API endpoints (TASK_007)
- No iOS app (TASK_008+)
- No push notifications (Phase 2)
- No user-facing filtering — that's FE

---

## Acceptance Criteria

### 1. OpportunityClass enum added
```bash
cd backend
python -c "
from app.models.enums import OpportunityClass
assert OpportunityClass.STRONG.value == 'strong'
assert OpportunityClass.EXCLUDE.value == 'exclude'
assert OpportunityClass.WORTH_A_LOOK.value == 'worth_a_look'
assert OpportunityClass.SPECULATIVE.value == 'speculative'
print('OpportunityClass enum: OK')
"
```

### 2. Profit calculation is correct
```bash
cd backend
python -c "
from app.services.opportunity_scorer import calculate_true_profit

result = calculate_true_profit(
    market_value_pence=380000,    # £3,800
    listing_price_pence=120000,   # £1,200
    parts_cost_min_pence=35000,   # £350
    parts_cost_max_pence=52000,   # £520
    total_man_days=2.5,
    day_rate_pence=15000           # £150/day
)

# parts_mid = (35000+52000)//2 = 43500
# effort = 2.5 * 15000 = 37500
# profit = 380000 - 120000 - 43500 - 37500 = 179000 (£1,790)
# margin = 179000/380000*100 = 47.1%

assert result['true_profit_pence'] == 179000, f'Got {result[\"true_profit_pence\"]}'
assert abs(result['true_margin_pct'] - 47.1) < 0.1, f'Got {result[\"true_margin_pct\"]}'
print(f'Profit calculation: OK — profit £{result[\"true_profit_pence\"]/100:.0f}, margin {result[\"true_margin_pct\"]:.1f}%')
"
```

### 3. Opportunity classification correct
```bash
cd backend
python -c "
from app.services.opportunity_scorer import classify_opportunity
from app.models.enums import OpportunityClass, MarketValueConfidence

# Strong — clean data, 47% margin
result = classify_opportunity(
    true_margin_pct=47.1,
    true_profit_pence=179000,
    market_value_confidence='high',
    has_unpriced_faults=False,
    write_off_category='clean',
    vagueness_signals=[],
    listing_price_pence=120000,
    market_value_pence=380000,
)
assert result == OpportunityClass.STRONG, f'Expected STRONG, got {result}'

# Exclude — Cat A
result = classify_opportunity(
    true_margin_pct=50.0,
    true_profit_pence=200000,
    market_value_confidence='high',
    has_unpriced_faults=False,
    write_off_category='cat_a',
    vagueness_signals=[],
    listing_price_pence=100000,
    market_value_pence=400000,
)
assert result == OpportunityClass.EXCLUDE, f'Expected EXCLUDE, got {result}'

# Exclude — negative profit
result = classify_opportunity(
    true_margin_pct=-10.0,
    true_profit_pence=-40000,
    market_value_confidence='high',
    has_unpriced_faults=False,
    write_off_category='clean',
    vagueness_signals=[],
    listing_price_pence=450000,
    market_value_pence=400000,
)
assert result == OpportunityClass.EXCLUDE, f'Expected EXCLUDE, got {result}'

print('Opportunity classification: OK')
"
```

### 4. Risk calculation correct
```bash
cd backend
python -c "
from app.services.opportunity_scorer import calculate_risk
from app.models.enums import RiskLevel

assert calculate_risk('cat_s', False, 'high', False, False, 0) == RiskLevel.HIGH
assert calculate_risk('clean', False, 'high', True, False, 0) == RiskLevel.HIGH
assert calculate_risk('cat_n', False, 'high', False, False, 0) == RiskLevel.MEDIUM
assert calculate_risk('clean', False, 'high', False, False, 0) == RiskLevel.LOW
print('Risk calculation: OK')
"
```

### 5. Full event chain fires in sequence
```bash
cd backend
python -c "
import asyncio
from app.events.bus import EventBus
from app.events.types import EventType, Event

bus = EventBus()
fired_events = []

async def track(event):
    fired_events.append(event.type)

bus.subscribe(EventType.PROBLEMS_DETECTED, track)
bus.subscribe(EventType.REPAIR_ESTIMATED, track)
bus.subscribe(EventType.MARKET_VALUE_ESTIMATED, track)
bus.subscribe(EventType.OPPORTUNITY_CREATED, track)

async def run():
    await bus.emit(Event(type=EventType.PROBLEMS_DETECTED,
                         payload={'listing_id': 'test-123'}))
    print(f'Events tracked: {[e for e in fired_events]}')
    print('Event chain: OK')

asyncio.run(run())
"
```

### 6. All previous smoke tests pass
```bash
cd backend
python -c "from app.models.listing import Listing; print('Listing: OK')"
python -c "from app.models.enums import WriteOffCategory, FaultSeverity; print('Enums: OK')"
python -c "from app.services.market_valuator import calculate_median; print('Market valuator: OK')"
python -c "from app.services.repair_estimator import search_part_price; print('Repair estimator: OK')"
```

---

## After Completion

- Update `ARCHITECTURE.md` Milestones 4, 5, 6 → ✅ (if not already done)
- Commit: `feat: TASK_006 — opportunity scoring with true profit and margin`
- Report: files changed, deviations with justification
- **Include the output of the profit calculation smoke test in the report**
  so we can verify the numbers look right before building the API

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_001 through TASK_005*
*Next task: TASK_007 — REST API Endpoints*
