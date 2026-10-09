"""
test_display_helpers.py

Unit tests for TASK_040 — helpers that turn stored data into what the app shows.

Run from backend/ directory:
    python -m pytest ../tests/unit/test_display_helpers.py -v
"""
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.adapters.ebay.listings import (
    _parse_from_title,
    extract_display_fields,
    upscale_ebay_image,
)
from app.api.opportunities import (
    card_fault_names,
    display_fault_name,
    parts_total_range,
    vehicle_display_name,
)
from app.api.schemas import PartResult, SupplierPrice
from app.services.location_service import haversine_miles, outward_code


def test_upscale_ebay_image():
    url = "https://i.ebayimg.com/images/g/abc/s-l225.jpg"
    assert upscale_ebay_image(url) == "https://i.ebayimg.com/images/g/abc/s-l1600.jpg"
    assert upscale_ebay_image("https://example.com/a.jpg") == "https://example.com/a.jpg"


def test_title_year_fallback_range():
    next_year = datetime.now(timezone.utc).year + 1
    assert _parse_from_title("1998 Ford Escort spares", None, None, 0)[2] == 1998
    assert _parse_from_title("2026 Kia Ceed non runner", None, None, 0)[2] == 2026
    assert _parse_from_title(f"Kia Ceed {next_year + 5} plate", None, None, 0)[2] == 0
    assert _parse_from_title("Golf 1600 engine 2015", None, None, 0)[2] == 2015


def test_extract_display_fields():
    fields = extract_display_fields({
        "image": {"imageUrl": "https://i.ebayimg.com/images/g/a/s-l225.jpg"},
        "additionalImages": [
            {"imageUrl": "https://i.ebayimg.com/images/g/b/s-l140.jpg"},
            {"imageUrl": "https://i.ebayimg.com/images/g/a/s-l500.jpg"},
        ],
        "itemLocation": {"city": "LEICESTER", "postalCode": "LE4****"},
        "itemCreationDate": "2026-10-09T07:12:00.000Z",
    })
    assert fields["image_urls"] == [
        "https://i.ebayimg.com/images/g/a/s-l1600.jpg",
        "https://i.ebayimg.com/images/g/b/s-l1600.jpg",
    ]
    assert fields["location_town"] == "Leicester"
    assert fields["listed_at"] == datetime(2026, 10, 9, 7, 12, tzinfo=timezone.utc)
    assert extract_display_fields({}) == {"image_urls": [], "location_town": None, "listed_at": None}


def test_display_fault_name():
    assert display_fault_name("timing_chain_failure") == "Timing chain"
    assert display_fault_name("dpf_fault") == "DPF"
    assert display_fault_name("egr_valve_failure") == "EGR valve"
    assert display_fault_name("clutch") == "Clutch"


def test_card_fault_names_most_severe_first_max_three():
    faults = [
        SimpleNamespace(issue="battery_failure", severity="low"),
        SimpleNamespace(issue="gearbox_failure", severity="critical"),
        SimpleNamespace(issue="clutch_failure", severity="medium"),
        SimpleNamespace(issue="turbo_failure", severity="high"),
    ]
    assert card_fault_names(faults) == ["Gearbox", "Turbo", "Clutch"]


def test_vehicle_display_name():
    v = SimpleNamespace(make="Volkswagen", model="golf r", year=2015, trim=None)
    assert vehicle_display_name(v, "x") == "2015 Volkswagen Golf R"
    v = SimpleNamespace(make="BMW", model="320d", year=2014, trim="SE")
    assert vehicle_display_name(v, "x") == "2014 BMW 320d SE"
    v = SimpleNamespace(make="BMW", model="320d", year=0, trim="d")
    assert vehicle_display_name(v, "x") == "BMW 320d"
    assert vehicle_display_name(None, "listing title") == "listing title"
    v = SimpleNamespace(make="Unknown", model="Unknown", year=0, trim=None)
    assert vehicle_display_name(v, "listing title") == "listing title"


def _part(*totals):
    return PartResult(
        part_name="p", part_category="c", quantity="1", is_consumable=False,
        suppliers=[
            SupplierPrice(supplier="s", price_pence=t, total_cost_pence=t, url="u", in_stock=True)
            for t in totals
        ],
    )


def test_parts_total_range_sums_per_part():
    parts = [_part(98000, 105000), _part(21500, 24000), _part(5500), _part()]
    assert parts_total_range(parts) == (125000, 134500)


def test_outward_code_and_distance():
    assert outward_code("LE4 8JF") == "LE4"
    assert outward_code("LE4****") == "LE4"
    assert outward_code("m4****") == "M4"
    assert outward_code("LE48JF") == "LE4"
    assert outward_code("SW1A1AA") == "SW1A"
    assert outward_code("LE4") == "LE4"
    assert outward_code("") is None
    leicester, coventry = (52.6620, -1.1180), (52.4080, -1.5100)
    assert 20 < haversine_miles(leicester, coventry) < 25


def test_inferred_vehicle_fields_fill_gaps_only():
    from app.services.problem_detector import _apply_inferred_vehicle_fields

    v = SimpleNamespace(make="Volkswagen", model="Unknown", year=0, mileage=None,
                        fuel_type="petrol", transmission=None, body_type=None)
    _apply_inferred_vehicle_fields(v, {
        "make": "Audi", "model": "Golf R", "year": 2015, "mileage": 84000,
        "fuel_type": "diesel", "transmission": "automatic", "body_type": None,
    })
    assert v.make == "Volkswagen"       # from eBay specifics: never overwritten
    assert v.fuel_type == "petrol"      # from eBay specifics: never overwritten
    assert v.model == "Golf R"
    assert v.year == 2015
    assert v.mileage == 84000
    assert v.transmission == "automatic"
    assert v.body_type is None


def test_inferred_vehicle_fields_reject_out_of_range():
    from app.services.problem_detector import _apply_inferred_vehicle_fields

    v = SimpleNamespace(make="Ford", model="Fiesta", year=0, mileage=None,
                        fuel_type=None, transmission=None, body_type=None)
    _apply_inferred_vehicle_fields(v, {"year": 2099, "mileage": 9_000_000})
    assert v.year == 0
    assert v.mileage is None
    _apply_inferred_vehicle_fields(v, {"year": "2015"})
    assert v.year == 0


def test_location_lookup_failures_are_retried_but_unknown_outcodes_are_cached():
    import asyncio
    from unittest.mock import patch

    import httpx

    from app.services import location_service as ls

    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/ZZ9"):
            return httpx.Response(404, json={"status": 404})
        if request.url.path.endswith("/XX1"):
            return httpx.Response(503)
        return httpx.Response(200, json={"result": {"latitude": 52.66, "longitude": -1.118}})

    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler))

    ls._cache.clear()
    ls._failed_at.clear()
    with patch.object(ls.settings, "ebay_stub", False), \
            patch.object(ls.httpx, "AsyncClient", client_factory):
        assert asyncio.run(ls._lookup_outcode("LE4")) == (52.66, -1.118)
        assert asyncio.run(ls._lookup_outcode("ZZ9")) is None
        assert asyncio.run(ls._lookup_outcode("XX1")) is None
        asyncio.run(ls._lookup_outcode("LE4"))
        asyncio.run(ls._lookup_outcode("ZZ9"))
        asyncio.run(ls._lookup_outcode("XX1"))
    assert calls.count("/outcodes/LE4") == 1   # cached
    assert calls.count("/outcodes/ZZ9") == 1   # 404 cached as unknown
    assert calls.count("/outcodes/XX1") == 1   # 503 backed off for an hour
    assert "XX1" not in ls._cache              # ...but not cached as unknown
    ls._cache.clear()
    ls._failed_at.clear()
