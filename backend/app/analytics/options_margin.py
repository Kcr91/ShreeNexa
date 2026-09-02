"""Options basket margin calculation engine: SPAN, Exposure, Premium, and Hedging Relief."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.greeks import OptionType
from app.analytics.strategy_builder import OptionLeg


class LegMarginBreakdown(BaseModel):
    """Margin breakdown for an individual option leg."""

    model_config = ConfigDict(frozen=True)

    leg_id: str
    symbol: str
    action: str
    option_type: OptionType
    strike: float
    quantity: int
    lot_size: int
    premium_margin: float
    span_margin: float
    exposure_margin: float
    total_margin: float


class BasketMarginResult(BaseModel):
    """Aggregate basket margin requirement with hedging relief benefits."""

    model_config = ConfigDict(frozen=True)

    underlying: str
    spot_price: float
    gross_margin: float
    total_span_margin: float
    total_exposure_margin: float
    total_premium_margin: float
    hedging_benefit_margin: float
    net_required_margin: float
    is_available: bool = True
    unreliable_reason: str | None = None
    leg_breakdown: list[LegMarginBreakdown] = Field(default_factory=list)


def calculate_basket_margin(
    underlying: str,
    spot_price: float,
    legs: list[OptionLeg],
    span_rate_pct: float = 0.11,
    exposure_rate_pct: float = 0.02,
) -> BasketMarginResult:
    """Calculate SPAN, Exposure, Premium, and Hedging Benefit margins for option legs."""
    if spot_price <= 0.0:
        return BasketMarginResult(
            underlying=underlying,
            spot_price=spot_price,
            gross_margin=0.0,
            total_span_margin=0.0,
            total_exposure_margin=0.0,
            total_premium_margin=0.0,
            hedging_benefit_margin=0.0,
            net_required_margin=0.0,
            is_available=False,
            unreliable_reason="Underlying spot price is invalid or unavailable",
        )

    active_legs = [leg for leg in legs if leg.is_enabled]
    if not active_legs:
        return BasketMarginResult(
            underlying=underlying,
            spot_price=spot_price,
            gross_margin=0.0,
            total_span_margin=0.0,
            total_exposure_margin=0.0,
            total_premium_margin=0.0,
            hedging_benefit_margin=0.0,
            net_required_margin=0.0,
            is_available=True,
            leg_breakdown=[],
        )

    leg_breakdown: list[LegMarginBreakdown] = []
    total_gross_span = 0.0
    total_gross_exposure = 0.0
    total_premium = 0.0

    short_calls: list[OptionLeg] = []
    long_calls: list[OptionLeg] = []
    short_puts: list[OptionLeg] = []
    long_puts: list[OptionLeg] = []

    for leg in active_legs:
        total_units = leg.quantity * leg.lot_size
        contract_value = spot_price * total_units

        if leg.action == "BUY":
            prem_margin = leg.entry_price * total_units
            span_margin = 0.0
            expo_margin = 0.0
            tot_margin = prem_margin
            total_premium += prem_margin

            if leg.option_type == OptionType.CALL:
                long_calls.append(leg)
            else:
                long_puts.append(leg)
        else:
            prem_margin = 0.0
            # Naked Short Option: SPAN (~11% contract value) + Exposure (~2% contract value)
            span_margin = contract_value * span_rate_pct + (leg.entry_price * total_units)
            expo_margin = contract_value * exposure_rate_pct
            tot_margin = span_margin + expo_margin

            total_gross_span += span_margin
            total_gross_exposure += expo_margin

            if leg.option_type == OptionType.CALL:
                short_calls.append(leg)
            else:
                short_puts.append(leg)

        leg_breakdown.append(
            LegMarginBreakdown(
                leg_id=leg.leg_id,
                symbol=leg.symbol,
                action=leg.action,
                option_type=leg.option_type,
                strike=leg.strike,
                quantity=leg.quantity,
                lot_size=leg.lot_size,
                premium_margin=round(prem_margin, 2),
                span_margin=round(span_margin, 2),
                exposure_margin=round(expo_margin, 2),
                total_margin=round(tot_margin, 2),
            )
        )

    gross_margin = total_gross_span + total_gross_exposure + total_premium

    # Compute Hedging Relief Benefit for defined-risk spreads
    hedged_margin = gross_margin

    # 1. Vertical Call Spreads (Bull Call or Bear Call)
    if short_calls and long_calls:
        # Match short call with long call
        for s_leg, l_leg in zip(short_calls, long_calls, strict=False):
            units = min(s_leg.quantity, l_leg.quantity) * s_leg.lot_size
            spread_width = abs(s_leg.strike - l_leg.strike)
            max_spread_risk = spread_width * units

            unhedged_short_cost = (
                (spot_price * units * (span_rate_pct + exposure_rate_pct))
                + (s_leg.entry_price * units)
            )
            long_prem_cost = l_leg.entry_price * units
            unhedged_total = unhedged_short_cost + long_prem_cost

            # Spread margin is capped at max risk plus buffer
            capped_spread_margin = max(max_spread_risk, long_prem_cost) + (
                spot_price * units * 0.005
            )
            relief = max(0.0, unhedged_total - capped_spread_margin)
            hedged_margin -= relief

    # 2. Vertical Put Spreads (Bull Put or Bear Put)
    if short_puts and long_puts:
        for s_leg, l_leg in zip(short_puts, long_puts, strict=False):
            units = min(s_leg.quantity, l_leg.quantity) * s_leg.lot_size
            spread_width = abs(s_leg.strike - l_leg.strike)
            max_spread_risk = spread_width * units

            unhedged_short_cost = (
                (spot_price * units * (span_rate_pct + exposure_rate_pct))
                + (s_leg.entry_price * units)
            )
            long_prem_cost = l_leg.entry_price * units
            unhedged_total = unhedged_short_cost + long_prem_cost

            capped_spread_margin = max(max_spread_risk, long_prem_cost) + (
                spot_price * units * 0.005
            )
            relief = max(0.0, unhedged_total - capped_spread_margin)
            hedged_margin -= relief

    # 3. If both Call and Put spreads are present (Iron Condor / Butterfly),
    # Exchange only charges margin on the higher of the two wings plus long premiums
    if short_calls and long_calls and short_puts and long_puts:
        # Iron Condor double-wing relief
        units = min(short_calls[0].quantity, short_puts[0].quantity) * short_calls[0].lot_size
        call_spread_width = abs(short_calls[0].strike - long_calls[0].strike)
        put_spread_width = abs(short_puts[0].strike - long_puts[0].strike)
        max_wing_width = max(call_spread_width, put_spread_width)
        condor_margin = (
            max_wing_width * units
            + (spot_price * units * 0.01)
            + (long_calls[0].entry_price + long_puts[0].entry_price) * units
        )
        if condor_margin < hedged_margin:
            hedged_margin = condor_margin

    hedging_benefit = max(0.0, gross_margin - hedged_margin)
    net_required = max(total_premium, hedged_margin)

    return BasketMarginResult(
        underlying=underlying.upper(),
        spot_price=spot_price,
        gross_margin=round(gross_margin, 2),
        total_span_margin=round(total_gross_span, 2),
        total_exposure_margin=round(total_gross_exposure, 2),
        total_premium_margin=round(total_premium, 2),
        hedging_benefit_margin=round(hedging_benefit, 2),
        net_required_margin=round(net_required, 2),
        is_available=True,
        leg_breakdown=leg_breakdown,
    )
