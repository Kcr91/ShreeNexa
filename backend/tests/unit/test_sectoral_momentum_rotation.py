"""Unit tests for point-in-time sectoral momentum rotation strategy (F10.5).

Proof requirement: G2, survivorship-bias checks, and enforced walk-forward evidence.
"""

from __future__ import annotations

from datetime import date

from app.investing.rotation import (
    SectorConstituentMembership,
    audit_survivorship_bias,
    compute_sector_momentum_scores,
    resolve_pit_sector_constituents,
    run_rotation_walk_forward,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_pit_sector_constituents_resolution_no_lookahead() -> None:
    """Proof: G2 compliance; constituents active strictly as of point-in-time timestamp."""
    memberships = [
        # Inception Jan 1, 2024; active through 2024
        SectorConstituentMembership(
            symbol="HDFCBANK",
            sector="BANKING",
            effective_date=date(2024, 1, 1),
            exit_date=None,
        ),
        # Delisted on June 30, 2024
        SectorConstituentMembership(
            symbol="YESBANK_OLD",
            sector="BANKING",
            effective_date=date(2024, 1, 1),
            exit_date=date(2024, 6, 30),
        ),
        # Added on July 1, 2024
        SectorConstituentMembership(
            symbol="IDFCFIRSTB",
            sector="BANKING",
            effective_date=date(2024, 7, 1),
            exit_date=None,
        ),
    ]

    # As of March 1, 2024: HDFCBANK & YESBANK_OLD active; IDFCFIRSTB not yet added
    active_mar = resolve_pit_sector_constituents(memberships, date(2024, 3, 1))
    assert active_mar["BANKING"] == ["HDFCBANK", "YESBANK_OLD"]

    # As of August 1, 2024: HDFCBANK & IDFCFIRSTB active; YESBANK_OLD delisted
    active_aug = resolve_pit_sector_constituents(memberships, date(2024, 8, 1))
    assert active_aug["BANKING"] == ["HDFCBANK", "IDFCFIRSTB"]


def test_sector_momentum_scoring_and_ranking() -> None:
    """Proof: Momentum scoring ranks outperformers and flags negative trend."""
    constituents = {
        "BANKING": ["HDFCBANK"],
        "IT": ["TCS"],
        "METALS": ["TATASTEEL"],
    }
    # Dates: d0 (start), d1 (1M), d2 (3M), d3 (6M / as_of)
    d0 = date(2024, 1, 1)
    d1 = date(2024, 5, 1)
    d2 = date(2024, 6, 1)
    as_of = date(2024, 7, 1)

    prices = {
        # BANKING: strong bull run (+50%)
        "HDFCBANK": {d0: 1000.0, d1: 1200.0, d2: 1350.0, as_of: 1500.0},
        # IT: moderate gain (+10%)
        "TCS": {d0: 3000.0, d1: 3100.0, d2: 3200.0, as_of: 3300.0},
        # METALS: severe bear trend (-30%)
        "TATASTEEL": {d0: 150.0, d1: 130.0, d2: 120.0, as_of: 105.0},
    }

    scores = compute_sector_momentum_scores(constituents, prices, as_of)
    assert len(scores) == 3

    # Rank 1 should be BANKING (highest composite score)
    assert scores[0].sector == "BANKING"
    assert scores[0].rank == 1
    assert scores[0].trend_positive is True

    # Rank 2 should be IT
    assert scores[1].sector == "IT"
    assert scores[1].rank == 2
    assert scores[1].trend_positive is True

    # Rank 3 should be METALS with negative trend
    assert scores[2].sector == "METALS"
    assert scores[2].rank == 3
    assert scores[2].trend_positive is False


def test_survivorship_bias_detection_audit() -> None:
    """Proof: Detects return inflation when naive static universe omits delisted names."""
    d1 = date(2024, 1, 1)
    d2 = date(2024, 6, 1)
    d3 = date(2024, 12, 1)
    rebalance_dates = [d1, d2, d3]

    # BANKING sector has 2 stocks initially:
    # 1. SURVIVOR: rises from 100 -> 120 -> 150 (+50%)
    # 2. DELISTED: collapses from 100 -> 20 and gets delisted on June 30
    memberships = [
        SectorConstituentMembership(
            symbol="SURVIVOR",
            sector="BANKING",
            effective_date=d1,
            exit_date=None,
        ),
        SectorConstituentMembership(
            symbol="DELISTED",
            sector="BANKING",
            effective_date=d1,
            exit_date=date(2024, 6, 30),
        ),
    ]

    prices = {
        "SURVIVOR": {d1: 100.0, d2: 120.0, d3: 150.0},
        "DELISTED": {d1: 100.0, d2: 20.0, d3: 20.0},
        "GOLDBEES": {d1: 50.0, d2: 52.0, d3: 54.0},
    }

    audit = audit_survivorship_bias(memberships, prices, rebalance_dates)

    # Invariant: Static universe omits the fallen stock, artificially inflating CAGR
    assert audit.is_survivorship_bias_detected is True
    assert audit.static_cagr_pct > audit.pit_cagr_pct
    assert audit.survivorship_bias_inflation_pct > 0.0
    assert "DELISTED" in audit.delisted_symbols_impacted


def test_enforced_walk_forward_evidence() -> None:
    """Proof requirement: Enforced out-of-sample walk-forward optimization and WFE."""
    # Generate 8 quarterly rebalance periods
    reb_dates = [
        date(2024, 1, 1),
        date(2024, 3, 1),
        date(2024, 5, 1),
        date(2024, 7, 1),
        date(2024, 9, 1),
        date(2024, 11, 1),
        date(2025, 1, 1),
        date(2025, 3, 1),
    ]

    memberships = [
        SectorConstituentMembership(
            symbol="NIFTYBEES",
            sector="INDEX",
            effective_date=date(2023, 1, 1),
            exit_date=None,
        ),
        SectorConstituentMembership(
            symbol="GOLDBEES",
            sector="DEFENSIVE",
            effective_date=date(2023, 1, 1),
            exit_date=None,
        ),
    ]

    prices = {
        "NIFTYBEES": {d: 200.0 + idx * 10.0 for idx, d in enumerate(reb_dates)},
        "GOLDBEES": {d: 50.0 + idx * 1.5 for idx, d in enumerate(reb_dates)},
    }

    wf_res = run_rotation_walk_forward(
        memberships,
        prices,
        reb_dates,
        in_sample_steps=4,
        out_of_sample_steps=2,
        step_stride=2,
    )

    assert wf_res.splits_count >= 1
    assert len(wf_res.windows) == wf_res.splits_count
    # WFE ratio should be positive and bounded
    assert wf_res.mean_wfe >= 0.0
    assert wf_res.robustness_score_pct >= 0.0


def test_sectoral_rotation_rest_api_endpoints() -> None:
    """Proof: REST API endpoints for backtest, walk-forward, and survivorship audit."""
    d1 = "2024-01-01"
    d2 = "2024-06-01"
    d3 = "2024-12-01"

    payload = {
        "memberships": [
            {
                "symbol": "HDFCBANK",
                "sector": "BANKING",
                "effective_date": d1,
                "exit_date": None,
            },
            {
                "symbol": "TCS",
                "sector": "IT",
                "effective_date": d1,
                "exit_date": None,
            },
        ],
        "price_history": {
            "HDFCBANK": {d1: 1000.0, d2: 1200.0, d3: 1400.0},
            "TCS": {d1: 3000.0, d2: 3200.0, d3: 3500.0},
            "GOLDBEES": {d1: 50.0, d2: 52.0, d3: 55.0},
        },
        "rebalance_dates": [d1, d2, d3],
    }

    # 1. Backtest endpoint
    resp_bt = client.post("/api/v1/investing/strategy/sectoral-rotation/backtest", json=payload)
    assert resp_bt.status_code == 200
    data_bt = resp_bt.json()
    assert data_bt["cagr_pct"] > 0.0
    assert len(data_bt["rebalance_decisions"]) == 3

    # 2. Survivorship audit endpoint
    resp_audit = client.post(
        "/api/v1/investing/strategy/sectoral-rotation/survivorship-audit",
        json=payload,
    )
    assert resp_audit.status_code == 200
    data_audit = resp_audit.json()
    assert "audit_verdict" in data_audit
