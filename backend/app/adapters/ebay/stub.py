from app.adapters.base import (
    BaseListingsAdapter,
    BasePartsAdapter,
    BaseSoldAdapter,
    PartListing,
    RawListing,
    SoldListing,
)


class EbayStubAdapter(BaseListingsAdapter, BaseSoldAdapter, BasePartsAdapter):
    async def search_listings(self, query: str, filters: dict) -> list[RawListing]:
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
        return [
            SoldListing(
                title=f"{make} {model} {year} - Good Condition",
                sold_price_pence=750000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title=f"{make} {model} {year} - Low Mileage",
                sold_price_pence=820000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title=f"{make} {model} {year} - Full Service History",
                sold_price_pence=690000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title=f"{make} {model} {year} - 1 Owner",
                sold_price_pence=780000,
                year=year,
                make=make,
                model=model,
            ),
            SoldListing(
                title=f"{make} {model} {year} - Recently Serviced",
                sold_price_pence=710000,
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
