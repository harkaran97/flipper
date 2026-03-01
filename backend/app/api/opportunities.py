"""
opportunities.py

GET /opportunities  — ranked opportunity feed
GET /opportunities/{opportunity_id}  — full opportunity detail
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.schemas import (
    FaultDetail,
    FaultPartsBreakdown,
    OpportunityCard,
    OpportunityDetail,
    OpportunityFeedResponse,
    PartResult,
    SupplierPrice,
)
from app.models.common_problem import CommonProblem
from app.models.fault import DetectedFault
from app.models.fault_part import FaultPart
from app.models.listing import Listing
from app.models.market_value import MarketValue
from app.models.opportunity import Opportunity
from app.models.parts_search_result import PartsSearchResult
from app.models.vehicle import Vehicle

logger = logging.getLogger(__name__)

router = APIRouter()

OPPORTUNITY_CLASS_ORDER = {
    "strong": 0,
    "speculative": 1,
    "worth_a_look": 2,
}


def _format_card(opp: Opportunity, listing: Listing, vehicle: Vehicle | None) -> OpportunityCard:
    """Assemble an OpportunityCard from ORM rows."""
    return OpportunityCard(
        id=str(opp.id),
        listing_id=str(opp.listing_id),
        title=listing.title,
        make=vehicle.make if vehicle else "",
        model=vehicle.model if vehicle else "",
        year=vehicle.year if vehicle else None,
        listing_url=listing.url,
        listing_price_pence=opp.listing_price_pence,
        parts_cost_min_pence=opp.parts_cost_min_pence,
        parts_cost_max_pence=opp.parts_cost_max_pence,
        market_value_pence=opp.market_value_pence,
        true_profit_pence=opp.true_profit_pence,
        true_margin_pct=round(opp.true_margin_pct, 2),
        total_man_days=opp.total_man_days,
        opportunity_class=opp.opportunity_class,
        risk_level=opp.risk_level,
        write_off_category=opp.write_off_category,
        has_unpriced_faults=opp.has_unpriced_faults,
        profit_is_floor_estimate=opp.profit_is_floor_estimate,
        market_value_confidence=opp.market_value_confidence,
        market_value_comp_count=opp.market_value_comp_count,
        created_at=opp.created_at.isoformat(),
    )


@router.get("/opportunities", response_model=OpportunityFeedResponse)
async def get_opportunities(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    min_margin_pct: float = Query(default=0.0, ge=0.0),
    max_man_days: Optional[float] = Query(default=None),
    max_listing_price_pence: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> OpportunityFeedResponse:
    """Ranked opportunity feed, sorted by class then margin descending."""
    # Build base filter — never return EXCLUDE class
    filters = [
        Opportunity.opportunity_class != "exclude",
        Opportunity.true_margin_pct >= min_margin_pct,
    ]
    if max_man_days is not None:
        filters.append(Opportunity.total_man_days <= max_man_days)
    if max_listing_price_pence is not None:
        filters.append(Opportunity.listing_price_pence <= max_listing_price_pence)

    # Count total matching rows
    count_result = await session.execute(
        select(func.count()).select_from(Opportunity).where(*filters)
    )
    total = count_result.scalar_one()

    # Fetch opportunities — join Listing for title/url, ordering applied in Python
    # (SQLAlchemy case() for custom order would add complexity; sort in Python is fine
    # for personal-use scale)
    opp_result = await session.execute(
        select(Opportunity).where(*filters)
    )
    opps = opp_result.scalars().all()

    # Sort: class order ASC, then true_margin_pct DESC
    opps_sorted = sorted(
        opps,
        key=lambda o: (
            OPPORTUNITY_CLASS_ORDER.get(o.opportunity_class, 99),
            -o.true_margin_pct,
        ),
    )

    # Apply offset and limit after sorting
    page = opps_sorted[offset: offset + limit]

    # Batch-load listings and vehicles for the page
    listing_ids = [o.listing_id for o in page]
    if listing_ids:
        listing_result = await session.execute(
            select(Listing).where(Listing.id.in_(listing_ids))
        )
        listings_by_id = {l.id: l for l in listing_result.scalars().all()}

        vehicle_result = await session.execute(
            select(Vehicle).where(Vehicle.listing_id.in_(listing_ids))
        )
        vehicles_by_listing = {v.listing_id: v for v in vehicle_result.scalars().all()}
    else:
        listings_by_id = {}
        vehicles_by_listing = {}

    cards = []
    for opp in page:
        listing = listings_by_id.get(opp.listing_id)
        vehicle = vehicles_by_listing.get(opp.listing_id)
        if listing is None:
            logger.warning("Opportunity %s has no listing row — skipping", opp.id)
            continue
        cards.append(_format_card(opp, listing, vehicle))

    return OpportunityFeedResponse(
        opportunities=cards,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
async def get_opportunity_detail(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
) -> OpportunityDetail:
    """Full opportunity detail including faults, parts breakdown, and market data."""
    # Load opportunity
    try:
        import uuid
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp_result = await session.execute(
        select(Opportunity).where(Opportunity.id == opp_uuid)
    )
    opp = opp_result.scalar_one_or_none()

    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.opportunity_class == "exclude":
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Load listing
    listing_result = await session.execute(
        select(Listing).where(Listing.id == opp.listing_id)
    )
    listing = listing_result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Load vehicle
    vehicle_result = await session.execute(
        select(Vehicle).where(Vehicle.listing_id == opp.listing_id)
    )
    vehicle = vehicle_result.scalar_one_or_none()

    # Load detected faults
    faults_result = await session.execute(
        select(DetectedFault).where(DetectedFault.listing_id == opp.listing_id)
    )
    detected_faults = faults_result.scalars().all()

    # Load all CommonProblem rows for these fault types (for description + labour_days)
    fault_types = [f.issue for f in detected_faults]
    if fault_types:
        cp_result = await session.execute(
            select(CommonProblem).where(CommonProblem.fault_type.in_(fault_types))
        )
        common_problems_by_type = {cp.fault_type: cp for cp in cp_result.scalars().all()}
    else:
        common_problems_by_type = {}

    # Build FaultDetail list
    fault_details: list[FaultDetail] = []
    for fault in detected_faults:
        cp = common_problems_by_type.get(fault.issue)
        fault_details.append(FaultDetail(
            fault_type=fault.issue,
            severity=fault.severity,
            description=cp.description if cp else None,
            labour_days=cp.labour_days_default if cp else 1.0,
        ))

    # Load PartsSearchResult rows for this listing
    psr_result = await session.execute(
        select(PartsSearchResult).where(PartsSearchResult.listing_id == opp.listing_id)
    )
    all_psr = psr_result.scalars().all()
    # Group by fault_type → part_name → list of results
    psr_by_fault: dict[str, dict[str, list[PartsSearchResult]]] = {}
    for psr in all_psr:
        psr_by_fault.setdefault(psr.fault_type, {}).setdefault(psr.part_name, []).append(psr)

    # Load FaultPart rows for all fault types
    if fault_types:
        fp_result = await session.execute(
            select(FaultPart).where(FaultPart.fault_type.in_(fault_types))
        )
        fault_parts_by_type: dict[str, list[FaultPart]] = {}
        for fp in fp_result.scalars().all():
            fault_parts_by_type.setdefault(fp.fault_type, []).append(fp)
    else:
        fault_parts_by_type = {}

    # Assemble parts breakdown per fault
    parts_breakdown: list[FaultPartsBreakdown] = []
    for fault in detected_faults:
        fault_type = fault.issue
        fault_parts = fault_parts_by_type.get(fault_type, [])
        psr_for_fault = psr_by_fault.get(fault_type, {})

        part_results: list[PartResult] = []
        all_prices: list[int] = []

        for fp in fault_parts:
            psr_for_part = psr_for_fault.get(fp.part_name, [])
            suppliers = [
                SupplierPrice(
                    supplier=psr.supplier,
                    price_pence=psr.price_pence,
                    url=psr.url,
                    in_stock=psr.in_stock,
                )
                for psr in psr_for_part
            ]
            if psr_for_part:
                all_prices.extend(psr.price_pence for psr in psr_for_part if psr.in_stock)

            part_results.append(PartResult(
                part_name=fp.part_name,
                part_category=fp.part_category,
                quantity=fp.quantity,
                is_consumable=fp.is_consumable,
                suppliers=suppliers,
            ))

        fault_parts_total_min = min(all_prices) if all_prices else 0
        fault_parts_total_max = max(all_prices) if all_prices else 0

        parts_breakdown.append(FaultPartsBreakdown(
            fault_type=fault_type,
            parts=part_results,
            fault_parts_total_min_pence=fault_parts_total_min,
            fault_parts_total_max_pence=fault_parts_total_max,
        ))

    # Load market value for linkup_fallback_used
    mv_result = await session.execute(
        select(MarketValue).where(MarketValue.listing_id == opp.listing_id)
    )
    market_value = mv_result.scalar_one_or_none()
    linkup_fallback_used = market_value.linkup_fallback_used if market_value else False

    return OpportunityDetail(
        id=str(opp.id),
        listing_id=str(opp.listing_id),
        title=listing.title,
        make=vehicle.make if vehicle else "",
        model=vehicle.model if vehicle else "",
        year=vehicle.year if vehicle else None,
        listing_url=listing.url,
        listing_price_pence=opp.listing_price_pence,
        parts_cost_min_pence=opp.parts_cost_min_pence,
        parts_cost_max_pence=opp.parts_cost_max_pence,
        market_value_pence=opp.market_value_pence,
        true_profit_pence=opp.true_profit_pence,
        true_margin_pct=round(opp.true_margin_pct, 2),
        total_man_days=opp.total_man_days,
        opportunity_class=opp.opportunity_class,
        risk_level=opp.risk_level,
        write_off_category=opp.write_off_category,
        has_unpriced_faults=opp.has_unpriced_faults,
        unpriced_fault_types=opp.unpriced_fault_types or [],
        profit_is_floor_estimate=opp.profit_is_floor_estimate,
        market_value_confidence=opp.market_value_confidence,
        market_value_comp_count=opp.market_value_comp_count,
        created_at=opp.created_at.isoformat(),
        faults=fault_details,
        parts_breakdown=parts_breakdown,
        effort_cost_pence=opp.effort_cost_pence,
        day_rate_pence=opp.day_rate_pence,
        linkup_fallback_used=linkup_fallback_used,
    )
