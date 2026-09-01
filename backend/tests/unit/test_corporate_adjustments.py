"""Unit tests for corporate action adjustment pipeline and point-in-time preservation."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from app.marketdata.adjustments import (
    ActionType,
    AdjustmentPipeline,
    CorporateAction,
)
from app.warehouse.schema import BarRecord, bars_to_arrow_table

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_corporate_actions.json"


def test_split_factor_and_bar_adjustments() -> None:
    """Verify 1:5 stock split adjusts prior prices by 0.2 and multiplies volume by 5x."""
    split_action = CorporateAction(
        symbol="TATAMOTORS",
        action_type=ActionType.SPLIT,
        ex_date=date(2026, 6, 15),
        ratio_numerator=1.0,
        ratio_denominator=5.0,
    )
    assert split_action.calculate_factor() == 0.2

    pipeline = AdjustmentPipeline([split_action])

    bar_pre = BarRecord(
        timestamp=datetime(2026, 6, 12, 10, 0, tzinfo=UTC),
        exchange_segment="NSE_EQ",
        security_id="3456",
        symbol="TATAMOTORS",
        open=1000.0,
        high=1020.0,
        low=990.0,
        close=1010.0,
        volume=100000,
        open_interest=0,
    )
    bar_post = BarRecord(
        timestamp=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        exchange_segment="NSE_EQ",
        security_id="3456",
        symbol="TATAMOTORS",
        open=202.0,
        high=205.0,
        low=199.0,
        close=204.0,
        volume=500000,
        open_interest=0,
    )

    adjusted = pipeline.adjust_bars([bar_pre, bar_post])
    assert len(adjusted) == 2

    # Pre-split bar adjusted
    adj_pre = adjusted[0]
    assert adj_pre.open == 200.0
    assert adj_pre.high == 204.0
    assert adj_pre.low == 198.0
    assert adj_pre.close == 202.0
    assert adj_pre.volume == 500000

    # Post-split bar untouched
    adj_post = adjusted[1]
    assert adj_post.open == 202.0
    assert adj_post.close == 204.0
    assert adj_post.volume == 500000


def test_bonus_issue_and_fixture_parity() -> None:
    """Verify 1:1 bonus issue against sample_corporate_actions.json fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    actions = [
        CorporateAction(
            symbol=a["symbol"],
            action_type=ActionType(a["action_type"]),
            ex_date=date.fromisoformat(a["ex_date"]),
            ratio_numerator=a["ratio_numerator"],
            ratio_denominator=a["ratio_denominator"],
        )
        for a in data["corporate_actions"]
    ]
    pipeline = AdjustmentPipeline(actions)

    infy_bars: list[BarRecord] = []
    for item in data["infy_sample_bars"]:
        d = date.fromisoformat(item["date"])
        infy_bars.append(
            BarRecord(
                timestamp=datetime(d.year, d.month, d.day, 10, 0, tzinfo=UTC),
                exchange_segment="NSE_EQ",
                security_id="1594",
                symbol="INFY",
                open=item["unadjusted"]["open"],
                high=item["unadjusted"]["high"],
                low=item["unadjusted"]["low"],
                close=item["unadjusted"]["close"],
                volume=item["unadjusted"]["volume"],
                open_interest=0,
            )
        )

    adjusted = pipeline.adjust_bars(infy_bars)
    assert len(adjusted) == 2

    # Verify 2024-09-11 (pre bonus) matches expected fixture values
    assert adjusted[0].open == data["infy_sample_bars"][0]["expected_adjusted"]["open"]
    assert adjusted[0].close == data["infy_sample_bars"][0]["expected_adjusted"]["close"]
    assert adjusted[0].volume == data["infy_sample_bars"][0]["expected_adjusted"]["volume"]

    # Verify 2024-09-12 (ex-date) is untouched
    assert adjusted[1].open == data["infy_sample_bars"][1]["expected_adjusted"]["open"]
    assert adjusted[1].close == data["infy_sample_bars"][1]["expected_adjusted"]["close"]
    assert adjusted[1].volume == data["infy_sample_bars"][1]["expected_adjusted"]["volume"]


def test_chained_cumulative_adjustments() -> None:
    """Verify compounding multi-event adjustments backwards in time."""
    # 1:1 bonus in 2024 (factor 0.5) + 1:5 split in 2026 (factor 0.2)
    bonus = CorporateAction(
        symbol="ABC",
        action_type=ActionType.BONUS,
        ex_date=date(2024, 6, 1),
        ratio_numerator=1.0,
        ratio_denominator=1.0,
    )
    split = CorporateAction(
        symbol="ABC",
        action_type=ActionType.SPLIT,
        ex_date=date(2026, 6, 1),
        ratio_numerator=1.0,
        ratio_denominator=5.0,
    )
    pipeline = AdjustmentPipeline([bonus, split])

    # Target date before 2024 bonus: cumulative factor = 0.5 * 0.2 = 0.1
    f_early = pipeline.get_cumulative_factor("ABC", date(2023, 1, 1))
    assert abs(f_early - 0.1) < 1e-9

    # Target date between bonus and split: cumulative factor = 0.2
    f_mid = pipeline.get_cumulative_factor("ABC", date(2025, 1, 1))
    assert abs(f_mid - 0.2) < 1e-9

    # Target date after split: cumulative factor = 1.0
    f_late = pipeline.get_cumulative_factor("ABC", date(2027, 1, 1))
    assert abs(f_late - 1.0) < 1e-9


def test_dividend_adjustment_factor() -> None:
    """Verify cash dividend factor calculation with reference close."""
    div_action = CorporateAction(
        symbol="COALINDIA",
        action_type=ActionType.DIVIDEND,
        ex_date=date(2026, 8, 10),
        dividend_amount=15.0,
    )
    # If reference close prior to ex-date was 300.0: factor = (300 - 15) / 300 = 0.95
    factor = div_action.calculate_factor(reference_close=300.0)
    assert round(factor, 4) == 0.95


def test_unadjusted_data_immutability_and_arrow_table() -> None:
    """Verify adjustments produce new records and preserve unadjusted inputs."""
    split = CorporateAction(
        symbol="XYZ",
        action_type=ActionType.SPLIT,
        ex_date=date(2026, 1, 1),
        ratio_numerator=1.0,
        ratio_denominator=2.0,
    )
    pipeline = AdjustmentPipeline([split])

    original_bar = BarRecord(
        timestamp=datetime(2025, 12, 31, 10, 0, tzinfo=UTC),
        exchange_segment="NSE_EQ",
        security_id="9999",
        symbol="XYZ",
        open=500.0,
        high=510.0,
        low=495.0,
        close=505.0,
        volume=10000,
        open_interest=0,
    )
    bars_input = [original_bar]

    table_input = bars_to_arrow_table(bars_input)
    table_adj = pipeline.adjust_table(table_input)

    # Input object is unchanged
    assert original_bar.open == 500.0
    assert original_bar.close == 505.0

    # Adjusted table reflects 1:2 split (factor 0.5)
    adj_open = table_adj.column("open").to_pylist()[0]
    adj_vol = table_adj.column("volume").to_pylist()[0]
    assert adj_open == 250.0
    assert adj_vol == 20000
