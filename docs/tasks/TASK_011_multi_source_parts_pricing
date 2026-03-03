# TASK_011 — Multi-Source Parts Pricing Service

## Context

Read `docs/GLOBAL_INSTRUCTIONS.md`, `docs/ARCHITECTURE.md`, and all files in
`backend/app/` before starting. Pay particular attention to:
- `backend/app/adapters/linkup/` — existing LinkUp adapter pattern
- `backend/app/models/` — existing DB models
- `backend/app/services/repair_estimation.py` — where parts pricing plugs in

## Objective

Build a multi-source parts pricing service that queries multiple UK suppliers in
parallel, aggregates results, deduplicates, and returns a ranked list of buy-ready
options sorted by total cost (part + delivery). This replaces the current LinkUp-only
parts pricing approach.

**Key principle:** Cache-first. Results cached 24hrs by `(part_name, make, model,
year_band)`. Scrapers only fire on cache miss. Adapter pattern — each supplier is
independent, failures are silent, system degrades gracefully.

---

## Architecture

```
PartsPricingService.get_prices(part_name, make, model, year, postcode)
        ↓
  Cache check → hit → return cached results immediately
        ↓ miss
  Run all adapters in parallel (asyncio.gather)
  ┌─────────────────────────────────────────────┐
  │ EbayPartsAdapter      (eBay Parts & Acc.)   │
  │ AutodocAdapter        (autodoc.co.uk)        │
  │ GSFAdapter            (gsfcarparts.com)      │
  │ CarParts4LessAdapter  (carparts4less.co.uk)  │
  │ CarPartsAdapter       (car-parts.co.uk)      │
  └─────────────────────────────────────────────┘
        ↓
  Aggregate → deduplicate by (supplier, part_number)
  Sort by total_cost_pence ASC
  Filter: UK delivery only, in-stock only
        ↓
  Cache results 24hrs
        ↓
  Return PartsPricingResult
```

---

## Data Model

### New DB table: `parts_price_cache`

```sql
CREATE TABLE parts_price_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR UNIQUE NOT NULL,
    -- key format: "{part_name_slug}_{make}_{model}_{year_band}"
    -- e.g. "clutch_kit_bmw_320d_2010s"
    results_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL  -- created_at + 24hrs
);
```

### New DB table: `fault_parts`

Maps detected fault types to standard part names to search for:

```sql
CREATE TABLE fault_parts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fault_type VARCHAR NOT NULL,
    -- e.g. "clutch_failure", "timing_chain", "dpf_blocked"
    part_names JSONB NOT NULL,
    -- e.g. ["clutch kit", "dual mass flywheel", "release bearing"]
    notes TEXT
);
```

Seed data (insert on startup if not exists):

| fault_type | part_names |
|---|---|
| clutch_failure | ["clutch kit", "dual mass flywheel", "clutch release bearing"] |
| timing_chain | ["timing chain kit", "timing chain tensioner"] |
| dpf_blocked | ["dpf filter", "dpf cleaning service"] |
| turbo_failure | ["turbocharger", "turbo actuator"] |
| egr_valve | ["egr valve", "egr cooler"] |
| injector_failure | ["fuel injector", "injector seal kit"] |
| head_gasket | ["head gasket kit", "cylinder head bolts"] |
| gearbox_fault | ["gearbox oil", "gearbox mount"] |
| suspension | ["shock absorber", "coil spring", "control arm"] |
| brake_failure | ["brake disc", "brake pads", "brake caliper"] |
| alternator | ["alternator"] |
| starter_motor | ["starter motor"] |
| water_pump | ["water pump", "thermostat"] |
| cambelt | ["cambelt kit", "water pump"] |

---

## Pydantic Models

```python
# backend/app/schemas/parts_pricing.py

from pydantic import BaseModel
from typing import Optional

class PartResult(BaseModel):
    supplier: str                    # "eBay", "Autodoc", "GSF", etc.
    supplier_logo_key: str           # key for mobile logo lookup
    part_description: str
    part_number: Optional[str]
    condition: str                   # "new" | "reconditioned" | "used"
    base_price_pence: int
    delivery_pence: int              # 0 if free
    total_cost_pence: int            # base + delivery
    availability: str                # "in_stock" | "unknown"
    url: str                         # direct product link
    price_confidence: str            # "live" | "estimated"
    # "live" = scraped directly from page
    # "estimated" = from search summary, may be stale

class PartsPricingResult(BaseModel):
    part_name: str
    results: list[PartResult]        # sorted by total_cost_pence ASC
    cheapest_pence: Optional[int]
    sourced_at: str                  # ISO timestamp
    cache_hit: bool
```

---

## Service Implementation

### `backend/app/services/parts_pricing.py`

```python
class PartsPricingService:

    async def get_prices(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
        postcode: str = "LE4 8JF"  # default to Ketan's location
    ) -> PartsPricingResult:
        
        cache_key = self._build_cache_key(part_name, make, model, year)
        
        # 1. Cache check
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        # 2. Run all adapters in parallel, fail silently
        results = await asyncio.gather(
            self.ebay_adapter.search(part_name, make, model, year),
            self.autodoc_adapter.search(part_name, make, model, year),
            self.gsf_adapter.search(part_name, make, model, year),
            self.carparts4less_adapter.search(part_name, make, model, year),
            self.carparts_adapter.search(part_name, make, model, year),
            return_exceptions=True  # never raise, log and continue
        )
        
        # 3. Flatten, filter exceptions, deduplicate
        all_parts = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Parts adapter error: {result}")
                continue
            all_parts.extend(result)
        
        # 4. Filter UK only, in-stock, deduplicate
        filtered = self._filter_and_deduplicate(all_parts)
        
        # 5. Sort by total cost
        sorted_parts = sorted(filtered, key=lambda x: x.total_cost_pence)
        
        # 6. Cache 24hrs
        await self._cache_results(cache_key, sorted_parts)
        
        return PartsPricingResult(
            part_name=part_name,
            results=sorted_parts,
            cheapest_pence=sorted_parts[0].total_cost_pence if sorted_parts else None,
            sourced_at=datetime.utcnow().isoformat(),
            cache_hit=False
        )
    
    def _build_cache_key(self, part_name, make, model, year) -> str:
        year_band = f"{(year // 10) * 10}s"  # 2015 → "2010s"
        slug = re.sub(r'[^a-z0-9]', '_', part_name.lower())
        return f"{slug}_{make.lower()}_{model.lower()}_{year_band}"
```

---

## Adapter Specifications

Each adapter implements:
```python
class BasePartsAdapter:
    async def search(
        self, 
        part_name: str, 
        make: str, 
        model: str, 
        year: int
    ) -> list[PartResult]:
        raise NotImplementedError
```

### 1. EbayPartsAdapter

- Uses eBay Browse API (same credentials as listing ingestion)
- Category: `33743` (Car Parts & Accessories, UK)
- Query: `f"{make} {model} {year} {part_name}"`
- Filters:
  - `filter=itemLocationCountry:GB,deliveryCountry:GB`
  - `filter=conditions:{NEW|USED|VERY_GOOD}` — all conditions
- Extract: `price.value`, `shippingOptions[0].shippingCost.value`, `itemWebUrl`
- `price_confidence: "live"` — prices are real-time from eBay API
- Return top 5 results sorted by total cost
- **Use stub when `EBAY_STUB=true`**

### 2. AutodocAdapter

- Target: `https://www.autodoc.co.uk/search?query={part_name}+{make}+{model}+{year}`
- Autodoc has consistent HTML structure — product cards with class `listing-item`
- Extract: product title, price (`.product-price__value`), part number, URL
- Delivery: Autodoc charges £3.99 standard UK delivery — hardcode this
- `price_confidence: "live"` — scraped directly
- Return top 3 results
- Timeout: 5 seconds. On timeout return empty list, log warning.
- Use `httpx` async client with headers mimicking a real browser:
  ```python
  headers = {
      "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      "Accept-Language": "en-GB,en;q=0.9",
      "Accept": "text/html,application/xhtml+xml"
  }
  ```

### 3. GSFAdapter

- Target: `https://www.gsfcarparts.com/search?q={part_name}+{make}+{model}+{year}`
- GSF has consistent product card HTML — `.product-card` elements
- Extract: title, price, part number, URL
- Delivery: GSF offers free delivery over £25, else £3.95 — use £0 if price > 2500p
- `price_confidence: "live"`
- Return top 3 results
- Timeout: 5 seconds

### 4. CarParts4LessAdapter

- Target: `https://www.carparts4less.co.uk/search.aspx?q={part_name}+{make}+{model}`
- Extract product cards, price, part number
- Delivery: free over £30, else £2.99
- `price_confidence: "live"`
- Return top 3 results
- Timeout: 5 seconds

### 5. CarPartsAdapter (breakers yards)

- Target: `https://www.car-parts.co.uk/parts/{part_name_slug}/{make}/{model}/{year}/`
- Used/reconditioned parts from breakers yards across UK
- Condition: always `"used"` or `"reconditioned"`
- Extract: price, supplier name, location, URL
- `price_confidence: "live"`
- Return top 3 results
- Timeout: 5 seconds

---

## Integration with Repair Estimation

In `backend/app/services/repair_estimation.py`, after fault detection:

```python
# For each detected fault:
fault_type = detected_fault.issue  # e.g. "clutch_failure"

# Look up part names for this fault
part_names = await self._get_part_names_for_fault(fault_type)

# Get prices for each part
for part_name in part_names:
    pricing = await parts_pricing_service.get_prices(
        part_name=part_name,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        postcode=config.USER_POSTCODE  # env var, default "LE4 8JF"
    )
    # Store results, use cheapest_pence for profit calculation
```

### Profit calculation update

Replace static repair cost estimates with live parts data:

```
repair_cost_min = labour_cost_min + cheapest_parts_total
repair_cost_max = labour_cost_max + median_parts_total
repair_cost_mid = (repair_cost_min + repair_cost_max) / 2
```

Labour costs remain static estimates from the fault knowledge base (unchanged).

---

## New Environment Variables

```
USER_POSTCODE=LE4 8JF         # used for delivery calculation
PARTS_CACHE_TTL_HOURS=24      # default 24
SCRAPER_TIMEOUT_SECONDS=5     # per-adapter timeout
```

Add to Railway Variables and `.env.example`.

---

## API Response Update

The `GET /api/v1/opportunities/{id}` detail endpoint should now return parts pricing
data per fault:

```json
{
  "faults": [
    {
      "fault_type": "clutch_failure",
      "severity": "high",
      "parts": [
        {
          "part_name": "clutch kit",
          "results": [
            {
              "supplier": "CarParts4Less",
              "supplier_logo_key": "carparts4less",
              "part_description": "LUK Clutch Kit BMW 320d 2015",
              "condition": "new",
              "base_price_pence": 14000,
              "delivery_pence": 0,
              "total_cost_pence": 14000,
              "url": "https://www.carparts4less.co.uk/...",
              "price_confidence": "live"
            },
            {
              "supplier": "eBay",
              "supplier_logo_key": "ebay",
              "part_description": "BMW 320d Clutch Kit + Flywheel",
              "condition": "used",
              "base_price_pence": 8500,
              "delivery_pence": 500,
              "total_cost_pence": 9000,
              "url": "https://www.ebay.co.uk/itm/...",
              "price_confidence": "live"
            }
          ],
          "cheapest_pence": 9000
        }
      ]
    }
  ]
}
```

---

## Files to Create/Modify

| File | Action |
|---|---|
| `backend/app/services/parts_pricing.py` | Create — main service |
| `backend/app/adapters/parts/base.py` | Create — base adapter |
| `backend/app/adapters/parts/ebay.py` | Create — eBay Parts adapter |
| `backend/app/adapters/parts/autodoc.py` | Create — Autodoc scraper |
| `backend/app/adapters/parts/gsf.py` | Create — GSF scraper |
| `backend/app/adapters/parts/carparts4less.py` | Create — CP4L scraper |
| `backend/app/adapters/parts/car_parts.py` | Create — car-parts.co.uk scraper |
| `backend/app/adapters/parts/stub.py` | Create — stub returning realistic fake data |
| `backend/app/models/parts_price_cache.py` | Create — DB model |
| `backend/app/models/fault_parts.py` | Create — fault→parts mapping model |
| `backend/app/schemas/parts_pricing.py` | Create — Pydantic schemas |
| `backend/app/services/repair_estimation.py` | Modify — integrate parts pricing |
| `backend/app/api/opportunities.py` | Modify — include parts in detail response |
| `backend/requirements.txt` | Modify — add `httpx`, `beautifulsoup4`, `lxml` |
| `.env.example` | Modify — add new env vars |

---

## Smoke Tests

After implementation, verify:

```
1. Stub mode test:
   PARTS_STUB=true → get_prices() returns ≥3 fake results in <100ms

2. Cache test:
   Call get_prices() twice with same args
   Second call returns cache_hit=True and is faster

3. Adapter isolation test:
   Force AutodocAdapter to raise exception
   Service still returns results from other adapters

4. Sort order test:
   Results always sorted by total_cost_pence ASC

5. eBay UK filter test:
   No results with itemLocationCountry != GB

6. Integration test:
   GET /api/v1/opportunities/{id} includes parts array in fault objects

7. Profit calculation test:
   expected_profit uses cheapest_parts_total not static estimates
```

All 7 must pass. Commit: `feat: multi-source parts pricing service (TASK_011)`

---

## Notes

- Add `PARTS_STUB=true` to Railway variables alongside `EBAY_STUB=true` until
  scrapers are verified working in production
- Scrapers should be considered best-effort. If all scrapers fail, fall back to
  static repair cost estimates from the existing knowledge base — never fail the
  whole pipeline because of a parts pricing miss
- LinkUp is **removed** from parts pricing entirely. It remains for fault intelligence
  only (existing behaviour unchanged)
- Do not scrape more than 3 results per supplier — keep request volume low
- Respect robots.txt for each supplier — if they disallow scraping, skip that adapter
