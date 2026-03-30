# TASK 038 — Sold Comp URLs

**Reference:** `docs/ARCHITECTURE.md`, `docs/GLOBAL_INSTRUCTIONS.md`
**Milestone:** 38
**Depends on:** TASK_005 (market value service), TASK_007 (REST API)
**Engineer:** Claude Code

---

## Objective

Surface the eBay URLs of the sold comps used to calculate market value, all the way
from the adapter through to the `GET /opportunities/{id}` API response.

Currently `SoldListing` carries no URL, so the user has no way to verify or
inspect which sold listings were used to determine market value. This task adds
`url` end-to-end.

---

## Context to load

- `backend/app/adapters/base.py` — SoldListing dataclass
- `backend/app/adapters/ebay/sold.py` — live adapter
- `backend/app/adapters/ebay/stub.py` — stub adapter
- `backend/app/models/market_value.py` — MarketValue DB model
- `backend/app/services/market_valuator.py` — valuation service
- `backend/app/api/schemas.py` — OpportunityDetail response schema
- `backend/app/api/opportunities.py` — detail endpoint

---

## Changes

### 1. `backend/app/adapters/base.py`

Add `url` field to `SoldListing`:

```python
@dataclass
class SoldListing:
    title: str
    sold_price_pence: int
    year: int
    make: str
    model: str
    url: str = ""
```

### 2. `backend/app/adapters/ebay/sold.py`

Capture `itemWebUrl` from the eBay Browse API response:

```python
listing = SoldListing(
    title=item["title"],
    sold_price_pence=int(float(price_value) * 100),
    year=year,
    make=make,
    model=model,
    url=item.get("itemWebUrl", ""),
)
```

### 3. `backend/app/adapters/ebay/stub.py`

Add realistic stub URLs to all 5 sold comps:

```python
SoldListing(..., url="https://www.ebay.co.uk/itm/sold_stub_001"),
SoldListing(..., url="https://www.ebay.co.uk/itm/sold_stub_002"),
# etc.
```

### 4. `backend/app/models/market_value.py`

Add a `sold_comp_urls` JSON column (list of URL strings):

```python
from sqlalchemy import JSON
sold_comp_urls: Mapped[list] = mapped_column(JSON, nullable=True, default=list)
```

### 5. `backend/app/services/market_valuator.py`

Collect URLs from sold comps and store in `MarketValue`:

```python
comp_urls = [c.url for c in sold_comps if c.url]
market_value = MarketValue(
    ...
    sold_comp_urls=comp_urls,
)
```

### 6. `backend/app/api/schemas.py`

Add to `OpportunityDetail`:

```python
sold_comp_urls: list[str] = []
```

### 7. `backend/app/api/opportunities.py`

Load and return `sold_comp_urls` from `MarketValue` in the detail endpoint:

```python
sold_comp_urls = market_value.sold_comp_urls or [] if market_value else []
return OpportunityDetail(
    ...
    sold_comp_urls=sold_comp_urls,
)
```

### 8. `backend/migrations/versions/014_add_sold_comp_urls.py`

```python
def upgrade():
    op.add_column("market_values", sa.Column("sold_comp_urls", postgresql.JSON, nullable=True))

def downgrade():
    op.drop_column("market_values", "sold_comp_urls")
```

---

## Acceptance Criteria

### 1. SoldListing has url field
```bash
cd backend
python -c "
from app.adapters.base import SoldListing
s = SoldListing(title='test', sold_price_pence=100000, year=2015, make='BMW', model='320d', url='https://ebay.co.uk/itm/123')
assert s.url == 'https://ebay.co.uk/itm/123'
print('SoldListing.url: OK')
"
```

### 2. Stub returns URLs
```bash
cd backend
python -c "
import asyncio
from app.adapters.ebay.stub import EbayStubAdapter
adapter = EbayStubAdapter()
comps = asyncio.run(adapter.search_sold('BMW', '320d', 2015))
assert all(c.url for c in comps), 'All stub comps must have a URL'
print('Stub sold comp URLs: OK')
"
```

### 3. OpportunityDetail schema has sold_comp_urls
```bash
cd backend
python -c "
from app.api.schemas import OpportunityDetail
import inspect
fields = OpportunityDetail.model_fields
assert 'sold_comp_urls' in fields
print('OpportunityDetail.sold_comp_urls: OK')
"
```

### 4. All previous smoke tests pass
```bash
cd backend
python -c "from app.models.market_value import MarketValue; print('MarketValue: OK')"
python -c "from app.services.market_valuator import estimate_market_value; print('market_valuator: OK')"
python -c "from app.api.schemas import OpportunityDetail; print('schemas: OK')"
```

---

## After Completion

- Commit: `feat: TASK_038 — sold comp URLs surfaced to API`
- Report: files changed

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_005, TASK_007*
