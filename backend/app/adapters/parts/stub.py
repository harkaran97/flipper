"""
stub.py

Stub parts pricing adapter returning realistic fake data.
Used when PARTS_STUB=true. All adapters delegate to this in stub mode.
"""
import logging

from app.adapters.parts.base import BasePartsSupplierAdapter
from app.schemas.parts_pricing import PartResult

logger = logging.getLogger(__name__)

# Realistic UK parts pricing stub data keyed by normalised part name
_STUB_DATA: dict[str, list[dict]] = {
    "clutch kit": [
        {
            "supplier": "GSF Car Parts",
            "supplier_logo_key": "gsf",
            "part_description": "LUK Clutch Kit 3-Piece",
            "part_number": "LUK-623-3070-00",
            "condition": "new",
            "base_price_pence": 11200,
            "delivery_pence": 0,
            "url": "https://www.gsfcarparts.com/stub/clutch-kit",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "CarParts4Less",
            "supplier_logo_key": "carparts4less",
            "part_description": "Sachs Clutch Kit with DMF",
            "part_number": "SACHS-3000951879",
            "condition": "new",
            "base_price_pence": 14000,
            "delivery_pence": 0,
            "url": "https://www.carparts4less.co.uk/stub/clutch-kit",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "eBay",
            "supplier_logo_key": "ebay",
            "part_description": "BMW 320d Clutch Kit + Flywheel Used",
            "part_number": None,
            "condition": "used",
            "base_price_pence": 8500,
            "delivery_pence": 500,
            "url": "https://www.ebay.co.uk/itm/stub_clutch_001",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "dual mass flywheel": [
        {
            "supplier": "Autodoc",
            "supplier_logo_key": "autodoc",
            "part_description": "LUK Dual Mass Flywheel",
            "part_number": "LUK-415-0228-10",
            "condition": "new",
            "base_price_pence": 18500,
            "delivery_pence": 399,
            "url": "https://www.autodoc.co.uk/stub/dmf",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "car-parts.co.uk",
            "supplier_logo_key": "car_parts",
            "part_description": "Used Dual Mass Flywheel Low Miles",
            "part_number": None,
            "condition": "used",
            "base_price_pence": 6500,
            "delivery_pence": 1500,
            "url": "https://www.car-parts.co.uk/stub/dmf",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "timing chain kit": [
        {
            "supplier": "GSF Car Parts",
            "supplier_logo_key": "gsf",
            "part_description": "Timing Chain Kit with Guides & Tensioner",
            "part_number": "INA-559004810",
            "condition": "new",
            "base_price_pence": 8700,
            "delivery_pence": 0,
            "url": "https://www.gsfcarparts.com/stub/timing-chain",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "Autodoc",
            "supplier_logo_key": "autodoc",
            "part_description": "Febi Timing Chain Kit Complete",
            "part_number": "FEBI-45409",
            "condition": "new",
            "base_price_pence": 9200,
            "delivery_pence": 399,
            "url": "https://www.autodoc.co.uk/stub/timing-chain",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "eBay",
            "supplier_logo_key": "ebay",
            "part_description": "BMW N47 Timing Chain Kit OEM Quality",
            "part_number": None,
            "condition": "new",
            "base_price_pence": 7800,
            "delivery_pence": 299,
            "url": "https://www.ebay.co.uk/itm/stub_tc_001",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "turbocharger": [
        {
            "supplier": "car-parts.co.uk",
            "supplier_logo_key": "car_parts",
            "part_description": "Reconditioned Turbocharger Exchange Unit",
            "part_number": None,
            "condition": "reconditioned",
            "base_price_pence": 22000,
            "delivery_pence": 0,
            "url": "https://www.car-parts.co.uk/stub/turbo",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "eBay",
            "supplier_logo_key": "ebay",
            "part_description": "Garrett Turbocharger Remanufactured",
            "part_number": "GTB1749V",
            "condition": "reconditioned",
            "base_price_pence": 18500,
            "delivery_pence": 500,
            "url": "https://www.ebay.co.uk/itm/stub_turbo_001",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "head gasket set": [
        {
            "supplier": "CarParts4Less",
            "supplier_logo_key": "carparts4less",
            "part_description": "Elring Head Gasket Set Full",
            "part_number": "ELR-032500",
            "condition": "new",
            "base_price_pence": 7800,
            "delivery_pence": 0,
            "url": "https://www.carparts4less.co.uk/stub/head-gasket",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "Autodoc",
            "supplier_logo_key": "autodoc",
            "part_description": "Victor Reinz Head Gasket Kit",
            "part_number": "VR-02-36370-01",
            "condition": "new",
            "base_price_pence": 8900,
            "delivery_pence": 399,
            "url": "https://www.autodoc.co.uk/stub/head-gasket",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "dpf filter": [
        {
            "supplier": "GSF Car Parts",
            "supplier_logo_key": "gsf",
            "part_description": "DPF Diesel Particulate Filter OE Spec",
            "part_number": "MANN-PU825X",
            "condition": "new",
            "base_price_pence": 28000,
            "delivery_pence": 0,
            "url": "https://www.gsfcarparts.com/stub/dpf",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
    "shock absorber": [
        {
            "supplier": "GSF Car Parts",
            "supplier_logo_key": "gsf",
            "part_description": "Bilstein B4 Shock Absorber Front",
            "part_number": "BIL-19-229387",
            "condition": "new",
            "base_price_pence": 5800,
            "delivery_pence": 0,
            "url": "https://www.gsfcarparts.com/stub/shock",
            "availability": "in_stock",
            "price_confidence": "live",
        },
        {
            "supplier": "CarParts4Less",
            "supplier_logo_key": "carparts4less",
            "part_description": "Monroe Shock Absorber",
            "part_number": "MON-R16108",
            "condition": "new",
            "base_price_pence": 4200,
            "delivery_pence": 299,
            "url": "https://www.carparts4less.co.uk/stub/shock",
            "availability": "in_stock",
            "price_confidence": "live",
        },
    ],
}

_DEFAULT_STUB = [
    {
        "supplier": "GSF Car Parts",
        "supplier_logo_key": "gsf",
        "part_description": "OEM Quality Replacement Part",
        "part_number": None,
        "condition": "new",
        "base_price_pence": 5000,
        "delivery_pence": 0,
        "url": "https://www.gsfcarparts.com/stub/generic",
        "availability": "in_stock",
        "price_confidence": "estimated",
    },
    {
        "supplier": "eBay",
        "supplier_logo_key": "ebay",
        "part_description": "Used Part Good Condition",
        "part_number": None,
        "condition": "used",
        "base_price_pence": 2500,
        "delivery_pence": 350,
        "url": "https://www.ebay.co.uk/itm/stub_generic",
        "availability": "in_stock",
        "price_confidence": "estimated",
    },
    {
        "supplier": "Autodoc",
        "supplier_logo_key": "autodoc",
        "part_description": "Aftermarket Replacement",
        "part_number": None,
        "condition": "new",
        "base_price_pence": 6200,
        "delivery_pence": 399,
        "url": "https://www.autodoc.co.uk/stub/generic",
        "availability": "in_stock",
        "price_confidence": "estimated",
    },
]


def _make_part_results(raw_list: list[dict], part_name: str, make: str, model: str, year: int) -> list[PartResult]:
    """Build PartResult objects from stub dict data, enriching descriptions with vehicle info."""
    results = []
    for item in raw_list:
        desc = item["part_description"]
        if make and model and make.lower() not in desc.lower():
            desc = f"{make} {model} {year} {desc}"
        results.append(PartResult(
            supplier=item["supplier"],
            supplier_logo_key=item["supplier_logo_key"],
            part_description=desc,
            part_number=item.get("part_number"),
            condition=item["condition"],
            base_price_pence=item["base_price_pence"],
            delivery_pence=item["delivery_pence"],
            total_cost_pence=item["base_price_pence"] + item["delivery_pence"],
            availability=item["availability"],
            url=item["url"],
            price_confidence=item["price_confidence"],
        ))
    return sorted(results, key=lambda r: r.total_cost_pence)


class StubPartsAdapter(BasePartsSupplierAdapter):
    """Stub adapter returning realistic fake parts pricing data."""

    async def search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        logger.debug("StubPartsAdapter.search(%s, %s, %s, %d)", part_name, make, model, year)
        key = part_name.lower().strip()
        raw = _STUB_DATA.get(key, _DEFAULT_STUB)
        return _make_part_results(raw, part_name, make, model, year)
