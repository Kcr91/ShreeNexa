"""Unit tests for versioned regime detectors and walk-forward verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.strategy import (
    IncrementalStrategyEngine,
    RegimeDetectorRegistry,
    StrategyIR,
    TrendRegimeDetector_v1,
    UnknownRegimeDetectorError,
    VectorStrategyCompiler,
    VolRegimeDetector_v1,
    WalkForwardEvidenceRequiredError,
    has_regime_conditioning,
    validate_headline_metrics_evidence,
)
from app.warehouse.schema import BarRecord


def _make_strategy_with_regime(
    detector: str = "trend_v1",
    state: str = "trending_up",
) -> StrategyIR:
    return StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": f"RegimeStrategy_{detector}_{state}",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1d",
            "entries": [
                {
                    "id": "e_regime",
                    "type": "buy",
                    "when": {
                        "node": "Regime",
                        "detector": detector,
                        "state": state,
                    },
                }
            ],
        }
    )


def _generate_synthetic_bars(n: int = 50) -> list[BarRecord]:
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    # Price path: 15 flat bars, 15 trending bars, 20 high-volatility bars
    prices: list[float] = []
    p = 100.0
    for i in range(n):
        if i < 15:
            p += 0.05 * ((i % 2) * 2 - 1)
        elif i < 30:
            p += 1.5
        else:
            p += 3.0 * ((i % 2) * 2 - 1)
        prices.append(p)

    return [
        BarRecord(
            symbol="TEST",
            exchange_segment="NSE_EQ",
            security_id="1333",
            timestamp=t0 + timedelta(minutes=i),
            open=p - 0.5,
            high=p + 1.0,
            low=p - 1.0,
            close=p,
            volume=1000,
            open_interest=0,
        )
        for i, p in enumerate(prices)
    ]


def test_lookahead_prevention_point_in_time_invariant() -> None:
    """Proof that no regime label uses future bars: truncated evaluation equals full series at t."""
    bars = _generate_synthetic_bars(50)
    closes = [b.close for b in bars]

    trend_detector = TrendRegimeDetector_v1()
    vol_detector = VolRegimeDetector_v1()

    full_trend_states = trend_detector.evaluate_series(closes)
    full_vol_states = vol_detector.evaluate_series(closes)

    # For multiple arbitrary historical horizons t, verify truncated evaluation matches full series
    for t in [15, 20, 25, 30, 35, 40, 49]:
        truncated_closes = closes[: t + 1]

        t_trend = TrendRegimeDetector_v1().evaluate_series(truncated_closes)
        assert t_trend[-1] == full_trend_states[t], (
            f"Look-ahead detected in TrendRegimeDetector at bar {t}: "
            f"truncated={t_trend[-1]} vs full={full_trend_states[t]}"
        )

        t_vol = VolRegimeDetector_v1().evaluate_series(truncated_closes)
        assert t_vol[-1] == full_vol_states[t], (
            f"Look-ahead detected in VolRegimeDetector at bar {t}: "
            f"truncated={t_vol[-1]} vs full={full_vol_states[t]}"
        )


def test_versioned_regime_detector_registry() -> None:
    detectors = RegimeDetectorRegistry.list_detectors()
    assert "trend_v1" in detectors
    assert "vol_v1" in detectors

    trend_inst = RegimeDetectorRegistry.get("trend_v1")
    assert isinstance(trend_inst, TrendRegimeDetector_v1)
    assert trend_inst.version == "1.0.0"
    assert "trending_up" in trend_inst.supported_states

    vol_inst = RegimeDetectorRegistry.get("vol_v1")
    assert isinstance(vol_inst, VolRegimeDetector_v1)
    assert vol_inst.version == "1.0.0"
    assert "high_vol" in vol_inst.supported_states

    with pytest.raises(UnknownRegimeDetectorError):
        RegimeDetectorRegistry.get("non_existent_detector_v99")


def test_regime_node_g1_g2_parity() -> None:
    """Verify bit-for-bit parity between G1 vectorized and G2 streaming incremental execution."""
    bars = _generate_synthetic_bars(40)

    for detector, state in [("trend_v1", "trending_up"), ("vol_v1", "high_vol")]:
        strategy = _make_strategy_with_regime(detector=detector, state=state)

        # G1: Vectorized batch evaluation
        compiler = VectorStrategyCompiler.compile(strategy)
        g1_result = compiler.evaluate(bars)
        g1_mask = g1_result.entry_signals["e_regime"]

        # G2: Streaming incremental evaluation
        engine = IncrementalStrategyEngine(strategy)
        g2_mask = [engine.update(b).entry_signals["e_regime"] for b in bars]

        assert g1_mask == g2_mask, (
            f"G1/G2 parity failure on RegimeNode({detector}, {state}):\n"
            f"G1: {g1_mask}\n"
            f"G2: {g2_mask}"
        )


def test_has_regime_conditioning_detection() -> None:
    # Standard non-regime strategy
    plain_strategy = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "PlainCrossover",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1d",
            "entries": [
                {
                    "id": "e_plain",
                    "type": "buy",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 100.0,
                    },
                }
            ],
        }
    )
    assert not has_regime_conditioning(plain_strategy)

    # Strategy with nested RegimeNode
    regime_strategy = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "NestedRegimeStrategy",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1d",
            "entries": [
                {
                    "id": "e_nested",
                    "type": "buy",
                    "when": {
                        "node": "And",
                        "children": [
                            {
                                "node": "IndicatorCompare",
                                "left": {"field": "close"},
                                "op": ">",
                                "right": 100.0,
                            },
                            {
                                "node": "Regime",
                                "detector": "trend_v1",
                                "state": "trending_up",
                            },
                        ],
                    },
                }
            ],
        }
    )
    assert has_regime_conditioning(regime_strategy)


def test_enforced_walk_forward_headline_metrics_refused() -> None:
    """Proof that headline metrics are refused without walk-forward evidence."""
    regime_strategy = _make_strategy_with_regime("trend_v1", "trending_up")
    plain_strategy = StrategyIR.model_validate(
        {
            "ir_version": 1,
            "name": "PlainCrossover",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "trend_following",
            "universe": {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": "1333"}],
            },
            "timeframe": "1d",
            "entries": [
                {
                    "id": "e_plain",
                    "type": "buy",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"field": "close"},
                        "op": ">",
                        "right": 100.0,
                    },
                }
            ],
        }
    )

    # 1. Non-regime strategy requires no walk-forward evidence
    validate_headline_metrics_evidence(plain_strategy, None)

    # 2. Regime strategy without walk-forward evidence is REFUSED
    with pytest.raises(WalkForwardEvidenceRequiredError) as exc_info:
        validate_headline_metrics_evidence(regime_strategy, None)
    assert "Headline metrics refused" in str(exc_info.value)
    assert "no walk-forward analysis evidence" in str(exc_info.value)

    class _MockWF:
        def __init__(self, mean_wfe: float) -> None:
            self.mean_walk_forward_efficiency = mean_wfe

    # 3. Regime strategy with non-positive walk-forward efficiency is REFUSED
    failing_wf = _MockWF(mean_wfe=-0.25)
    with pytest.raises(WalkForwardEvidenceRequiredError) as exc_info:
        validate_headline_metrics_evidence(regime_strategy, failing_wf)
    assert "must be positive" in str(exc_info.value)

    # 4. Regime strategy with valid positive walk-forward efficiency is ACCEPTED
    valid_wf = _MockWF(mean_wfe=0.67)
    validate_headline_metrics_evidence(regime_strategy, valid_wf)
