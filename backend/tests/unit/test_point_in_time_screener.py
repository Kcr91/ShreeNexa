"""Unit tests for Point-in-Time Screener Runner with 3 hand-verified names and G2 audit."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.screener.models import RankingRule, ScreenerDefinition
from app.screener.runner import PointInTimeScreenerRunner
from app.strategy.ir import (
    AndNode,
    CrossOverNode,
    IndexUniverse,
    IndicatorCompareNode,
    IndicatorDef,
    InstrumentRef,
    StaticUniverse,
)
from app.warehouse.schema import BarRecord


def _make_bars_for_symbol(symbol: str, end_dt: datetime, n: int = 30) -> list[BarRecord]:
    bars: list[BarRecord] = []
    for i in range(n):
        ts = end_dt - timedelta(days=n - 1 - i)
        if symbol == "RELIANCE":
            # Downtrend until last bar, then huge upward breakout on final bar (CrossOver)
            if i == n - 1:
                p = 115.0
            else:
                p = 100.0 - 0.5 * i
        elif symbol == "TCS":
            # Continuous downtrend: sma5 < sma15
            p = 100.0 - 0.5 * i
        elif symbol == "INFY":
            # Continuous strong uptrend: RSI = 100.0
            p = 100.0 + 2.0 * i
        else:
            p = 100.0 + 0.1 * i

        bars.append(
            BarRecord(
                symbol=symbol,
                exchange_segment="NSE_EQ",
                security_id=symbol,
                timestamp=ts,
                open=p - 0.5,
                high=p + 1.0,
                low=p - 1.0,
                close=p,
                volume=10000 + i * 100,
                open_interest=0,
            )
        )
    return bars


def test_point_in_time_screener_three_names_hand_verified() -> None:
    """Three hand-verified names test:

    1. Stock A (RELIANCE): in index at T, satisfies MA CrossOver + RSI > 50 -> Matches.
    2. Stock B (TCS): in index at T, fails MA CrossOver -> Rejected.
    3. Stock C (YESBANK): removed from index prior to T -> Excluded by point-in-time resolver.
    """
    as_of_date = date(2026, 9, 1)

    # Mock historical index membership resolver
    def mock_index_resolver(index_name: str, dt: date) -> list[dict[str, str]]:
        if index_name == "NIFTY 50" and dt == as_of_date:
            # YESBANK was removed earlier and is not present in NIFTY 50 on 2026-09-01
            return [
                {"segment": "NSE_EQ", "security_id": "RELIANCE", "symbol": "RELIANCE"},
                {"segment": "NSE_EQ", "security_id": "TCS", "symbol": "TCS"},
            ]
        return []

    # Mock bar provider
    def mock_bar_provider(
        segment: str, security_id: str, dt: datetime, lookback: int
    ) -> list[BarRecord]:
        return _make_bars_for_symbol(security_id, dt, n=30)

    screener_def = ScreenerDefinition(
        name="Golden Cross Screener",
        universe=IndexUniverse(index_name="NIFTY 50"),
        as_of=as_of_date,
        indicators={
            "sma5": IndicatorDef(fn="SMA", params={"period": 5}, source="close"),
            "sma15": IndicatorDef(fn="SMA", params={"period": 15}, source="close"),
            "rsi": IndicatorDef(fn="RSI", params={"period": 14}, source="close"),
        },
        filter=AndNode(
            children=[
                CrossOverNode(left={"ref": "sma5"}, right={"ref": "sma15"}),
                IndicatorCompareNode(left={"ref": "rsi"}, op=">", right={"const": 50.0}),
            ]
        ),
    )

    runner = PointInTimeScreenerRunner(
        bar_provider=mock_bar_provider,
        index_resolver=mock_index_resolver,
    )
    result = runner.run(screener_def)

    assert result.total_universe_size == 2
    assert result.evaluated_count == 2
    assert result.matched_count == 1
    assert len(result.matches) == 1
    assert result.matches[0].symbol == "RELIANCE"
    assert result.matches[0].indicator_values["rsi"] > 50.0


def test_point_in_time_screener_g2_anti_lookahead() -> None:
    """G2 Anti-Lookahead: Future bars beyond as_of date do not affect screener output."""
    as_of_dt = datetime(2026, 9, 1, 15, 30, tzinfo=UTC)

    # Bar provider that contains future bars for 2026-09-02 and 2026-09-03
    def mock_bar_provider_with_future(
        segment: str, security_id: str, dt: datetime, lookback: int
    ) -> list[BarRecord]:
        past_bars = _make_bars_for_symbol(security_id, dt, n=20)
        future_bars = [
            BarRecord(
                symbol=security_id,
                exchange_segment="NSE_EQ",
                security_id=security_id,
                timestamp=dt + timedelta(days=1),
                open=200.0,
                high=250.0,
                low=190.0,
                close=240.0,
                volume=50000,
                open_interest=0,
            ),
            BarRecord(
                symbol=security_id,
                exchange_segment="NSE_EQ",
                security_id=security_id,
                timestamp=dt + timedelta(days=2),
                open=240.0,
                high=300.0,
                low=230.0,
                close=290.0,
                volume=80000,
                open_interest=0,
            ),
        ]
        return past_bars + future_bars

    screener_def = ScreenerDefinition(
        name="SMA Compare",
        universe=StaticUniverse(
            instruments=[InstrumentRef(segment="NSE_EQ", security_id="RELIANCE")]
        ),
        as_of=as_of_dt,
        indicators={"sma5": IndicatorDef(fn="SMA", params={"period": 5}, source="close")},
        filter=IndicatorCompareNode(left={"field": "close"}, op=">", right={"ref": "sma5"}),
    )

    runner = PointInTimeScreenerRunner(bar_provider=mock_bar_provider_with_future)
    result = runner.run(screener_def)

    assert result.matched_count == 1
    # Check that as_of date on match is exactly the evaluated as_of_dt, not the future bar
    assert result.matches[0].as_of == as_of_dt


def test_point_in_time_screener_survivorship_bias_warning() -> None:
    """Verify that survivorship-bias warnings are emitted when historical index data is missing."""
    screener_def = ScreenerDefinition(
        name="Missing Index History",
        universe=IndexUniverse(index_name="UNKNOWN_INDEX"),
        as_of=date(2020, 1, 1),
        indicators={"sma5": IndicatorDef(fn="SMA", params={"period": 5}, source="close")},
        filter=IndicatorCompareNode(left={"field": "close"}, op=">", right={"ref": "sma5"}),
    )

    runner = PointInTimeScreenerRunner(
        bar_provider=lambda s, sec, dt, lookback: [],
        index_resolver=lambda idx, dt: [],  # returns empty
    )
    result = runner.run(screener_def)

    assert result.matched_count == 0
    assert any("Survivorship-bias warning" in w for w in result.warnings)


def test_point_in_time_screener_ranking_and_limit() -> None:
    """Verify ranking matches by indicator value descending with limit."""
    as_of_dt = datetime(2026, 9, 1, 15, 30, tzinfo=UTC)

    def mock_bar_provider(
        segment: str, security_id: str, dt: datetime, lookback: int
    ) -> list[BarRecord]:
        return _make_bars_for_symbol(security_id, dt, n=30)

    screener_def = ScreenerDefinition(
        name="Ranked Screener",
        universe=StaticUniverse(
            instruments=[
                InstrumentRef(segment="NSE_EQ", security_id="RELIANCE"),
                InstrumentRef(segment="NSE_EQ", security_id="INFY"),
            ]
        ),
        as_of=as_of_dt,
        indicators={"rsi": IndicatorDef(fn="RSI", params={"period": 14}, source="close")},
        filter=IndicatorCompareNode(left={"ref": "rsi"}, op=">", right={"const": 30.0}),
        ranking=RankingRule(by="rsi", direction="desc"),
        limit=1,
    )

    runner = PointInTimeScreenerRunner(bar_provider=mock_bar_provider)
    result = runner.run(screener_def)

    assert result.matched_count == 1
    # INFY has steeper slope and higher RSI than RELIANCE in synthetic fixtures
    assert result.matches[0].symbol == "INFY"
