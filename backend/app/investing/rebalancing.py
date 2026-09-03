"""SIP planning, calendar/threshold rebalancing proposals, and TWR calculation (F10.4).

Safety invariant: Rebalancing engine generates proposals only. No automatic orders
are ever placed or transmitted to live brokers or execution engines.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.investing.ledger import HoldingsLedger, holdings_ledger


class RebalanceAction(StrEnum):
    """Direction of proposed rebalancing transaction."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RebalanceTrigger(StrEnum):
    """Mechanism that triggered the rebalance review."""

    CALENDAR = "CALENDAR"  # Periodic review (quarterly, annual)
    THRESHOLD = "THRESHOLD"  # Allocation drift exceeded tolerance band
    INFLOW_ONLY = "INFLOW_ONLY"  # Rebalance via fresh cash without selling


class SIPAllocationItem(BaseModel):
    """Calculated share allocation for a single security in a SIP instalment."""

    model_config = ConfigDict(frozen=True)

    security_id: str
    trading_symbol: str
    target_weight_pct: float
    target_amount: float
    cmp: float
    allocated_shares: int
    allocated_amount: float
    leftover_cash: float


class SIPPlanResult(BaseModel):
    """Calculated SIP purchase schedule with whole-share allocations and cash residue."""

    model_config = ConfigDict(frozen=True)

    budget: float
    total_allocated: float
    total_unallocated_cash: float
    items: list[SIPAllocationItem] = Field(default_factory=list)


class StepUpSIPProjection(BaseModel):
    """Projected future annual cashflows under a step-up SIP schedule."""

    model_config = ConfigDict(frozen=True)

    year: int
    monthly_instalment: float
    annual_contribution: float
    cumulative_invested: float


class RebalanceProposalItem(BaseModel):
    """Single suggested rebalancing action for an asset."""

    model_config = ConfigDict(frozen=True)

    security_id: str
    trading_symbol: str
    current_quantity: int
    current_value: float
    current_weight_pct: float
    target_weight_pct: float
    drift_pct: float
    action: RebalanceAction
    proposed_quantity: int
    proposed_price: float
    estimated_amount: float
    reason: str


class RebalanceProposal(BaseModel):
    """Actionable rebalancing plan. Strictly a proposal; never automatically executed."""

    model_config = ConfigDict(frozen=True)

    proposal_id: str
    account_id: str
    created_at: datetime
    trigger: RebalanceTrigger
    status: str = "PROPOSED"  # Invariant: always PROPOSED, never auto-ordered
    total_portfolio_value: float
    available_cash: float
    total_proposed_buy_amount: float
    total_proposed_sell_amount: float
    net_cash_impact: float
    cash_limit_exceeded: bool
    items: list[RebalanceProposalItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SubPeriodReturn(BaseModel):
    """Sub-period return segment between cashflow dates for TWR calculation."""

    model_config = ConfigDict(frozen=True)

    start_date: date
    end_date: date
    start_value: float
    end_value: float
    net_cash_flow: float
    sub_period_return: float


class TWRCalculationResult(BaseModel):
    """Time-Weighted Return separating external cash additions from manager performance."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    start_date: date
    end_date: date
    twr: float
    twr_pct: float
    sub_periods: list[SubPeriodReturn] = Field(default_factory=list)
    methodology: str = (
        "Time-Weighted Return (TWR) chains geometric sub-period returns across cashflow "
        "injection dates, completely removing the timing distortion of investor deposits."
    )


# --- SIP Planning Functions ---


def plan_sip_instalment(
    budget: float,
    target_weights: dict[str, float],
    current_prices: dict[str, float],
) -> SIPPlanResult:
    """Plan whole-lot equity purchases from a periodic SIP budget and target weights."""
    if budget <= 0:
        raise ValueError(f"SIP budget must be positive, got {budget}")

    tot_weight = sum(target_weights.values())
    if abs(tot_weight - 100.0) > 0.01:
        raise ValueError(f"Target weights must sum to 100.0%, got {tot_weight}%")

    items: list[SIPAllocationItem] = []
    total_allocated = 0.0

    for symbol, weight_pct in target_weights.items():
        cmp = current_prices.get(symbol, 0.0)
        if cmp <= 0:
            raise ValueError(f"Valid positive CMP required for {symbol}, got {cmp}")

        target_amt = round(budget * (weight_pct / 100.0), 2)
        shares = int(target_amt // cmp)
        alloc_amt = round(shares * cmp, 2)
        leftover = round(target_amt - alloc_amt, 2)
        total_allocated += alloc_amt

        items.append(
            SIPAllocationItem(
                security_id=symbol,
                trading_symbol=symbol,
                target_weight_pct=weight_pct,
                target_amount=target_amt,
                cmp=cmp,
                allocated_shares=shares,
                allocated_amount=alloc_amt,
                leftover_cash=leftover,
            )
        )

    unallocated = round(budget - total_allocated, 2)
    return SIPPlanResult(
        budget=budget,
        total_allocated=round(total_allocated, 2),
        total_unallocated_cash=unallocated,
        items=items,
    )


def project_step_up_sip(
    initial_monthly: float,
    annual_step_up_pct: float,
    years: int = 5,
) -> list[StepUpSIPProjection]:
    """Calculate multi-year capital commitment under a step-up SIP schedule."""
    if initial_monthly <= 0:
        raise ValueError(f"Initial monthly instalment must be positive, got {initial_monthly}")

    projections: list[StepUpSIPProjection] = []
    current_monthly = initial_monthly
    cum_invested = 0.0

    for yr in range(1, years + 1):
        annual_contrib = round(current_monthly * 12.0, 2)
        cum_invested = round(cum_invested + annual_contrib, 2)
        projections.append(
            StepUpSIPProjection(
                year=yr,
                monthly_instalment=round(current_monthly, 2),
                annual_contribution=annual_contrib,
                cumulative_invested=cum_invested,
            )
        )
        current_monthly = current_monthly * (1.0 + (annual_step_up_pct / 100.0))

    return projections


# --- Rebalancing Proposal Generator ---


def generate_rebalance_proposal(
    account_id: str,
    target_weights: dict[str, float],
    current_prices: dict[str, float],
    *,
    available_cash: float = 0.0,
    tolerance_band_pct: float = 5.0,
    inflow_only: bool = False,
    max_allocation_per_trade: float | None = None,
    ledger: HoldingsLedger = holdings_ledger,
) -> RebalanceProposal:
    """Generate portfolio rebalancing proposal.

    Safety: Strictly returns a proposal for user authorization; never transmits
    live orders. Proposal totals respect available cash and trade limits.
    """
    report = ledger.generate_portfolio_report(account_id, current_prices=current_prices)
    tot_weight = sum(target_weights.values())
    if abs(tot_weight - 100.0) > 0.01:
        raise ValueError(f"Target weights must sum to 100%, got {tot_weight}%")

    portfolio_equity = report.total_current_value or report.total_invested
    total_capital = portfolio_equity + max(0.0, available_cash)
    if total_capital <= 0:
        raise ValueError("Total portfolio value and available cash cannot be zero")

    holding_dict = {h.trading_symbol: h for h in report.holdings}
    all_symbols = set(target_weights.keys()).union(holding_dict.keys())

    items: list[RebalanceProposalItem] = []
    tot_buy = 0.0
    tot_sell = 0.0
    warnings: list[str] = []

    for sym in sorted(all_symbols):
        tgt_wt = target_weights.get(sym, 0.0)
        h = holding_dict.get(sym)
        cmp = current_prices.get(sym, h.current_market_price if h else 0.0)

        if cmp <= 0:
            warnings.append(f"CMP missing for {sym}; skipped from rebalance calculations.")
            continue

        curr_qty = h.total_quantity if h else 0
        curr_val = round(curr_qty * cmp, 2)
        curr_wt = round((curr_val / total_capital) * 100.0, 2)
        drift = round(curr_wt - tgt_wt, 2)

        desired_val = round(total_capital * (tgt_wt / 100.0), 2)
        diff_val = desired_val - curr_val

        action = RebalanceAction.HOLD
        prop_qty = 0
        est_amt = 0.0
        reason = f"Within tolerance band ({abs(drift)}% <= {tolerance_band_pct}%)"

        if abs(drift) > tolerance_band_pct:
            if diff_val > 0:
                # Underweight -> BUY
                action = RebalanceAction.BUY
                prop_qty = int(diff_val // cmp)
                if max_allocation_per_trade and (prop_qty * cmp) > max_allocation_per_trade:
                    prop_qty = int(max_allocation_per_trade // cmp)
                    warnings.append(f"Buy order for {sym} capped by max_allocation_per_trade.")
                est_amt = round(prop_qty * cmp, 2)
                reason = f"Underweight by {abs(drift)}%: allocate to meet target {tgt_wt}%"
                tot_buy += est_amt
            elif diff_val < 0 and not inflow_only:
                # Overweight -> SELL (if not inflow-only)
                action = RebalanceAction.SELL
                prop_qty = min(curr_qty, int(abs(diff_val) // cmp))
                est_amt = round(prop_qty * cmp, 2)
                reason = f"Overweight by {abs(drift)}%: trim to meet target {tgt_wt}%"
                tot_sell += est_amt

        items.append(
            RebalanceProposalItem(
                security_id=sym,
                trading_symbol=sym,
                current_quantity=curr_qty,
                current_value=curr_val,
                current_weight_pct=curr_wt,
                target_weight_pct=tgt_wt,
                drift_pct=drift,
                action=action,
                proposed_quantity=prop_qty,
                proposed_price=cmp,
                estimated_amount=est_amt,
                reason=reason,
            )
        )

    net_cash = round(tot_sell + available_cash - tot_buy, 2)
    cash_exceeded = tot_buy > (available_cash + tot_sell)
    if cash_exceeded:
        warnings.append(
            f"Cash limit notice: Proposed purchases (₹{tot_buy}) exceed available cash "
            f"+ sell proceeds (₹{round(available_cash + tot_sell, 2)})."
        )

    trigger = (
        RebalanceTrigger.INFLOW_ONLY
        if inflow_only
        else (
            RebalanceTrigger.THRESHOLD
            if any(abs(it.drift_pct) > tolerance_band_pct for it in items)
            else RebalanceTrigger.CALENDAR
        )
    )

    return RebalanceProposal(
        proposal_id=f"reb-{uuid.uuid4().hex[:10]}",
        account_id=account_id,
        created_at=datetime.now(),
        trigger=trigger,
        status="PROPOSED",
        total_portfolio_value=portfolio_equity,
        available_cash=available_cash,
        total_proposed_buy_amount=round(tot_buy, 2),
        total_proposed_sell_amount=round(tot_sell, 2),
        net_cash_impact=net_cash,
        cash_limit_exceeded=cash_exceeded,
        items=items,
        warnings=warnings,
    )


# --- Cashflow / TWR Separation ---


def calculate_time_weighted_return(
    account_id: str,
    sub_periods_data: list[tuple[date, date, float, float, float]],
) -> TWRCalculationResult:
    """Calculate Time-Weighted Return (TWR) isolating performance from cashflow timing.

    Each entry in sub_periods_data is:
    (start_date, end_date, start_val, end_val, net_cashflow_at_start)
    Sub-period return: r_t = (end_val - (start_val + cashflow)) / (start_val + cashflow).
    Total TWR: prod(1 + r_t) - 1.
    """
    if not sub_periods_data:
        raise ValueError("At least one sub-period required to calculate TWR")

    sub_periods: list[SubPeriodReturn] = []
    compounded = 1.0

    for s_date, e_date, s_val, e_val, flow in sub_periods_data:
        base = s_val + flow
        if base <= 0:
            r_t = 0.0
        else:
            r_t = (e_val - base) / base

        compounded *= 1.0 + r_t
        sub_periods.append(
            SubPeriodReturn(
                start_date=s_date,
                end_date=e_date,
                start_value=round(s_val, 2),
                end_value=round(e_val, 2),
                net_cash_flow=round(flow, 2),
                sub_period_return=round(r_t, 6),
            )
        )

    total_twr = compounded - 1.0
    return TWRCalculationResult(
        account_id=account_id,
        start_date=sub_periods[0].start_date,
        end_date=sub_periods[-1].end_date,
        twr=round(total_twr, 6),
        twr_pct=round(total_twr * 100.0, 2),
        sub_periods=sub_periods,
    )
