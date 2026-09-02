"""Walk-forward optimization and out-of-sample validation analysis engine."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from app.backtest.metrics import calculate_backtest_metrics
from app.backtest.models import BacktestConfig, BacktestPerformanceMetrics
from app.backtest.runner import StockStrategyBacktestRunner
from app.engine.contracts import EquityPoint, Portfolio
from app.warehouse.schema import BarRecord


class WalkForwardSplit(BaseModel):
    """Specification of an In-Sample (IS) and Out-of-Sample (OOS) time split."""

    model_config = ConfigDict(extra="forbid")

    split_index: int
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime


class WalkForwardConfig(BaseModel):
    """Configuration for rolling or expanding walk-forward window partitioning."""

    model_config = ConfigDict(extra="forbid")

    train_window_days: int = Field(default=180, ge=1)
    validation_window_days: int = Field(default=60, ge=1)
    step_days: int = Field(default=60, ge=1)
    anchored: bool = Field(default=False)


class WalkForwardWindowResult(BaseModel):
    """Backtesting results for a single In-Sample / Out-of-Sample window."""

    model_config = ConfigDict(extra="forbid")

    split: WalkForwardSplit
    in_sample_metrics: BacktestPerformanceMetrics
    out_of_sample_metrics: BacktestPerformanceMetrics
    in_sample_cagr_pct: float
    out_of_sample_cagr_pct: float
    walk_forward_efficiency: float


class WalkForwardResult(BaseModel):
    """Aggregated walk-forward analysis output with stitched OOS equity curve."""

    model_config = ConfigDict(extra="forbid")

    config: WalkForwardConfig
    windows: list[WalkForwardWindowResult]
    combined_out_of_sample_equity: list[EquityPoint]
    overall_out_of_sample_metrics: BacktestPerformanceMetrics
    mean_walk_forward_efficiency: float
    robustness_score_pct: float


def generate_walk_forward_splits(
    start_date: datetime,
    end_date: datetime,
    config: WalkForwardConfig,
) -> list[WalkForwardSplit]:
    """Generate sequential train/validation time splits according to window config."""
    splits: list[WalkForwardSplit] = []
    curr_train_start = start_date
    curr_train_end = curr_train_start + timedelta(days=config.train_window_days)
    idx = 0

    while True:
        val_start = curr_train_end
        val_end = val_start + timedelta(days=config.validation_window_days)
        if val_end > end_date:
            break

        train_start = start_date if config.anchored else curr_train_start
        splits.append(
            WalkForwardSplit(
                split_index=idx,
                train_start=train_start,
                train_end=curr_train_end,
                validation_start=val_start,
                validation_end=val_end,
            )
        )

        idx += 1
        curr_train_start += timedelta(days=config.step_days)
        curr_train_end += timedelta(days=config.step_days)

    return splits


def run_walk_forward_analysis(
    runner: StockStrategyBacktestRunner,
    config: BacktestConfig,
    wf_config: WalkForwardConfig,
    bars_dataset: dict[str, list[BarRecord]],
) -> WalkForwardResult:
    """Execute walk-forward analysis over historical bar dataset."""
    splits = generate_walk_forward_splits(
        start_date=config.start_date,
        end_date=config.end_date,
        config=wf_config,
    )

    if not splits:
        empty_port = Portfolio.create(initial_cash=config.initial_cash)
        metrics = calculate_backtest_metrics(
            config.initial_cash, empty_port, config.start_date, config.end_date
        )
        return WalkForwardResult(
            config=wf_config,
            windows=[],
            combined_out_of_sample_equity=[],
            overall_out_of_sample_metrics=metrics,
            mean_walk_forward_efficiency=0.0,
            robustness_score_pct=0.0,
        )

    windows: list[WalkForwardWindowResult] = []
    stitched_oos_equity: list[EquityPoint] = []
    current_cash = config.initial_cash
    profitable_windows = 0
    wfe_values: list[float] = []

    for split in splits:
        # 1. In-Sample Backtest
        cfg_is = config.model_copy(
            update={
                "start_date": split.train_start,
                "end_date": split.train_end,
                "initial_cash": current_cash,
            }
        )
        res_is = runner.run(cfg_is, bars_dataset=bars_dataset)

        # 2. Out-of-Sample Backtest
        cfg_oos = config.model_copy(
            update={
                "start_date": split.validation_start,
                "end_date": split.validation_end,
                "initial_cash": current_cash,
            }
        )
        res_oos = runner.run(cfg_oos, bars_dataset=bars_dataset)

        # 3. Walk-Forward Efficiency (CAGR_OOS / CAGR_IS)
        is_cagr = res_is.metrics.cagr_pct
        oos_cagr = res_oos.metrics.cagr_pct
        if is_cagr > 0:
            wfe = oos_cagr / is_cagr
        else:
            wfe = 1.0 if oos_cagr >= 0 else 0.0

        wfe_values.append(wfe)
        if res_oos.metrics.total_pnl > 0:
            profitable_windows += 1

        windows.append(
            WalkForwardWindowResult(
                split=split,
                in_sample_metrics=res_is.metrics,
                out_of_sample_metrics=res_oos.metrics,
                in_sample_cagr_pct=is_cagr,
                out_of_sample_cagr_pct=oos_cagr,
                walk_forward_efficiency=wfe,
            )
        )

        # Stitch OOS equity
        for ep in res_oos.equity_curve:
            stitched_oos_equity.append(ep)

        current_cash = res_oos.metrics.final_equity

    # Overall OOS metrics
    synth_oos_port = Portfolio.create(initial_cash=config.initial_cash)
    synth_oos_port.equity_curve = stitched_oos_equity
    first_val = splits[0].validation_start
    last_val = splits[-1].validation_end

    overall_metrics = calculate_backtest_metrics(
        initial_capital=config.initial_cash,
        portfolio=synth_oos_port,
        start_date=first_val,
        end_date=last_val,
    )

    mean_wfe = sum(wfe_values) / len(wfe_values) if wfe_values else 0.0
    robustness = (profitable_windows / len(splits)) * 100.0 if splits else 0.0

    return WalkForwardResult(
        config=wf_config,
        windows=windows,
        combined_out_of_sample_equity=stitched_oos_equity,
        overall_out_of_sample_metrics=overall_metrics,
        mean_walk_forward_efficiency=mean_wfe,
        robustness_score_pct=robustness,
    )
