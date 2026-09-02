"""Option strategy backtesting simulation engine with Greeks aggregation and margin modeling."""

from __future__ import annotations

import logging
import subprocess
import uuid

from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.options_models import (
    OptionBacktestConfig,
    OptionBacktestResult,
    OptionLegConfig,
    PortfolioGreeks,
)
from app.engine.contracts import (
    FillEvent,
    OrderSide,
    Portfolio,
)
from app.engine.costs import ProductType, cost_calculator
from app.marketdata.options_analytics import BlackScholesPricer, OptionType
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


def _get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


def calculate_option_margin(
    legs: list[OptionLegConfig],
    spot_price: float,
    current_prices: dict[str, float],
    lots: int = 1,
) -> float:
    """Approximate exchange margin requirement (SPAN + Exposure) for multi-leg option strategy."""
    total_margin = 0.0
    for leg in legs:
        qty = leg.ratio * leg.lot_size * lots
        opt_price = current_prices.get(leg.leg_id, 0.0)

        if leg.side == OrderSide.BUY:
            # Long options only require full premium outlay
            total_margin += opt_price * qty
        else:
            # Short options require ~15% underlying value minus OTM distance + premium
            if leg.option_type == OptionType.CALL:
                otm_dist = max(0.0, leg.strike - spot_price)
            else:
                otm_dist = max(0.0, spot_price - leg.strike)
            base_margin = (0.15 * spot_price - otm_dist) * qty
            min_margin = 0.05 * spot_price * qty
            short_leg_margin = max(min_margin, base_margin) + opt_price * qty
            total_margin += short_leg_margin

    return total_margin


class OptionStrategyBacktestRunner:
    """Executes multi-leg options strategies against underlying prices with Greeks & settlement."""

    def __init__(self) -> None:
        self.pricer = BlackScholesPricer()

    def run(
        self,
        config: OptionBacktestConfig,
        underlying_bars: list[BarRecord],
    ) -> OptionBacktestResult:
        """Run multi-leg option strategy backtest over historical underlying price bars."""
        strategy = config.strategy
        portfolio = Portfolio.create(initial_cash=config.initial_cash)
        fills: list[FillEvent] = []
        greeks_history: list[PortfolioGreeks] = []
        margin_history: list[dict[str, float]] = []

        if not underlying_bars:
            metrics = calculate_backtest_metrics(
                config.initial_cash, portfolio, config.start_date, config.end_date
            )
            return OptionBacktestResult(
                strategy_name=strategy.name,
                config=config,
                metrics=metrics,
                greeks_history=[],
                margin_history=[],
                trades=[],
                equity_curve=[],
                engine_commit=_get_git_commit(),
            )

        sorted_bars = sorted(underlying_bars, key=lambda b: b.timestamp)
        open_legs = {leg.leg_id: leg for leg in strategy.legs}

        # 1. Entry at first bar Open
        first_bar = sorted_bars[0]
        entry_time = first_bar.timestamp
        entry_spot = first_bar.open

        current_prices: dict[str, float] = {}

        for leg in strategy.legs:
            qty = leg.ratio * leg.lot_size * strategy.lots
            t_exp = max(0.0001, (leg.expiry_date - entry_time).total_seconds() / (365.0 * 86400.0))
            opt_price = self.pricer.price(
                spot=entry_spot,
                strike=leg.strike,
                t_years=t_exp,
                rate=strategy.risk_free_rate,
                vol=strategy.volatility,
                option_type=leg.option_type,
            )
            current_prices[leg.leg_id] = opt_price

            fee = cost_calculator.calculate_cost(
                product_type=ProductType.OPTIONS,
                side=leg.side,
                quantity=qty,
                price=opt_price,
                timestamp=entry_time,
            )

            fill = FillEvent(
                fill_id=str(uuid.uuid4()),
                order_id=str(uuid.uuid4()),
                security_id=leg.leg_id,
                exchange_segment=strategy.exchange_segment,
                side=leg.side,
                quantity=qty,
                price=opt_price,
                timestamp=entry_time,
                brokerage=fee.brokerage,
                taxes=(
                    fee.stt_ctt + fee.exchange_txn_charge + fee.sebi_fee + fee.stamp_duty + fee.gst
                ),
            )
            fills.append(fill)
            portfolio.apply_fill(fill)

        # 2. Simulation Loop over Bars
        for bar in sorted_bars:
            t = bar.timestamp
            spot = bar.close

            # Check expiration / exercise
            expired_leg_ids: list[str] = []
            for leg_id, leg in list(open_legs.items()):
                if t >= leg.expiry_date:
                    expired_leg_ids.append(leg_id)
                    pos = portfolio.positions.get(leg_id)
                    if pos and pos.quantity != 0:
                        # Intrinsic settlement value
                        if leg.option_type == OptionType.CALL:
                            intrinsic = max(0.0, spot - leg.strike)
                        else:
                            intrinsic = max(0.0, leg.strike - spot)

                        close_side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
                        close_qty = abs(pos.quantity)

                        fee = cost_calculator.calculate_cost(
                            product_type=ProductType.OPTIONS,
                            side=close_side,
                            quantity=close_qty,
                            price=intrinsic,
                            timestamp=t,
                        )

                        settle_fill = FillEvent(
                            fill_id=str(uuid.uuid4()),
                            order_id=str(uuid.uuid4()),
                            security_id=leg_id,
                            exchange_segment=strategy.exchange_segment,
                            side=close_side,
                            quantity=close_qty,
                            price=intrinsic,
                            timestamp=t,
                            brokerage=fee.brokerage,
                            taxes=(
                                fee.stt_ctt
                                + fee.exchange_txn_charge
                                + fee.sebi_fee
                                + fee.stamp_duty
                                + fee.gst
                            ),
                        )
                        fills.append(settle_fill)
                        portfolio.apply_fill(settle_fill)
                        current_prices[leg_id] = intrinsic

            for exp_id in expired_leg_ids:
                open_legs.pop(exp_id, None)

            # Re-price open legs and aggregate portfolio Greeks
            net_delta = 0.0
            net_gamma = 0.0
            net_theta = 0.0
            net_vega = 0.0
            net_rho = 0.0

            for leg_id, leg in open_legs.items():
                pos = portfolio.positions.get(leg_id)
                if pos and pos.quantity != 0:
                    t_rem = max(0.0, (leg.expiry_date - t).total_seconds() / (365.0 * 86400.0))
                    opt_p = self.pricer.price(
                        spot=spot,
                        strike=leg.strike,
                        t_years=t_rem,
                        rate=strategy.risk_free_rate,
                        vol=strategy.volatility,
                        option_type=leg.option_type,
                    )
                    current_prices[leg_id] = opt_p

                    greeks = self.pricer.calculate_greeks(
                        spot=spot,
                        strike=leg.strike,
                        t_years=t_rem,
                        rate=strategy.risk_free_rate,
                        vol=strategy.volatility,
                        option_type=leg.option_type,
                    )

                    # Directional sign: +1 for Long, -1 for Short
                    sign = 1.0 if pos.quantity > 0 else -1.0
                    pos_qty = abs(pos.quantity)

                    net_delta += sign * pos_qty * greeks.delta
                    net_gamma += sign * pos_qty * greeks.gamma
                    net_theta += sign * pos_qty * greeks.theta
                    net_vega += sign * pos_qty * greeks.vega
                    net_rho += sign * pos_qty * greeks.rho

            greeks_history.append(
                PortfolioGreeks(
                    timestamp=t,
                    net_delta=net_delta,
                    net_gamma=net_gamma,
                    net_theta=net_theta,
                    net_vega=net_vega,
                    net_rho=net_rho,
                )
            )

            # Mark portfolio to market
            portfolio.mark_to_market(current_prices, t)

            # Margin requirement
            req_margin = calculate_option_margin(
                strategy.legs, spot, current_prices, lots=strategy.lots
            )
            margin_history.append({"timestamp": t.timestamp(), "required_margin": req_margin})

        # 3. Calculate Performance Metrics
        metrics = calculate_backtest_metrics(
            initial_capital=config.initial_cash,
            portfolio=portfolio,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        return OptionBacktestResult(
            strategy_name=strategy.name,
            config=config,
            metrics=metrics,
            greeks_history=greeks_history,
            margin_history=margin_history,
            trades=fills,
            equity_curve=portfolio.equity_curve,
            engine_commit=_get_git_commit(),
        )
