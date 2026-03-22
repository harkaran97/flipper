from app.adapters.base import (
    BaseListingsAdapter,
    BasePartsAdapter,
    BaseSoldAdapter,
    PartListing,
    RawListing,
    SoldListing,
)


class EbayStubAdapter(BaseListingsAdapter, BaseSoldAdapter, BasePartsAdapter):
    # Vehicle data keyed by external_id, parsed from stub listing titles/descriptions.
    # Used by the ingestion worker to seed Vehicle rows so the estimation pipeline
    # can proceed without a real enrichment step.
    STUB_VEHICLE_DATA: dict[str, dict] = {
        "ebay_stub_001": {
            "make": "BMW",
            "model": "320d",
            "year": 2015,
            "engine_cc": 1995,
            "fuel_type": "diesel",
            "transmission": "manual",
            "trim": "d",
        },
        "ebay_stub_002": {
            "make": "Ford",
            "model": "Focus",
            "year": 2018,
            "engine_cc": 999,
            "fuel_type": "petrol",
            "transmission": "manual",
            "trim": "EcoBoost",
        },
        "ebay_stub_003": {
            "make": "Volkswagen",
            "model": "Golf",
            "year": 2016,
            "engine_cc": 1598,
            "fuel_type": "diesel",
            "transmission": "manual",
            "trim": "TDI",
        },
    }

    def __init__(self) -> None:
        self._call_count = 0

    @property
    def call_count(self) -> int:
        """Number of times search_listings has been called. Used in smoke tests."""
        return self._call_count

    async def search_listings(self, query: str, filters: dict) -> list[RawListing]:
        self._call_count += 1
        return [
            RawListing(
                external_id="ebay_stub_001",
                source="ebay",
                title="BMW 320d 2015 Spares or Repair - Timing Chain Failure",
                description=(
                    "2015 BMW 320d F30, 95k miles. Car has timing chain failure, "
                    "engine knocking on startup. Was running fine until last week. "
                    "Selling as spares or repair. No MOT. Cat N previously repaired. "
                    "Good tyres, full leather interior."
                ),
                price_pence=275000,
                postcode="B15 2TT",
                url="https://www.ebay.co.uk/itm/stub001",
                raw_json={"stub": True, "item_id": "ebay_stub_001"},
            ),
            RawListing(
                external_id="ebay_stub_002",
                source="ebay",
                title="Ford Focus 2018 1.0 EcoBoost Non Runner - Clutch Gone",
                description=(
                    "2018 Ford Focus 1.0 EcoBoost, 62k miles. Clutch has gone, "
                    "not driveable. Otherwise in great condition, full service history. "
                    "Needs new clutch and possibly flywheel. Selling as non-runner."
                ),
                price_pence=185000,
                postcode="M4 1HQ",
                url="https://www.ebay.co.uk/itm/stub002",
                raw_json={"stub": True, "item_id": "ebay_stub_002"},
            ),
            RawListing(
                external_id="ebay_stub_003",
                source="ebay",
                title="VW Golf 2016 1.6 TDI Spares Repair - Gearbox Fault",
                description=(
                    "2016 Volkswagen Golf 1.6 TDI, 78k miles. Gearbox fault, "
                    "grinding noise when selecting 3rd and 5th gear. Drives but "
                    "needs gearbox rebuild or replacement. MOT until June. "
                    "Damage to rear bumper from parking."
                ),
                price_pence=320000,
                postcode="LS1 4AP",
                url="https://www.ebay.co.uk/itm/stub003",
                raw_json={"stub": True, "item_id": "ebay_stub_003"},
            ),
        ]

    async def search_sold(self, make: str, model: str, year: int) -> list[SoldListing]:
        # Realistic UK spares/repair sold comps — median 380000p (£3,800)
        # Prices match STUB_SOLD_COMPS spec for TASK_006 tests
        return [
            SoldListing(
                title="BMW 320d SE spares repair",
                sold_price_pence=350000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title="BMW 320d M Sport cat n",
                sold_price_pence=420000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title="BMW 320d ES spares",
                sold_price_pence=380000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title="BMW 320d 2010 repair",
                sold_price_pence=395000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title="BMW 320d non runner sold",
                sold_price_pence=310000,
                year=year,
                make=make,
                model=model,
            ),
        ]

    async def search_parts(self, part_name: str, vehicle: str) -> list[PartListing]:
        return [
            PartListing(
                title=f"{part_name} for {vehicle} - OEM Quality",
                price_pence=8500,
                url="https://www.ebay.co.uk/itm/stub_part_001",
            ),
            PartListing(
                title=f"{part_name} for {vehicle} - Genuine Part",
                price_pence=12000,
                url="https://www.ebay.co.uk/itm/stub_part_002",
            ),
            PartListing(
                title=f"{part_name} for {vehicle} - Aftermarket",
                price_pence=5500,
                url="https://www.ebay.co.uk/itm/stub_part_003",
            ),
        ]
