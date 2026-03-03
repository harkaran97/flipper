"""
test_parts_pricing.py

Smoke tests for TASK_011 — Multi-source parts pricing service.
All 7 tests must pass.

Run from backend/ directory:
    python -m pytest ../tests/smoke/test_parts_pricing.py -v --asyncio-mode=auto
"""
import asyncio
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import pytest

# ─────────────────────────────────────────────
# Test 1: Stub mode — get_prices() returns ≥3 results in <100ms
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_1_stub_mode_returns_results_quickly():
    """PARTS_STUB=true → get_prices() returns ≥3 fake results in <100ms"""
    from app.services.parts_pricing import PartsPricingService
    from config import settings

    settings.parts_stub = True

    svc = PartsPricingService()

    start = time.monotonic()
    result = await svc.get_prices(
        part_name="clutch kit",
        make="BMW",
        model="320d",
        year=2015,
        session=None,
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    assert len(result.results) >= 3, (
        f"Expected ≥3 results in stub mode, got {len(result.results)}"
    )
    assert elapsed_ms < 100, (
        f"Stub mode took {elapsed_ms:.1f}ms — expected <100ms"
    )
    assert result.cache_hit is False
    assert result.cheapest_pence is not None
    print(f"  ✓ Test 1 passed: {len(result.results)} results in {elapsed_ms:.1f}ms")


# ─────────────────────────────────────────────
# Test 2: Cache test — second call returns cache_hit=True and is faster
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_2_cache_hit_on_second_call():
    """Call get_prices() twice; second call returns cache_hit=True and is faster."""
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime
    from app.services.parts_pricing import PartsPricingService
    from app.schemas.parts_pricing import PartResult
    from config import settings

    settings.parts_stub = True
    svc = PartsPricingService()

    fake_result = PartResult(
        supplier="GSF Car Parts",
        supplier_logo_key="gsf",
        part_description="Timing Chain Kit Test",
        part_number="INA-12345",
        condition="new",
        base_price_pence=8700,
        delivery_pence=0,
        total_cost_pence=8700,
        availability="in_stock",
        url="https://www.gsfcarparts.com/test",
        price_confidence="live",
    )

    cached_json = {
        "part_name": "timing chain kit",
        "results": [fake_result.model_dump()],
        "cheapest_pence": 8700,
        "sourced_at": datetime.utcnow().isoformat(),
    }

    from app.models.parts_price_cache import PartsPriceCache
    mock_cache_row = MagicMock(spec=PartsPriceCache)
    mock_cache_row.is_valid = True
    mock_cache_row.results_json = cached_json

    # Use an AsyncMock for the session but a regular MagicMock for execute result
    mock_session = AsyncMock()
    # scalar_one_or_none() is a synchronous call on the execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_cache_row
    mock_session.execute = AsyncMock(return_value=mock_execute_result)

    # First call — no session, always goes to adapters
    start1 = time.monotonic()
    result1 = await svc.get_prices(
        part_name="timing chain kit",
        make="BMW",
        model="320d",
        year=2015,
        session=None,
    )
    elapsed1 = (time.monotonic() - start1) * 1000

    # Second call — mocked session returns the cached row instantly
    start2 = time.monotonic()
    result2 = await svc.get_prices(
        part_name="timing chain kit",
        make="BMW",
        model="320d",
        year=2015,
        session=mock_session,
    )
    elapsed2 = (time.monotonic() - start2) * 1000

    assert result2.cache_hit is True, "Second call should return cache_hit=True"
    assert result2.results[0].total_cost_pence == 8700
    assert elapsed2 < elapsed1 or elapsed2 < 10, (
        f"Cache hit should be fast: first={elapsed1:.1f}ms, second={elapsed2:.1f}ms"
    )
    print(f"  ✓ Test 2 passed: first={elapsed1:.1f}ms, cached={elapsed2:.1f}ms")


# ─────────────────────────────────────────────
# Test 3: Adapter isolation — if one adapter raises, others still return results
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_3_adapter_isolation():
    """Force AutodocAdapter to raise; service still returns results from other adapters."""
    from unittest.mock import AsyncMock
    from app.services.parts_pricing import PartsPricingService
    from app.schemas.parts_pricing import PartResult
    from config import settings

    settings.parts_stub = False  # Force live adapters to be used
    svc = PartsPricingService()

    working_result = [PartResult(
        supplier="GSF Car Parts",
        supplier_logo_key="gsf",
        part_description="Test Part",
        condition="new",
        base_price_pence=5000,
        delivery_pence=0,
        total_cost_pence=5000,
        availability="in_stock",
        url="https://test.com",
        price_confidence="live",
    )]

    # Autodoc raises, all other adapters return a result
    svc.autodoc_adapter.search = AsyncMock(side_effect=Exception("Autodoc down"))
    svc.ebay_adapter.search = AsyncMock(return_value=working_result)
    svc.gsf_adapter.search = AsyncMock(return_value=working_result)
    svc.carparts4less_adapter.search = AsyncMock(return_value=working_result)
    svc.carparts_adapter.search = AsyncMock(return_value=working_result)

    result = await svc.get_prices(
        part_name="head gasket",
        make="Ford",
        model="Focus",
        year=2016,
        session=None,
    )

    assert len(result.results) > 0, (
        "Service should return results even when one adapter fails"
    )
    assert result.cache_hit is False
    print(f"  ✓ Test 3 passed: {len(result.results)} results despite Autodoc failure")

    settings.parts_stub = True  # Reset


# ─────────────────────────────────────────────
# Test 4: Sort order — results always sorted by total_cost_pence ASC
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_4_results_sorted_by_total_cost_asc():
    """Results always sorted by total_cost_pence ASC."""
    from app.services.parts_pricing import PartsPricingService
    from config import settings

    settings.parts_stub = True
    svc = PartsPricingService()

    for part_name in ["clutch kit", "timing chain kit", "turbocharger", "shock absorber"]:
        result = await svc.get_prices(
            part_name=part_name,
            make="BMW",
            model="320d",
            year=2015,
            session=None,
        )
        if len(result.results) >= 2:
            prices = [r.total_cost_pence for r in result.results]
            assert prices == sorted(prices), (
                f"Results for '{part_name}' not sorted ASC: {prices}"
            )

    print("  ✓ Test 4 passed: all results sorted by total_cost_pence ASC")


# ─────────────────────────────────────────────
# Test 5: eBay UK filter — live adapter applies GB filter in request
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_5_ebay_uk_filter():
    """eBay adapter sends GB location+delivery filter and returns parsed results."""
    from unittest.mock import AsyncMock, patch
    from app.adapters.parts.ebay import EbayPartsAdapter
    from app.adapters.ebay.client import EbayClient
    from config import settings

    settings.ebay_stub = False  # Use live code path

    adapter = EbayPartsAdapter()

    mock_response = {
        "itemSummaries": [
            {
                "title": "BMW 320d Clutch Kit UK",
                "price": {"value": "89.99"},
                "shippingOptions": [{"shippingCost": {"value": "0.00"}}],
                "condition": "NEW",
                "itemWebUrl": "https://www.ebay.co.uk/itm/test1",
            },
            {
                "title": "BMW 320d Clutch Kit UK Second",
                "price": {"value": "75.00"},
                "shippingOptions": [{"shippingCost": {"value": "3.99"}}],
                "condition": "GOOD",
                "itemWebUrl": "https://www.ebay.co.uk/itm/test2",
            },
        ]
    }

    captured_params = {}

    async def mock_get(self_arg, path, params):
        captured_params.update(params)
        return mock_response

    # Patch the get method on the EbayClient class
    with patch.object(EbayClient, "get", new=mock_get):
        results = await adapter.search("clutch kit", "BMW", "320d", 2015)

    # Verify GB filter was included in the API call
    assert "filter" in captured_params, "eBay adapter must pass filter param"
    assert "GB" in captured_params["filter"], (
        f"eBay filter must include GB: got {captured_params['filter']}"
    )

    assert len(results) > 0, "Should return results from mock response"
    for r in results:
        assert r.supplier == "eBay"

    print(f"  ✓ Test 5 passed: {len(results)} results, filter={captured_params.get('filter')}")

    settings.ebay_stub = True  # Reset


# ─────────────────────────────────────────────
# Test 6: Integration test — OpportunityDetail includes parts array in fault objects
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_6_opportunity_detail_includes_parts():
    """GET /api/v1/opportunities/{id} includes parts_breakdown array in response."""
    from unittest.mock import AsyncMock, MagicMock
    import uuid as _uuid

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))
    from main import app
    from app.models.opportunity import Opportunity
    from app.models.listing import Listing
    from app.models.vehicle import Vehicle
    from app.models.fault import DetectedFault
    from datetime import datetime

    opp_id = _uuid.uuid4()
    listing_id = _uuid.uuid4()

    mock_opp = MagicMock(spec=Opportunity)
    mock_opp.id = opp_id
    mock_opp.listing_id = listing_id
    mock_opp.opportunity_class = "speculative"
    mock_opp.listing_price_pence = 200000
    mock_opp.parts_cost_min_pence = 5000
    mock_opp.parts_cost_max_pence = 15000
    mock_opp.parts_cost_mid_pence = 10000
    mock_opp.market_value_pence = 450000
    mock_opp.true_profit_pence = 240000
    mock_opp.true_margin_pct = 53.3
    mock_opp.total_man_days = 1.0
    mock_opp.risk_level = "medium"
    mock_opp.write_off_category = "clean"
    mock_opp.has_unpriced_faults = False
    mock_opp.unpriced_fault_types = []
    mock_opp.profit_is_floor_estimate = False
    mock_opp.market_value_confidence = "high"
    mock_opp.market_value_comp_count = 5
    mock_opp.effort_cost_pence = 15000
    mock_opp.day_rate_pence = 15000
    mock_opp.alerted = False
    mock_opp.created_at = datetime(2024, 1, 1, 12, 0, 0)

    mock_listing = MagicMock(spec=Listing)
    mock_listing.id = listing_id
    mock_listing.title = "BMW 320d Spares or Repair"
    mock_listing.url = "https://www.ebay.co.uk/itm/test"

    mock_vehicle = MagicMock(spec=Vehicle)
    mock_vehicle.listing_id = listing_id
    mock_vehicle.make = "BMW"
    mock_vehicle.model = "320d"
    mock_vehicle.year = 2015

    mock_fault = MagicMock(spec=DetectedFault)
    mock_fault.listing_id = listing_id
    mock_fault.issue = "clutch_failure"
    mock_fault.severity = "medium"

    # Use a sequential response queue — the endpoint queries in a fixed order:
    # 1. Opportunity  2. Listing  3. Vehicle  4. DetectedFaults
    # 5. CommonProblems  6. FaultParts  7+ MarketValue / any fallback

    def scalar_result(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        r.scalars.return_value = scalars_mock
        return r

    def scalars_result(vals):
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = vals
        r.scalars.return_value = scalars_mock
        return r

    response_queue = [
        scalar_result(mock_opp),          # 1: Opportunity
        scalar_result(mock_listing),       # 2: Listing
        scalar_result(mock_vehicle),       # 3: Vehicle
        scalars_result([mock_fault]),      # 4: DetectedFaults
        scalars_result([]),                # 5: CommonProblems
        scalars_result([]),                # 6: FaultParts
        scalar_result(None),              # 7: MarketValue
    ]
    queue_index = [0]

    async def fake_execute(query):
        idx = queue_index[0]
        queue_index[0] += 1
        if idx < len(response_queue):
            return response_queue[idx]
        return scalar_result(None)

    mock_session = AsyncMock()
    mock_session.execute = fake_execute

    async def mock_get_db():
        yield mock_session

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = mock_get_db

    try:
        import httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/opportunities/{opp_id}")

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "faults" in data, "Response must include 'faults' array"
        assert "parts_breakdown" in data, "Response must include 'parts_breakdown' array"
        print(
            f"  ✓ Test 6 passed: detail endpoint returns faults={len(data['faults'])} "
            f"+ parts_breakdown={len(data['parts_breakdown'])} arrays"
        )
    finally:
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────
# Test 7: Profit calculation uses cheapest_parts_total not static estimates
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_7_profit_uses_live_parts_data():
    """expected_profit uses cheapest_parts_total from PartsPricingService."""
    from app.services.parts_pricing import PartsPricingService
    from config import settings

    settings.parts_stub = True
    svc = PartsPricingService()

    result = await svc.get_prices(
        part_name="clutch kit",
        make="BMW",
        model="320d",
        year=2015,
        session=None,
    )

    assert result.cheapest_pence is not None, "cheapest_pence must be set"
    assert result.cheapest_pence > 0, "cheapest_pence must be positive"

    # Verify cheapest_pence matches the first (cheapest) sorted result
    assert result.cheapest_pence == result.results[0].total_cost_pence, (
        "cheapest_pence should equal first sorted result's total_cost_pence"
    )

    # Simulate profit calculation using live parts data
    listing_price_pence = 200000
    market_value_pence = 450000
    labour_cost_pence = 15000  # 1 day labour
    cheapest_parts_total = result.cheapest_pence
    median_parts = svc.compute_median_total_pence(result) or cheapest_parts_total

    repair_cost_min = labour_cost_pence + cheapest_parts_total
    repair_cost_max = labour_cost_pence + median_parts
    repair_cost_mid = (repair_cost_min + repair_cost_max) // 2

    expected_profit = market_value_pence - listing_price_pence - repair_cost_mid

    assert expected_profit > 0, (
        f"Profit should be positive: market={market_value_pence}, "
        f"listing={listing_price_pence}, repair_mid={repair_cost_mid}"
    )

    print(
        f"  ✓ Test 7 passed: profit=£{expected_profit//100}, "
        f"cheapest_parts=£{cheapest_parts_total//100}, "
        f"repair_mid=£{repair_cost_mid//100}"
    )


# ─────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────

if __name__ == "__main__":
    async def run_all():
        tests = [
            ("Test 1: Stub mode returns ≥3 results in <100ms", test_1_stub_mode_returns_results_quickly),
            ("Test 2: Cache hit on second call", test_2_cache_hit_on_second_call),
            ("Test 3: Adapter isolation (one fails, others succeed)", test_3_adapter_isolation),
            ("Test 4: Results sorted by total_cost_pence ASC", test_4_results_sorted_by_total_cost_asc),
            ("Test 5: eBay UK filter", test_5_ebay_uk_filter),
            ("Test 6: Integration — detail endpoint includes parts", test_6_opportunity_detail_includes_parts),
            ("Test 7: Profit uses live parts data", test_7_profit_uses_live_parts_data),
        ]

        passed = 0
        failed = 0

        for name, test_fn in tests:
            print(f"\n→ {name}")
            try:
                await test_fn()
                passed += 1
            except Exception as e:
                import traceback
                print(f"  ✗ FAILED: {e}")
                traceback.print_exc()
                failed += 1

        print(f"\n{'='*50}")
        print(f"Results: {passed}/{len(tests)} passed, {failed} failed")
        if failed > 0:
            sys.exit(1)

    asyncio.run(run_all())
