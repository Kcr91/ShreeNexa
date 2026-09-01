"""Indicator primitive implementations across trend, momentum, volatility, volume, and stats."""

from app.indicators.primitives.momentum import (
    ROCIndicator,
    RSIIndicator,
    StochasticIndicator,
)
from app.indicators.primitives.statistical import (
    RollingStdIndicator,
    ZScoreIndicator,
)
from app.indicators.primitives.trend import (
    EMAIndicator,
    MACDIndicator,
    SMAIndicator,
    SupertrendIndicator,
)
from app.indicators.primitives.volatility import (
    ATRIndicator,
    BollingerBandsIndicator,
)
from app.indicators.primitives.volume import (
    OBVIndicator,
    VWAPIndicator,
)
from app.indicators.registry import registry

# Auto-register all primitives in global registry
registry.register(SMAIndicator())
registry.register(EMAIndicator())
registry.register(MACDIndicator())
registry.register(SupertrendIndicator())
registry.register(RSIIndicator())
registry.register(StochasticIndicator())
registry.register(StochasticIndicator(), alias="stochastic")
registry.register(ROCIndicator())
registry.register(ATRIndicator())
registry.register(BollingerBandsIndicator())
registry.register(OBVIndicator())
registry.register(VWAPIndicator())
registry.register(ZScoreIndicator())
registry.register(RollingStdIndicator())

__all__ = [
    "ATRIndicator",
    "BollingerBandsIndicator",
    "EMAIndicator",
    "MACDIndicator",
    "OBVIndicator",
    "ROCIndicator",
    "RSIIndicator",
    "RollingStdIndicator",
    "SMAIndicator",
    "StochasticIndicator",
    "SupertrendIndicator",
    "VWAPIndicator",
    "ZScoreIndicator",
]
