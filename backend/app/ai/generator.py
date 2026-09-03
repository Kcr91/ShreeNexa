"""Natural-language StrategyIR generator with strict adversarial prompt safety."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ai.explainer import explain_strategy_ir
from app.ai.redaction import redact_secrets
from app.ai.repair import repair_strategy_ir
from app.strategy.ir import StrategyIR


class GenerationResult(BaseModel):
    """Result of natural-language strategy generation."""

    model_config = ConfigDict(frozen=True)

    strategy_ir: StrategyIR
    strategy_dict: dict[str, Any]
    explanation: str
    warnings: list[str] = Field(default_factory=list)
    draft_status: str = "draft"


# Prohibited adversarial phrases that attempt to bypass safety or order execution
ADVERSARIAL_PATTERNS = [
    r"\b(deploy|activate)\b.*\b(live|immediately|production)\b",
    r"\b(bypass|disable|ignore)\b.*\b(risk|limit|kill[\s_-]?switch|filter)\b",
    r"\b(execute|place|send)\b.*\b(real|live)\b.*\b(order|trade)\b",
    r"\b(drop|delete|truncate)\b.*\b(table|database|schema)\b",
    r"\b(auth|token|credential|key)\b.*\b(steal|leak|export|print)\b",
]


def check_adversarial_safety(prompt: str) -> tuple[bool, list[str]]:
    """Scan prompt for prohibited adversarial deployment or command injection attempts."""
    warnings: list[str] = []
    lower = prompt.lower()
    is_adversarial = False

    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, lower):
            is_adversarial = True
            warnings.append(
                "Security alert: Real-order execution or deployment mutation commands "
                "are prohibited. Output is strictly constrained to an un-deployed StrategyIR draft."
            )
            break

    return is_adversarial, warnings


def _extract_symbol(prompt: str) -> str:
    """Extract known equity or index ticker from prompt text."""
    known_symbols = [
        "RELIANCE",
        "TCS",
        "INFY",
        "HDFCBANK",
        "ICICIBANK",
        "SBIN",
        "BHARTIARTL",
        "KOTAKBANK",
        "LT",
        "ITC",
        "TATAMOTORS",
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
        "MIDCPNIFTY",
    ]
    upper = prompt.upper()
    for s in known_symbols:
        if re.search(rf"\b{s}\b", upper):
            return s
    return "RELIANCE"


def _extract_timeframe(prompt: str) -> str:
    """Extract operational bar timeframe from prompt."""
    lower = prompt.lower()
    m = re.search(r"\b(1m|3m|5m|15m|30m|1h|2h|4h|1d|daily)\b", lower)
    if m:
        val = m.group(1)
        return "1d" if val == "daily" else val
    return "5m" if "intraday" in lower else "1d"


def _extract_sizing(prompt: str) -> dict[str, Any]:
    """Extract sizing parameters from prompt."""
    lower = prompt.lower()
    m_qty = re.search(r"(\d+)\s*(shares|qty|quantity)", lower)
    if m_qty:
        return {"type": "fixed_qty", "qty": int(m_qty.group(1))}

    m_cap = re.search(r"(\d+)\s*(capital|rs|inr|lakh|thousand)", lower)
    if m_cap:
        return {"type": "fixed_value", "value": float(m_cap.group(1))}

    m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(equity|capital|portfolio|risk)", lower)
    if m_pct:
        return {"type": "pct_capital", "pct": float(m_pct.group(1))}

    return {"type": "fixed_qty", "qty": 100}


def _extract_exits(prompt: str) -> list[dict[str, Any]]:
    """Extract stop-loss and take-profit rules from prompt."""
    lower = prompt.lower()
    exits: list[dict[str, Any]] = []

    m_sl = re.search(r"(?:sl|stop[\s_-]?loss|risk)\s*(?:of|at|is)?\s*(\d+(?:\.\d+)?)\s*%", lower)
    m_tp = re.search(
        r"(?:target|take[\s_-]?profit|tp)\s*(?:of|at|is)?\s*(\d+(?:\.\d+)?)\s*%", lower
    )

    sl_val = float(m_sl.group(1)) if m_sl else 2.0
    tp_val = float(m_tp.group(1)) if m_tp else 4.0

    exits.append(
        {
            "id": "exit_stop_loss",
            "type": "stop",
            "pct": sl_val,
        }
    )
    exits.append(
        {
            "id": "exit_take_profit",
            "type": "target",
            "pct": tp_val,
        }
    )
    return exits


def generate_strategy_ir_from_prompt(prompt: str) -> GenerationResult:
    """Compile natural-language description into validated StrategyIR draft with safety checks."""
    # Scrub secrets and check adversarial patterns
    scrubbed = redact_secrets(prompt)
    is_adv, warnings = check_adversarial_safety(scrubbed)

    symbol = _extract_symbol(scrubbed)
    tf = _extract_timeframe(scrubbed)
    sizing = _extract_sizing(scrubbed)
    exits = _extract_exits(scrubbed)
    horizon = "intraday" if tf in ("1m", "3m", "5m", "15m", "30m") else "positional"

    lower = scrubbed.lower()

    # Determine archetype and build indicators/entries
    indicators: dict[str, Any] = {}
    entries: list[dict[str, Any]] = []
    st_type = "trend_following"
    strategy_name = f"{symbol} Strategy Draft"

    # Pattern A: Moving average crossover (e.g. 9/21 EMA or 50/200 SMA)
    if "cross" in lower or "ema" in lower or "sma" in lower or "moving average" in lower:
        fast_period = 9
        slow_period = 21
        m_periods = re.findall(r"\b(\d+)\s*(?:ema|sma|period|bar)\b", lower)
        if len(m_periods) >= 2:
            fast_period = min(int(m_periods[0]), int(m_periods[1]))
            slow_period = max(int(m_periods[0]), int(m_periods[1]))
        elif "golden" in lower:
            fast_period = 50
            slow_period = 200

        fn_type = "SMA" if "sma" in lower else "EMA"
        indicators = {
            "fast_ma": {"fn": fn_type, "params": {"period": fast_period}, "source": "close"},
            "slow_ma": {"fn": fn_type, "params": {"period": slow_period}, "source": "close"},
        }
        entries = [
            {
                "id": "entry_cross_above",
                "side": "BUY",
                "when": {
                    "node": "CrossOver",
                    "left": {"ref": "fast_ma"},
                    "right": {"ref": "slow_ma"},
                },
            }
        ]
        strategy_name = f"{symbol} {fast_period}/{slow_period} {fn_type} Crossover"
        st_type = "trend_following"

    # Pattern B: RSI Mean Reversion
    elif "rsi" in lower or "oversold" in lower or "overbought" in lower:
        thresh = 30.0
        m_thresh = re.search(r"\b(?:below|under|less than)\s*(\d+)\b", lower)
        if m_thresh:
            thresh = float(m_thresh.group(1))

        indicators = {
            "rsi": {"fn": "RSI", "params": {"period": 14}, "source": "close"},
        }
        entries = [
            {
                "id": "entry_rsi_oversold",
                "side": "BUY",
                "when": {
                    "node": "IndicatorCompare",
                    "left": {"ref": "rsi"},
                    "op": "<",
                    "right": thresh,
                },
            }
        ]
        strategy_name = f"{symbol} RSI Oversold Reversion"
        st_type = "mean_reversion"

    # Pattern C: Supertrend breakout
    elif "supertrend" in lower:
        indicators = {
            "supertrend": {
                "fn": "SUPERTREND",
                "params": {"period": 10, "multiplier": 3.0},
                "source": "close",
            },
        }
        entries = [
            {
                "id": "entry_supertrend_bullish",
                "side": "BUY",
                "when": {
                    "node": "IndicatorCompare",
                    "left": {"field": "close"},
                    "op": ">",
                    "right": {"ref": "supertrend"},
                },
            }
        ]
        strategy_name = f"{symbol} Supertrend Breakout"
        st_type = "trend_following"

    # Pattern D: Bollinger Bands squeeze/breakout
    elif "bollinger" in lower or "band" in lower:
        indicators = {
            "bb_upper": {
                "fn": "BOLLINGER",
                "params": {"period": 20, "stddev": 2.0},
                "source": "close",
            },
            "bb_lower": {
                "fn": "BOLLINGER",
                "params": {"period": 20, "stddev": 2.0},
                "source": "close",
            },
        }
        entries = [
            {
                "id": "entry_bb_breakout",
                "side": "BUY",
                "when": {
                    "node": "IndicatorCompare",
                    "left": {"field": "close"},
                    "op": ">",
                    "right": {"ref": "bb_upper"},
                },
            }
        ]
        strategy_name = f"{symbol} Bollinger Breakout"
        st_type = "trend_following"

    # Pattern E: Default fallback price momentum
    else:
        indicators = {
            "fast_ema": {"fn": "EMA", "params": {"period": 20}, "source": "close"},
        }
        entries = [
            {
                "id": "entry_price_above_ema",
                "side": "BUY",
                "when": {
                    "node": "IndicatorCompare",
                    "left": {"field": "close"},
                    "op": ">",
                    "right": {"ref": "fast_ema"},
                },
            }
        ]
        strategy_name = f"{symbol} Price Momentum"
        st_type = "trend_following"

    raw_dict = {
        "schema_version": "1.0",
        "ir_version": 1,
        "name": strategy_name,
        "kind": "stock",
        "horizon": horizon,
        "strategy_type": st_type,
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": symbol, "symbol": symbol}],
        },
        "timeframe": tf,
        "indicators": indicators,
        "entries": entries,
        "exits": exits,
        "sizing": sizing,
        "risk": {
            "max_daily_loss_pct": 3.0,
            "max_position_value_pct": 20.0,
        },
    }

    # Repair & validate against canonical StrategyIR
    repaired_dict, _ = repair_strategy_ir(raw_dict)
    strategy_ir = StrategyIR.from_dict(repaired_dict)
    explanation = explain_strategy_ir(strategy_ir)

    if is_adv:
        warnings.append("Draft-only invariant enforced: strategy has not been deployed.")

    return GenerationResult(
        strategy_ir=strategy_ir,
        strategy_dict=strategy_ir.to_dict(),
        explanation=explanation,
        warnings=warnings,
        draft_status="draft",
    )
