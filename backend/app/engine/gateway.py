"""Risk-filtered broker gateway factory ensuring DhanBroker is never unshielded.

CRITICAL INVARIANTS:
1. No execution path reaches DhanBroker without passing pre-trade risk checks.
2. Direct instantiation of DhanBroker outside this gateway is prohibited.
"""

from __future__ import annotations

from typing import Any

from app.engine.broker import DhanBroker
from app.engine.risk import RiskEngine, RiskFilteredBroker, RiskLimits


def get_risk_filtered_broker(
    limits: RiskLimits | None = None,
    risk_engine: RiskEngine | None = None,
    **broker_kwargs: Any,
) -> RiskFilteredBroker:
    """Construct a DhanBroker exclusively shielded by RiskFilteredBroker.

    Any orders placed through the returned broker instance are unconditionally
    validated against account risk caps, velocity limits, price bands, and
    the emergency kill switch before dispatching to the live Dhan API.
    """
    broker = DhanBroker(**broker_kwargs)
    engine = risk_engine or RiskEngine(limits=limits)
    return RiskFilteredBroker(broker=broker, risk_engine=engine)
