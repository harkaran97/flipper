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
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import EventBus
from app.events.types import Event, EventType
from app.models.enums import OpportunityClass, RiskLevel
from app.models.exterior_condition import ExteriorCondition
from app.models.fault import DetectedFault
from app.models.listing import Listing
from app.models.market_value import MarketValue
from app.models.opportunity import Opportunity
from app.models.repair_estimate import RepairEstimate
from app.models.user_settings import UserSettings

logger = logging.getLogger(__name__)

_DEFAULT_DAY_RATE_PENCE = 15000  # £150/day


def calculate_true_profit(
    market_value_pence: int,
    listing_price_pence: int,
    parts_cost_min_pence: int,
    parts_cost_max_pence: int,
    total_man_days: float,
    day_rate_pence: int,
) -> dict:
    """
    Canonical profit calculation. All values in pence.
    Returns dict with parts_cost_mid_pence, effort_cost_pence,
    true_profit_pence, true_margin_pct.

    If market_value_pence is 0, true_margin_pct is set to 0.0 (no division).
    """
    parts_cost_mid = (parts_cost_min_pence + parts_cost_max_pence) // 2
    effort_cost = int(total_man_days * day_rate_pence)
    true_profit_pence = (
        market_value_pence - listing_price_pence - parts_cost_mid - effort_cost
    )
    if market_value_pence == 0:
        true_margin_pct = 0.0
    else:
        true_margin_pct = (true_profit_pence / market_value_pence) * 100
    return {
        "parts_cost_mid_pence": parts_cost_mid,
        "effort_cost_pence": effort_cost,
        "true_profit_pence": true_profit_pence,
        "true_margin_pct": true_margin_pct,
    }


def classify_opportunity(
    true_margin_pct: float,
    true_profit_pence: int,
    market_value_confidence: str,
    has_unpriced_faults: bool,
    write_off_category: str,
    vagueness_signals: list,
    listing_price_pence: int,
    market_value_pence: int,
    comp_count: int = 0,
) -> OpportunityClass:
    """
    Canonical opportunity classification.
    Order of evaluation matters — check EXCLUDE conditions first.
    """
    # 1. Hard excludes — never surface write-offs or unknowns
    _WRITEOFF_EXCLUDE = {
        'cat_a', 'cat_b', 'cat_c', 'cat_d', 'cat_s', 'cat_n',
        'fire', 'flood', 'salvage', 'unknown_writeoff',
    }
    if write_off_category in _WRITEOFF_EXCLUDE:
        return OpportunityClass.EXCLUDE

    # Insufficient market value data — valuation unreliable
    if (
        market_value_pence == 0
        or comp_count == 0
        or (market_value_confidence == "low" and comp_count < 3)
    ):
        return OpportunityClass.EXCLUDE

    if true_profit_pence < 0:
        return OpportunityClass.EXCLUDE

    if true_margin_pct < 5.0:
        return OpportunityClass.EXCLUDE

    # 2. Worth a look — vague listings with low confidence + unpriced faults
    if (
        market_value_confidence == "low"
        and has_unpriced_faults
        and len(vagueness_signals) >= 2
    ):
        return OpportunityClass.WORTH_A_LOOK

    # 3. Strong — clean data, good margin
    if (
        true_margin_pct >= 40.0
        and market_value_confidence in ("high", "medium")
        and not has_unpriced_faults
    ):
        return OpportunityClass.STRONG

    # 4. Speculative — margin present but data incomplete
    if true_margin_pct >= 20.0:
        return OpportunityClass.SPECULATIVE

    # 5. Everything else with positive margin but below threshold
    return OpportunityClass.WORTH_A_LOOK


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
    if (
        write_off_category == "cat_s"
        or flood_damage
        or fire_damage
        or (has_unpriced_faults and market_value_confidence == "low")
    ):
        return RiskLevel.HIGH

    if (
        write_off_category == "cat_n"
        or has_unpriced_faults
        or market_value_confidence == "low"
        or vagueness_signal_count >= 3
    ):
        return RiskLevel.MEDIUM

    return RiskLevel.LOW


async def load_opportunity_inputs(
    session: AsyncSession,
    listing_id: uuid.UUID,
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
    # Load listing
    result = await session.execute(
        select(Listing).where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise ValueError(f"Listing {listing_id} not found")

    # Load repair estimate
    result = await session.execute(
        select(RepairEstimate).where(RepairEstimate.listing_id == listing_id)
    )
    repair_estimate = result.scalar_one_or_none()
    if repair_estimate is None:
        raise ValueError(f"RepairEstimate not found for listing {listing_id}")

    # Load market value
    result = await session.execute(
        select(MarketValue).where(MarketValue.listing_id == listing_id)
    )
    market_value = result.scalar_one_or_none()
    if market_value is None:
        raise ValueError(f"MarketValue not found for listing {listing_id}")

    # Load exterior condition (optional — use defaults if missing)
    result = await session.execute(
        select(ExteriorCondition).where(ExteriorCondition.listing_id == listing_id)
    )
    exterior_condition = result.scalar_one_or_none()

    # Load detected faults — derive vagueness signals from low-confidence faults
    result = await session.execute(
        select(DetectedFault).where(DetectedFault.listing_id == listing_id)
    )
    detected_faults = result.scalars().all()
    vagueness_signals = [f.issue for f in detected_faults if f.confidence < 0.5]

    # Load user settings (single row — fall back to defaults if missing)
    result = await session.execute(select(UserSettings).limit(1))
    user_settings = result.scalar_one_or_none()
    day_rate_pence = user_settings.day_rate_pence if user_settings else _DEFAULT_DAY_RATE_PENCE

    return {
        "listing": listing,
        "repair_estimate": repair_estimate,
        "market_value": market_value,
        "exterior_condition": exterior_condition,
        "vagueness_signals": vagueness_signals,
        "day_rate_pence": day_rate_pence,
    }


async def score_opportunity(
    session: AsyncSession,
    listing_id: uuid.UUID,
    bus: EventBus,
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
    try:
        inputs = await load_opportunity_inputs(session, listing_id)
    except ValueError as e:
        logger.error("Cannot score opportunity for listing %s: %s", listing_id, e)
        return

    listing = inputs["listing"]
    repair_estimate = inputs["repair_estimate"]
    market_value = inputs["market_value"]
    exterior_condition = inputs["exterior_condition"]
    vagueness_signals = inputs["vagueness_signals"]
    day_rate_pence = inputs["day_rate_pence"]

    # Extract write-off and damage flags from exterior_condition
    write_off_category = (
        exterior_condition.write_off_category if exterior_condition else "clean"
    )
    flood_damage = exterior_condition.flood_damage if exterior_condition else False
    fire_damage = exterior_condition.fire_damage if exterior_condition else False

    # Canonical profit calculation
    profit_result = calculate_true_profit(
        market_value_pence=market_value.median_value_pence,
        listing_price_pence=listing.price_pence,
        parts_cost_min_pence=repair_estimate.total_parts_min_pence,
        parts_cost_max_pence=repair_estimate.total_parts_max_pence,
        total_man_days=repair_estimate.total_man_days,
        day_rate_pence=day_rate_pence,
    )

    # Opportunity classification
    opportunity_class = classify_opportunity(
        true_margin_pct=profit_result["true_margin_pct"],
        true_profit_pence=profit_result["true_profit_pence"],
        market_value_confidence=market_value.confidence,
        has_unpriced_faults=repair_estimate.has_unpriced_faults,
        write_off_category=write_off_category,
        vagueness_signals=vagueness_signals,
        listing_price_pence=listing.price_pence,
        market_value_pence=market_value.median_value_pence,
        comp_count=market_value.comp_count,
    )
    _WRITEOFF_EXCLUDE = {
        'cat_a', 'cat_b', 'cat_c', 'cat_d', 'cat_s', 'cat_n',
        'fire', 'flood', 'salvage', 'unknown_writeoff',
    }
    if opportunity_class == OpportunityClass.EXCLUDE and write_off_category in _WRITEOFF_EXCLUDE:
        logger.info(
            "[SCORING] Excluded listing %s — write-off category: %s",
            listing_id, write_off_category,
        )
    elif opportunity_class == OpportunityClass.EXCLUDE and (
        market_value.median_value_pence == 0
        or market_value.comp_count == 0
        or (market_value.confidence == "low" and market_value.comp_count < 3)
    ):
        logger.warning(
            "[SCORER] Excluding listing %s — insufficient market value data (comps=%d, confidence=%s)",
            listing_id, market_value.comp_count, market_value.confidence,
        )

    # Risk calculation
    risk_level = calculate_risk(
        write_off_category=write_off_category,
        has_unpriced_faults=repair_estimate.has_unpriced_faults,
        market_value_confidence=market_value.confidence,
        flood_damage=flood_damage,
        fire_damage=fire_damage,
        vagueness_signal_count=len(vagueness_signals),
    )

    profit_is_floor_estimate = repair_estimate.has_unpriced_faults

    # Upsert Opportunity row (unique per listing)
    result = await session.execute(
        select(Opportunity).where(Opportunity.listing_id == listing_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        await session.delete(existing)
        await session.flush()

    opportunity = Opportunity(
        listing_id=listing_id,
        listing_price_pence=listing.price_pence,
        parts_cost_min_pence=repair_estimate.total_parts_min_pence,
        parts_cost_max_pence=repair_estimate.total_parts_max_pence,
        parts_cost_mid_pence=profit_result["parts_cost_mid_pence"],
        effort_cost_pence=profit_result["effort_cost_pence"],
        market_value_pence=market_value.median_value_pence,
        true_profit_pence=profit_result["true_profit_pence"],
        true_margin_pct=profit_result["true_margin_pct"],
        total_man_days=repair_estimate.total_man_days,
        day_rate_pence=day_rate_pence,
        opportunity_class=opportunity_class.value,
        risk_level=risk_level.value,
        has_unpriced_faults=repair_estimate.has_unpriced_faults,
        unpriced_fault_types=repair_estimate.unpriced_fault_types,
        market_value_confidence=market_value.confidence,
        market_value_comp_count=market_value.comp_count,
        profit_is_floor_estimate=profit_is_floor_estimate,
        write_off_category=write_off_category,
        alerted=False,
    )
    session.add(opportunity)
    await session.commit()

    logger.info(
        "Opportunity scored for listing %s: class=%s, risk=%s, profit=£%d, margin=%.1f%%",
        listing_id,
        opportunity_class.value,
        risk_level.value,
        profit_result["true_profit_pence"] // 100,
        profit_result["true_margin_pct"],
    )

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
        },
    ))
