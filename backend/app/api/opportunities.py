"""
opportunities.py

GET /opportunities  — ranked opportunity feed
GET /opportunities/{opportunity_id}  — full opportunity detail
"""
import logging
import re
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ebay.listings import upscale_ebay_image
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
from app.models.parts_price_cache import PartsPriceCache
from app.models.vehicle import Vehicle
from app.services.location_service import outward_code
from app.services.parts_pricing import PartsPricingService
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

OPPORTUNITY_CLASS_ORDER = {
    "strong": 0,
    "speculative": 1,
    "worth_a_look": 2,
}

_parts_pricing_svc = PartsPricingService()


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_MAX_CARD_FAULT_NAMES = 3


_ACRONYMS = {
    "abs", "ac", "cv", "cvt", "dmf", "dpf", "dsg", "ecu", "egr", "eml", "srs", "tpms",
}


def display_fault_name(fault_type: str) -> str:
    """"timing_chain_failure" → "Timing chain", "dpf_fault" → "DPF"."""
    words = fault_type.replace("_", " ").strip()
    words = re.sub(r"\s+(failure|fault|issue|problem)$", "", words, flags=re.IGNORECASE)
    if not words:
        return fault_type
    tokens = [w.upper() if w.lower() in _ACRONYMS else w for w in words.split()]
    if tokens[0] == tokens[0].lower():
        tokens[0] = tokens[0][:1].upper() + tokens[0][1:]
    return " ".join(tokens)


def vehicle_display_name(vehicle: Vehicle | None, fallback_title: str) -> str:
    """
    "2015 Volkswagen Golf R". Keeps eBay's casing for the model; title-cases it
    only when it is entirely lower case ("golf" → "Golf", "320d" unchanged).
    Falls back to the listing title when make or model is unknown.
    """
    if vehicle is None or not vehicle.make or vehicle.make == "Unknown" \
            or not vehicle.model or vehicle.model == "Unknown":
        return fallback_title
    model = vehicle.model
    if model.islower() and not any(ch.isdigit() for ch in model):
        model = model.title()
    parts = [str(vehicle.year)] if vehicle.year else []
    parts.append(vehicle.make)
    if not model.lower().startswith(vehicle.make.lower()):
        parts.append(model)
    else:
        parts[-1] = model
    if vehicle.trim and vehicle.trim.lower() not in model.lower():
        parts.append(vehicle.trim)
    return " ".join(parts)


def listing_image_urls(listing: Listing) -> list[str]:
    """Stored photos, else the summary image already in raw_json (pre-TASK_040 rows)."""
    if listing.image_urls:
        return list(listing.image_urls)
    raw_image = ((listing.raw_json or {}).get("image") or {}).get("imageUrl")
    return [upscale_ebay_image(raw_image)] if raw_image else []


def listing_location(listing: Listing) -> str | None:
    """Town, else the outward postcode ("LE4")."""
    return listing.location_town or outward_code(listing.postcode)


def listing_listed_at(listing: Listing) -> str:
    """When the listing went up on eBay, else when we first saw it."""
    if listing.listed_at is not None:
        return listing.listed_at.isoformat()
    raw_created = (listing.raw_json or {}).get("itemCreationDate")
    return raw_created or listing.created_at.isoformat()


def card_fault_names(faults: list[DetectedFault]) -> list[str]:
    """Up to three display names, most severe first, without duplicates."""
    names: list[str] = []
    for fault in sorted(faults, key=lambda f: SEVERITY_ORDER.get(f.severity, 99)):
        name = display_fault_name(fault.issue)
        if name not in names:
            names.append(name)
    return names[:_MAX_CARD_FAULT_NAMES]


def parts_total_range(parts: list[PartResult]) -> tuple[int, int]:
    """
    Totals for a fault's parts: min = sum of the cheapest supplier per part,
    max = sum of the dearest supplier per part. Parts with no price are skipped.
    """
    total_min = 0
    total_max = 0
    for part in parts:
        if not part.suppliers:
            continue
        totals = [s.total_cost_pence for s in part.suppliers]
        total_min += min(totals)
        total_max += max(totals)
    return total_min, total_max


def _format_card(
    opp: Opportunity,
    listing: Listing,
    vehicle: Vehicle | None,
    faults: list[DetectedFault],
) -> OpportunityCard:
    """Assemble an OpportunityCard from ORM rows."""
    images = listing_image_urls(listing)
    return OpportunityCard(
        id=str(opp.id),
        listing_id=str(opp.listing_id),
        title=listing.title,
        make=vehicle.make if vehicle else "",
        model=vehicle.model if vehicle else "",
        year=vehicle.year if vehicle and vehicle.year else None,
        listing_url=listing.url,
        vehicle_name=vehicle_display_name(vehicle, listing.title),
        image_url=images[0] if images else None,
        mileage=vehicle.mileage if vehicle else None,
        location=listing_location(listing),
        distance_miles=round(listing.distance_miles) if listing.distance_miles is not None else None,
        listed_at=listing_listed_at(listing),
        fault_names=card_fault_names(faults),
        listing_price_pence=opp.listing_price_pence,
        parts_cost_min_pence=opp.parts_cost_min_pence,
        parts_cost_max_pence=opp.parts_cost_max_pence,
        fix_cost_pence=opp.parts_cost_mid_pence + opp.effort_cost_pence,
        market_value_pence=opp.market_value_pence,
        true_profit_pence=opp.true_profit_pence,
        true_margin_pct=round(opp.true_margin_pct, 2),
        total_man_days=opp.total_man_days,
        opportunity_class=opp.opportunity_class,
        risk_level=opp.risk_level,
        write_off_category=opp.write_off_category,
        has_unpriced_faults=opp.has_unpriced_faults,
        profit_is_floor_estimate=opp.profit_is_floor_estimate,
        profit_is_best_case=len(faults) == 0,
        market_value_confidence=opp.market_value_confidence,
        market_value_comp_count=opp.market_value_comp_count,
        created_at=opp.created_at.isoformat(),
        saved=opp.saved,
        marked_as_build=opp.marked_as_build,
    )


async def _build_cards(session: AsyncSession, opps: list[Opportunity]) -> list[OpportunityCard]:
    """Batch-load listings, vehicles and faults for these opportunities and format cards."""
    listing_ids = [o.listing_id for o in opps]
    if not listing_ids:
        return []

    listing_result = await session.execute(
        select(Listing).where(Listing.id.in_(listing_ids))
    )
    listings_by_id = {l.id: l for l in listing_result.scalars().all()}

    vehicle_result = await session.execute(
        select(Vehicle).where(Vehicle.listing_id.in_(listing_ids))
    )
    vehicles_by_listing = {v.listing_id: v for v in vehicle_result.scalars().all()}

    fault_result = await session.execute(
        select(DetectedFault).where(DetectedFault.listing_id.in_(listing_ids))
    )
    faults_by_listing: dict = {}
    for fault in fault_result.scalars().all():
        faults_by_listing.setdefault(fault.listing_id, []).append(fault)

    cards = []
    for opp in opps:
        listing = listings_by_id.get(opp.listing_id)
        if listing is None:
            logger.warning("Opportunity %s has no listing row — skipping", opp.id)
            continue
        cards.append(_format_card(
            opp, listing,
            vehicles_by_listing.get(opp.listing_id),
            faults_by_listing.get(opp.listing_id, []),
        ))
    return cards


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
        Opportunity.created_at >= func.now() - timedelta(days=14),
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

    cards = await _build_cards(session, page)

    return OpportunityFeedResponse(
        opportunities=cards,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/opportunities/saved", response_model=OpportunityFeedResponse)
async def get_saved_opportunities(
    session: AsyncSession = Depends(get_session),
) -> OpportunityFeedResponse:
    """Returns all opportunities the user has saved."""
    opp_result = await session.execute(
        select(Opportunity).where(Opportunity.saved == True)  # noqa: E712
    )
    opps = opp_result.scalars().all()
    cards = await _build_cards(session, opps)

    return OpportunityFeedResponse(opportunities=cards, total=len(cards), has_more=False)


@router.get("/opportunities/builds", response_model=OpportunityFeedResponse)
async def get_build_opportunities(
    session: AsyncSession = Depends(get_session),
) -> OpportunityFeedResponse:
    """Returns all opportunities marked as active builds."""
    opp_result = await session.execute(
        select(Opportunity).where(Opportunity.marked_as_build == True)  # noqa: E712
    )
    opps = opp_result.scalars().all()
    cards = await _build_cards(session, opps)

    return OpportunityFeedResponse(opportunities=cards, total=len(cards), has_more=False)


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
            display_name=display_fault_name(fault.issue),
            severity=fault.severity,
            description=cp.description if cp else None,
            explanation=fault.explanation,
            seller_quote=fault.evidence,
            labour_days=cp.labour_days_default if cp else 1.0,
        ))

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

    # Build parts breakdown — pull from parts_price_cache for richer supplier data
    parts_breakdown: list[FaultPartsBreakdown] = []

    for fault in detected_faults:
        fault_type = fault.issue
        fault_parts = fault_parts_by_type.get(fault_type, [])

        part_results: list[PartResult] = []

        for fp in fault_parts:
            # Attempt to load from parts_price_cache (keyed by part+vehicle)
            suppliers = await _load_suppliers_from_cache(
                session=session,
                part_name=fp.part_name,
                vehicle=vehicle,
            )
            cheapest = min((s.total_cost_pence for s in suppliers), default=None)

            part_results.append(PartResult(
                part_name=fp.part_name,
                part_category=fp.part_category,
                quantity=fp.quantity,
                is_consumable=fp.is_consumable,
                suppliers=suppliers,
                cheapest_pence=cheapest,
            ))

        fault_parts_total_min, fault_parts_total_max = parts_total_range(part_results)

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
    sold_comp_urls = (market_value.sold_comp_urls or []) if market_value else []

    card = _format_card(opp, listing, vehicle, list(detected_faults))
    return OpportunityDetail(
        **card.model_dump(),
        image_urls=listing_image_urls(listing),
        unpriced_fault_types=opp.unpriced_fault_types or [],
        faults=fault_details,
        parts_breakdown=parts_breakdown,
        effort_cost_pence=opp.effort_cost_pence,
        day_rate_pence=opp.day_rate_pence,
        linkup_fallback_used=linkup_fallback_used,
        sold_comp_urls=sold_comp_urls,
    )


async def _load_suppliers_from_cache(
    session: AsyncSession,
    part_name: str,
    vehicle: Vehicle | None,
) -> list[SupplierPrice]:
    """
    Looks up parts_price_cache for this part+vehicle combination.
    Returns list of SupplierPrice from cached PartResult objects.
    Returns empty list if no cache entry found or entry expired.
    """
    if vehicle is None:
        return []

    cache_key = _parts_pricing_svc._build_cache_key(
        part_name=part_name,
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
    )

    result = await session.execute(
        select(PartsPriceCache).where(PartsPriceCache.cache_key == cache_key)
    )
    row = result.scalar_one_or_none()
    if row is None or not row.is_valid:
        return []

    try:
        suppliers = []
        for item in row.results_json.get("results", []):
            base = item.get("base_price_pence", 0)
            delivery = item.get("delivery_pence", 0)
            total = item.get("total_cost_pence", base + delivery)
            suppliers.append(SupplierPrice(
                supplier=item.get("supplier", ""),
                supplier_logo_key=item.get("supplier_logo_key", ""),
                price_pence=base,
                delivery_pence=delivery,
                total_cost_pence=total,
                condition=item.get("condition", "new"),
                url=item.get("url", ""),
                in_stock=item.get("availability", "in_stock") == "in_stock",
                price_confidence=item.get("price_confidence", "live"),
            ))
        # Strip stub/scraped suppliers when running in live eBay-only mode
        if settings.ebay_parts_live and not settings.parts_stub:
            suppliers = [s for s in suppliers if "ebay" in s.supplier.lower()]

        return suppliers
    except Exception as exc:
        logger.warning("Failed to deserialise parts cache for %s: %s", cache_key, exc)
        return []


async def _get_opportunity_or_404(opportunity_id: str, session: AsyncSession) -> Opportunity:
    """Load an Opportunity by UUID string, raising 404 if not found."""
    try:
        import uuid
        opp_uuid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    result = await session.execute(select(Opportunity).where(Opportunity.id == opp_uuid))
    opp = result.scalar_one_or_none()
    if opp is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.post("/opportunities/{opportunity_id}/save")
async def save_opportunity(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    opp = await _get_opportunity_or_404(opportunity_id, session)
    opp.saved = True
    await session.commit()
    return {"status": "saved"}


@router.post("/opportunities/{opportunity_id}/unsave")
async def unsave_opportunity(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    opp = await _get_opportunity_or_404(opportunity_id, session)
    opp.saved = False
    await session.commit()
    return {"status": "unsaved"}


@router.post("/opportunities/{opportunity_id}/mark-build")
async def mark_as_build(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    opp = await _get_opportunity_or_404(opportunity_id, session)
    opp.marked_as_build = True
    await session.commit()
    return {"status": "marked_as_build"}


@router.post("/opportunities/{opportunity_id}/unmark-build")
async def unmark_as_build(
    opportunity_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    opp = await _get_opportunity_or_404(opportunity_id, session)
    opp.marked_as_build = False
    await session.commit()
    return {"status": "unmarked_as_build"}
