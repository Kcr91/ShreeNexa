"""Multi-leg option strategy builder: payoffs, breakevens, extrema, and position Greeks."""

from __future__ import annotations

import math
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.greeks import OptionType, price_black76_scalar

IST = ZoneInfo("Asia/Kolkata")


class OptionLeg(BaseModel):
    """Single option contract leg in a multi-leg strategy."""

    model_config = ConfigDict(frozen=True)

    leg_id: str
    symbol: str
    strike: float
    option_type: OptionType
    action: Literal["BUY", "SELL"]
    quantity: int = Field(default=1, gt=0)  # in lots
    lot_size: int = Field(default=25, gt=0)
    entry_price: float = Field(..., ge=0)
    iv: float = Field(default=0.15, gt=0)
    expiry_date: date
    is_enabled: bool = True


class MultiLegStrategy(BaseModel):
    """Complete multi-leg strategy definition."""

    model_config = ConfigDict(frozen=True)

    strategy_id: str
    name: str
    underlying: str
    spot_price: float = Field(..., gt=0)
    forward_price: float = Field(..., gt=0)
    interest_rate: float = Field(default=0.07, ge=0)
    legs: list[OptionLeg] = Field(default_factory=list)


class PayoffPoint(BaseModel):
    """Payoff valuation point along hypothetical underlying spot prices."""

    model_config = ConfigDict(frozen=True)

    price: float
    expiry_pnl: float
    target_date_pnl: float


class StrategyAnalyticsResult(BaseModel):
    """Comprehensive strategy analytics, breakevens, extrema, and net Greeks."""

    model_config = ConfigDict(frozen=True)

    strategy_name: str
    underlying: str
    spot_price: float
    net_premium: float  # Positive = Net Debit (paid), Negative = Net Credit (received)
    max_profit: float | None = None  # None indicates unlimited profit
    max_loss: float | None = None  # None indicates unlimited loss (negative value)
    risk_reward_ratio: float | None = None
    breakevens: list[float] = Field(default_factory=list)
    net_delta: float
    net_gamma: float
    net_theta: float  # in ₹ / day
    net_vega: float  # in ₹ / 1% vol
    net_rho: float
    payoff_curve: list[PayoffPoint] = Field(default_factory=list)


def calculate_strategy_payoff_and_greeks(
    strategy: MultiLegStrategy,
    target_days_forward: int = 0,
    price_range_pct: float = 0.10,
    num_points: int = 41,
) -> StrategyAnalyticsResult:
    """Compute aggregate net Greeks, analytical breakevens, extrema, and payoff curve."""
    active_legs = [leg for leg in strategy.legs if leg.is_enabled]

    # If no active legs, return zeroed analytics
    if not active_legs:
        return StrategyAnalyticsResult(
            strategy_name=strategy.name,
            underlying=strategy.underlying,
            spot_price=strategy.spot_price,
            net_premium=0.0,
            max_profit=0.0,
            max_loss=0.0,
            risk_reward_ratio=None,
            breakevens=[],
            net_delta=0.0,
            net_gamma=0.0,
            net_theta=0.0,
            net_vega=0.0,
            net_rho=0.0,
            payoff_curve=[],
        )

    today = date.today()
    net_premium = 0.0
    net_delta = 0.0
    net_gamma = 0.0
    net_theta = 0.0
    net_vega = 0.0
    net_rho = 0.0

    # 1. Compute Net Premium & Net Position Greeks at Spot
    for leg in active_legs:
        multiplier = 1 if leg.action == "BUY" else -1
        total_units = leg.quantity * leg.lot_size
        net_premium += multiplier * leg.entry_price * total_units

        # Compute leg Greeks
        days_to_exp = max(1, (leg.expiry_date - today).days)
        t_years = days_to_exp / 365.0
        greeks_res = price_black76_scalar(
            forward=strategy.forward_price,
            strike=leg.strike,
            t_years=t_years,
            rate=strategy.interest_rate,
            vol=leg.iv,
            option_type=leg.option_type,
        )

        net_delta += multiplier * total_units * greeks_res.delta
        net_gamma += multiplier * total_units * greeks_res.gamma
        net_theta += multiplier * total_units * greeks_res.theta
        net_vega += multiplier * total_units * greeks_res.vega
        net_rho += multiplier * total_units * greeks_res.rho

    # 2. Generate Grid of Prices for Payoff Curves
    spot = strategy.spot_price
    min_price = spot * (1.0 - price_range_pct)
    max_price = spot * (1.0 + price_range_pct)
    step = (max_price - min_price) / (num_points - 1)

    payoff_curve: list[PayoffPoint] = []
    expiry_pnls: list[tuple[float, float]] = []

    for idx in range(num_points):
        test_price = round(min_price + idx * step, 2)
        total_expiry_pnl = 0.0
        total_target_pnl = 0.0

        for leg in active_legs:
            multiplier = 1 if leg.action == "BUY" else -1
            total_units = leg.quantity * leg.lot_size

            # Expiry Payoff
            if leg.option_type == OptionType.CALL:
                intrinsic = max(0.0, test_price - leg.strike)
            else:
                intrinsic = max(0.0, leg.strike - test_price)

            leg_expiry_pnl = multiplier * (intrinsic - leg.entry_price) * total_units
            total_expiry_pnl += leg_expiry_pnl

            # Target Date Payoff (T+n)
            days_to_exp = max(1, (leg.expiry_date - today).days)
            rem_days = max(0.01, days_to_exp - target_days_forward)
            t_rem_years = rem_days / 365.0
            # Target forward
            f_target = test_price * (1.0 + strategy.interest_rate * t_rem_years)

            model_val = price_black76_scalar(
                forward=f_target,
                strike=leg.strike,
                t_years=t_rem_years,
                rate=strategy.interest_rate,
                vol=leg.iv,
                option_type=leg.option_type,
            ).price

            leg_target_pnl = multiplier * (model_val - leg.entry_price) * total_units
            total_target_pnl += leg_target_pnl

        total_expiry_pnl = round(total_expiry_pnl, 2)
        total_target_pnl = round(total_target_pnl, 2)
        payoff_curve.append(
            PayoffPoint(
                price=test_price,
                expiry_pnl=total_expiry_pnl,
                target_date_pnl=total_target_pnl,
            )
        )
        expiry_pnls.append((test_price, total_expiry_pnl))

    # 3. Exact Piecewise Linear Breakeven Finding
    # Collect all strike points plus outer bounds
    break_points = sorted(
        list(
            {
                min_price,
                max_price,
                *(leg.strike for leg in active_legs),
            }
        )
    )

    def _eval_exact_expiry_pnl(spot_val: float) -> float:
        total = 0.0
        for leg in active_legs:
            mult = 1 if leg.action == "BUY" else -1
            units = leg.quantity * leg.lot_size
            if leg.option_type == OptionType.CALL:
                intrinsic = max(0.0, spot_val - leg.strike)
            else:
                intrinsic = max(0.0, leg.strike - spot_val)
            total += mult * (intrinsic - leg.entry_price) * units
        return total

    exact_breakevens: list[float] = []
    # Check interior intervals
    for i in range(len(break_points) - 1):
        x1 = break_points[i]
        x2 = break_points[i + 1]
        y1 = _eval_exact_expiry_pnl(x1)
        y2 = _eval_exact_expiry_pnl(x2)

        if math.isclose(y1, 0.0, abs_tol=1e-5):
            exact_breakevens.append(round(x1, 2))
        elif (y1 < 0.0 and y2 > 0.0) or (y1 > 0.0 and y2 < 0.0):
            root = x1 - y1 * (x2 - x1) / (y2 - y1)
            exact_breakevens.append(round(root, 2))

    # Also check outer linear rays if slope crosses zero
    # Left ray (S < min_price)
    y_min1 = _eval_exact_expiry_pnl(min_price)
    y_min0 = _eval_exact_expiry_pnl(min_price - 100.0)
    slope_left = (y_min1 - y_min0) / 100.0
    if abs(slope_left) > 1e-4:
        root_left = min_price - y_min1 / slope_left
        if root_left < min_price and (
            (y_min0 < 0 < y_min1) or (y_min0 > 0 > y_min1)
        ):
            exact_breakevens.append(round(root_left, 2))

    # Right ray (S > max_price)
    y_max0 = _eval_exact_expiry_pnl(max_price)
    y_max1 = _eval_exact_expiry_pnl(max_price + 100.0)
    slope_right = (y_max1 - y_max0) / 100.0
    if abs(slope_right) > 1e-4:
        root_right = max_price - y_max0 / slope_right
        if root_right > max_price and (
            (y_max0 < 0 < y_max1) or (y_max0 > 0 > y_max1)
        ):
            exact_breakevens.append(round(root_right, 2))

    # 4. Compute Extrema (Max Profit and Max Loss)
    pnl_values = [pnl for _, pnl in expiry_pnls]
    max_p = max(pnl_values)
    min_p = min(pnl_values)

    # Check slope at extreme ends to detect unboundedness
    unbounded_upside = (pnl_values[-1] - pnl_values[-2]) > 5.0
    unbounded_downside = (pnl_values[0] - pnl_values[1]) > 5.0

    unbounded_loss_upside = (pnl_values[-1] - pnl_values[-2]) < -5.0
    unbounded_loss_downside = (pnl_values[0] - pnl_values[1]) < -5.0

    final_max_profit = None if (unbounded_upside or unbounded_downside) else round(max_p, 2)
    final_max_loss = (
        None if (unbounded_loss_upside or unbounded_loss_downside) else round(min_p, 2)
    )

    rr_ratio: float | None = None
    if (
        final_max_profit is not None
        and final_max_loss is not None
        and abs(final_max_loss) > 0.01
    ):
        rr_ratio = round(abs(final_max_profit / final_max_loss), 2)

    return StrategyAnalyticsResult(
        strategy_name=strategy.name,
        underlying=strategy.underlying,
        spot_price=strategy.spot_price,
        net_premium=round(net_premium, 2),
        max_profit=final_max_profit,
        max_loss=final_max_loss,
        risk_reward_ratio=rr_ratio,
        breakevens=sorted(list(set(exact_breakevens))),
        net_delta=round(net_delta, 2),
        net_gamma=round(net_gamma, 4),
        net_theta=round(net_theta, 2),
        net_vega=round(net_vega, 2),
        net_rho=round(net_rho, 2),
        payoff_curve=payoff_curve,
    )


def create_standard_strategy(
    strategy_type: str,
    underlying: str,
    spot_price: float,
    atm_strike: float,
    step: float,
    lot_size: int,
    expiry_date: date,
) -> MultiLegStrategy:
    """Factory creating standard pre-built multi-leg option strategies."""
    stype = strategy_type.upper()
    legs: list[OptionLeg] = []
    forward = spot_price * 1.003

    if stype == "BULL_CALL_SPREAD":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike)}-CE",
                strike=atm_strike,
                option_type=OptionType.CALL,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=150.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike + step)}-CE",
                strike=atm_strike + step,
                option_type=OptionType.CALL,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=90.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Bull Call Spread"

    elif stype == "BEAR_PUT_SPREAD":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike)}-PE",
                strike=atm_strike,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=145.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike - step)}-PE",
                strike=atm_strike - step,
                option_type=OptionType.PUT,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=85.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Bear Put Spread"

    elif stype == "STRADDLE":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike)}-CE",
                strike=atm_strike,
                option_type=OptionType.CALL,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=150.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike)}-PE",
                strike=atm_strike,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=145.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Long Straddle"

    elif stype == "STRANGLE":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike + step)}-CE",
                strike=atm_strike + step,
                option_type=OptionType.CALL,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=90.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike - step)}-PE",
                strike=atm_strike - step,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=85.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Long Strangle"

    elif stype == "IRON_CONDOR":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike - 2 * step)}-PE",
                strike=atm_strike - 2 * step,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=15.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike - step)}-PE",
                strike=atm_strike - step,
                option_type=OptionType.PUT,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=35.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-3",
                symbol=f"{underlying}-{int(atm_strike + step)}-CE",
                strike=atm_strike + step,
                option_type=OptionType.CALL,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=35.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-4",
                symbol=f"{underlying}-{int(atm_strike + 2 * step)}-CE",
                strike=atm_strike + 2 * step,
                option_type=OptionType.CALL,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=15.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Iron Condor"

    elif stype == "IRON_BUTTERFLY":
        legs = [
            OptionLeg(
                leg_id="leg-1",
                symbol=f"{underlying}-{int(atm_strike - step)}-PE",
                strike=atm_strike - step,
                option_type=OptionType.PUT,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=45.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-2",
                symbol=f"{underlying}-{int(atm_strike)}-PE",
                strike=atm_strike,
                option_type=OptionType.PUT,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=110.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-3",
                symbol=f"{underlying}-{int(atm_strike)}-CE",
                strike=atm_strike,
                option_type=OptionType.CALL,
                action="SELL",
                quantity=1,
                lot_size=lot_size,
                entry_price=115.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
            OptionLeg(
                leg_id="leg-4",
                symbol=f"{underlying}-{int(atm_strike + step)}-CE",
                strike=atm_strike + step,
                option_type=OptionType.CALL,
                action="BUY",
                quantity=1,
                lot_size=lot_size,
                entry_price=48.0,
                iv=0.14,
                expiry_date=expiry_date,
            ),
        ]
        name = "Iron Butterfly"

    else:
        # Default fallback to Bull Call Spread
        return create_standard_strategy(
            "BULL_CALL_SPREAD", underlying, spot_price, atm_strike, step, lot_size, expiry_date
        )

    return MultiLegStrategy(
        strategy_id=f"strat-{stype.lower()}",
        name=name,
        underlying=underlying,
        spot_price=spot_price,
        forward_price=forward,
        legs=legs,
    )
