"""Rule-based strategy extraction from strategy-document text.

This is a lightweight, offline, deterministic parser that converts free-form
strategy-description text (typically extracted from a PDF) into a draft
`StrategyIR`. It does NOT call any LLM. It returns a `StrategyIR` plus an
`ExtractionReport` with per-component confidence scores and source snippets
so the user can review before accepting.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.strategy.ir import (
    CompareOp,
    IndicatorDef,
    IndexUniverse,
    EntryRule,
    ExitRule,
    IndicatorCompareNode,
    OrderSide,
    RiskRule,
    SessionConfig,
    SizingRule,
    StrategyHorizon,
    StrategyIR,
    StrategyKind,
    StrategyType,
)

# ---- Public report shapes ----------------------------------------------------


ConfidenceLevel = Literal["high", "medium", "low"]


class ExtractedComponent(BaseModel):
    """A single detected component (indicator, condition, risk param)."""

    description: str
    confidence: ConfidenceLevel
    source_text: str = Field(default="")


class ExtractionComponents(BaseModel):
    """Grouped findings used by the review UI."""

    indicators: list[ExtractedComponent] = Field(default_factory=list)
    entry_conditions: list[ExtractedComponent] = Field(default_factory=list)
    exit_conditions: list[ExtractedComponent] = Field(default_factory=list)
    timeframe: ExtractedComponent | None = None
    risk_params: list[ExtractedComponent] = Field(default_factory=list)


class ExtractionReport(BaseModel):
    """Human-readable per-field report shown next to the auto-filled IR."""

    name: str
    confidence: ConfidenceLevel
    components_found: ExtractionComponents = Field(default_factory=ExtractionComponents)
    warnings: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Full extraction endpoint response shape."""

    success: bool
    extracted_text: str
    strategy_ir: dict[str, Any]
    extraction_report: ExtractionReport


# ---- Rule-based parser -------------------------------------------------------


_INDICATOR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMA", re.compile(r"\b(?:(\d{1,3})[\s-]*(?:period|day|bar)?\s*)?EMA(?:\s*\(?\s*(\d{1,3})\s*\)?)?\b", re.I)),
    ("SMA", re.compile(r"\b(?:(\d{1,3})[\s-]*(?:period|day|bar)?\s*)?SMA(?:\s*\(?\s*(\d{1,3})\s*\)?)?\b", re.I)),
    ("RSI", re.compile(r"\bRSI(?:\s*\(?\s*(\d{1,3})\s*\)?)?\b", re.I)),
    ("MACD", re.compile(r"\bMACD\b", re.I)),
    ("VWAP", re.compile(r"\bVWAP\b", re.I)),
    ("BOLLINGER", re.compile(r"\bBollinger(?:\s*Bands)?\b", re.I)),
    ("ATR", re.compile(r"\bATR(?:\s*\(?\s*(\d{1,3})\s*\)?)?\b", re.I)),
    ("SUPERTREND", re.compile(r"\bSuper[-\s]?Trend\b", re.I)),
    ("ADX", re.compile(r"\bADX(?:\s*\(?\s*(\d{1,3})\s*\)?)?\b", re.I)),
    ("STOCHASTIC", re.compile(r"\bStochastic\b", re.I)),
]

_TIMEFRAME_PATTERN = re.compile(
    r"\b(\d{1,3})[\s-]*(min(?:ute)?|hr|hour|day|daily|wk|week)\b|\b(\d{1,3})(m|h|d|w)\s*(?:chart|timeframe)?\b",
    re.I,
)

_PCT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_SL_PATTERN = re.compile(r"stop[-\s]?loss(?:\s+(?:of|at))?\s+(\d+(?:\.\d+)?)\s*%", re.I)
_TP_PATTERN = re.compile(r"(?:take[-\s]?profit|target)(?:\s+(?:of|at))?\s+(\d+(?:\.\d+)?)\s*%", re.I)
_TRAIL_PATTERN = re.compile(r"trail(?:ing)?\s+stop(?:\s+(?:of|at))?\s+(\d+(?:\.\d+)?)\s*%", re.I)

_ENTRY_HEADINGS = re.compile(
    r"\b(entry(?:\s+conditions?)?|buy\s+signal|when\s+to\s+buy|long\s+entry)\b.*?:?",
    re.I,
)
_EXIT_HEADINGS = re.compile(
    r"\b(exit(?:\s+conditions?)?|sell\s+signal|when\s+to\s+sell|short\s+entry)\b.*?:?",
    re.I,
)

_CROSS_ABOVE = re.compile(r"cross(?:es|ing)?\s+above", re.I)
_CROSS_BELOW = re.compile(r"cross(?:es|ing)?\s+below", re.I)
_GT = re.compile(r"\b(greater\s+than|above|more\s+than|>\s*)\b", re.I)
_LT = re.compile(r"\b(less\s+than|below|under|<\s*)\b", re.I)


def _snippet(text: str, match: re.Match[str], width: int = 60) -> str:
    start = max(0, match.start() - width // 3)
    end = min(len(text), match.end() + width)
    return text[start:end].replace("\n", " ").strip()


def _find_indicators(text: str) -> tuple[dict[str, IndicatorDef], list[ExtractedComponent]]:
    """Return declared indicators and user-facing report rows."""
    indicators: dict[str, IndicatorDef] = {}
    components: list[ExtractedComponent] = []

    for name, pat in _INDICATOR_PATTERNS:
        for m in pat.finditer(text):
            period = None
            groups = [g for g in m.groups() if g and g.isdigit()]
            if groups:
                period = int(groups[0])
            key_base = name.lower()
            key = f"{key_base}_{period}" if period else key_base
            if key in indicators:
                continue
            params: dict[str, Any] = {}
            if period:
                if name in {"MACD"}:
                    continue  # MACD without specific component params → use defaults
                params["period"] = period
            elif name == "RSI":
                params["period"] = 14
            elif name in {"EMA", "SMA", "ATR", "ADX"}:
                params["period"] = 20 if name in {"EMA", "SMA"} else 14
            indicators[key] = IndicatorDef(fn=name, params=params, source="close")
            components.append(
                ExtractedComponent(
                    description=f"{name}{f'({period})' if period else ''}",
                    confidence="high" if period else "medium",
                    source_text=_snippet(text, m),
                )
            )
    return indicators, components


def _find_timeframe(text: str) -> tuple[str, ExtractedComponent | None]:
    m = _TIMEFRAME_PATTERN.search(text)
    if not m:
        return "15m", None

    raw_num = m.group(1) or m.group(3)
    raw_unit = (m.group(2) or m.group(4) or "").lower()
    unit_map = {
        "min": "m", "minute": "m", "m": "m",
        "hr": "h", "hour": "h", "h": "h",
        "day": "D", "daily": "D", "d": "D",
        "wk": "W", "week": "W", "w": "W",
    }
    unit = unit_map.get(raw_unit, "m")
    tf = f"{raw_num}{unit}"
    return tf, ExtractedComponent(
        description=tf,
        confidence="medium",
        source_text=_snippet(text, m),
    )


def _slice_section(text: str, start_regex: re.Pattern[str], stop_regex: re.Pattern[str]) -> str:
    m = start_regex.search(text)
    if not m:
        return ""
    tail = text[m.end():]
    stop = stop_regex.search(tail)
    if stop:
        return tail[: stop.start()].strip()
    return tail.strip()


def _parse_conditions(
    section_text: str,
    indicator_names: list[str],
) -> tuple[list[IndicatorCompareNode], list[ExtractedComponent]]:
    """Return simple IndicatorCompare conditions plus report components."""
    nodes: list[IndicatorCompareNode] = []
    components: list[ExtractedComponent] = []
    if not section_text:
        return nodes, components

    # Look for "<ind> crosses above <ind>" / "<ind> crosses below <ind>"
    for direction, pat in (("CROSS_ABOVE", _CROSS_ABOVE), ("CROSS_BELOW", _CROSS_BELOW)):
        for m in pat.finditer(section_text):
            around_start = max(0, m.start() - 60)
            around_end = min(len(section_text), m.end() + 60)
            window = section_text[around_start:around_end]
            found_inds = [n for n in indicator_names if n in window.lower()]
            if len(found_inds) >= 2:
                left_name = found_inds[0]
                right_name = found_inds[1]
                # Use IndicatorCompare with pseudo-op; the Phase-1 compiler maps
                # CROSS_ABOVE/BELOW to CrossOver/CrossUnder at the IR level, but
                # here we're emitting backend IR directly, so pick GTE/LTE
                # as a conservative stand-in; mark confidence medium.
                op = CompareOp.GT if direction == "CROSS_ABOVE" else CompareOp.LT
                nodes.append(
                    IndicatorCompareNode(
                        left={"ref": left_name},
                        op=op,
                        right={"ref": right_name},
                    )
                )
                components.append(
                    ExtractedComponent(
                        description=f"{left_name} {direction.replace('_', ' ').lower()} {right_name}",
                        confidence="high",
                        source_text=_snippet(section_text, m),
                    )
                )

    # Look for "<ind> > <value>" / "<ind> < <value>"
    for direction, pat in (("GREATER_THAN", _GT), ("LESS_THAN", _LT)):
        for m in pat.finditer(section_text):
            around_start = max(0, m.start() - 40)
            around_end = min(len(section_text), m.end() + 40)
            window = section_text[around_start:around_end]
            for name in indicator_names:
                if name in window.lower():
                    # Pull a number near the operator
                    num_m = re.search(r"-?\d+(?:\.\d+)?", window[window.lower().find(name) :])
                    if num_m:
                        value = float(num_m.group())
                        op = CompareOp.GT if direction == "GREATER_THAN" else CompareOp.LT
                        nodes.append(
                            IndicatorCompareNode(
                                left={"ref": name},
                                op=op,
                                right={"const": value},
                            )
                        )
                        components.append(
                            ExtractedComponent(
                                description=f"{name} {op.value} {value}",
                                confidence="medium",
                                source_text=_snippet(section_text, m),
                            )
                        )
                        break
    return nodes, components


def _find_risk(text: str) -> tuple[float, float, float | None, list[ExtractedComponent]]:
    components: list[ExtractedComponent] = []
    sl = 1.0
    tp = 2.0
    trail: float | None = None

    sl_m = _SL_PATTERN.search(text)
    if sl_m:
        sl = float(sl_m.group(1))
        components.append(
            ExtractedComponent(
                description=f"Stop loss {sl}%",
                confidence="high",
                source_text=_snippet(text, sl_m),
            )
        )

    tp_m = _TP_PATTERN.search(text)
    if tp_m:
        tp = float(tp_m.group(1))
        components.append(
            ExtractedComponent(
                description=f"Target {tp}%",
                confidence="high",
                source_text=_snippet(text, tp_m),
            )
        )

    trail_m = _TRAIL_PATTERN.search(text)
    if trail_m:
        trail = float(trail_m.group(1))
        components.append(
            ExtractedComponent(
                description=f"Trailing stop {trail}%",
                confidence="medium",
                source_text=_snippet(text, trail_m),
            )
        )

    return sl, tp, trail, components


def extract_strategy_from_text(text: str, name: str = "Extracted Strategy") -> ExtractionResult:
    """Rule-based extractor. Pure function, no network, no filesystem."""
    text = text or ""
    warnings: list[str] = []

    indicators_map, indicator_components = _find_indicators(text)
    if not indicators_map:
        warnings.append("No recognised indicators detected; using empty indicator set.")

    tf_value, tf_component = _find_timeframe(text)
    if not tf_component:
        warnings.append("Timeframe not detected; defaulting to 15m.")

    sl_pct, tp_pct, trail_pct, risk_components = _find_risk(text)
    if not risk_components:
        warnings.append("No risk parameters detected; defaulting to 1% stop / 2% target.")

    entry_section = _slice_section(text, _ENTRY_HEADINGS, _EXIT_HEADINGS)
    exit_section = _slice_section(text, _EXIT_HEADINGS, _ENTRY_HEADINGS)
    # Only consider the parsed indicators' keys (lowercased) when looking in sections.
    indicator_keys = list(indicators_map.keys())
    entry_nodes, entry_components = _parse_conditions(entry_section, indicator_keys)
    exit_nodes, exit_components = _parse_conditions(exit_section, indicator_keys)

    entries: list[EntryRule] = []
    if entry_nodes:
        # Combine with And by using a single first node; multiple nodes are
        # left to the user to compose in the visual builder after loading.
        entries.append(EntryRule(id="entry-1", side=OrderSide.BUY, when=entry_nodes[0]))
        if len(entry_nodes) > 1:
            warnings.append(
                f"Found {len(entry_nodes)} entry conditions; only the first was wired. Review in the builder."
            )

    exits: list[ExitRule] = [
        ExitRule(id="exit-sl", type="stop", pct=sl_pct),
        ExitRule(id="exit-tp", type="target", pct=tp_pct),
    ]
    if trail_pct is not None:
        exits.append(ExitRule(id="exit-trail", type="trailing_stop", trailing_pct=trail_pct))

    # Infer archetype
    strat_type = StrategyType.TREND_FOLLOWING
    if any(k.startswith("rsi") for k in indicators_map):
        strat_type = StrategyType.MEAN_REVERSION
        warnings.append("Strategy type inferred as mean_reversion from RSI usage.")
    elif indicators_map:
        warnings.append("Strategy type inferred as trend_following.")

    ir = StrategyIR(
        name=name,
        kind=StrategyKind.STOCK,
        horizon=StrategyHorizon.INTRADAY,
        strategy_type=strat_type,
        universe=IndexUniverse(index_name="NIFTY 50"),
        timeframe=tf_value,
        session=SessionConfig(),
        indicators=indicators_map,
        entries=entries,
        exits=exits,
        sizing=SizingRule(type="fixed_value", value=50_000.0),
        risk=RiskRule(max_positions=5),
    )

    # Overall confidence: high if we found both entries and risk, else medium/low.
    if entries and risk_components:
        overall: ConfidenceLevel = "high"
    elif indicators_map or risk_components:
        overall = "medium"
    else:
        overall = "low"

    report = ExtractionReport(
        name=name,
        confidence=overall,
        components_found=ExtractionComponents(
            indicators=indicator_components,
            entry_conditions=entry_components,
            exit_conditions=exit_components,
            timeframe=tf_component,
            risk_params=risk_components,
        ),
        warnings=warnings,
    )

    return ExtractionResult(
        success=True,
        extracted_text=text,
        strategy_ir=ir.to_dict(),
        extraction_report=report,
    )


# ---- Optional PDF text extraction (pypdf lazy import) -----------------------


def extract_text_from_pdf_bytes(data: bytes) -> str:
    """Lazy-import pypdf; raise RuntimeError with a clear hint if missing."""
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PDF support requires the 'pypdf' package. "
            "Install it with: uv pip install pypdf"
        ) from exc

    import io

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            parts.append("")
    return "\n".join(parts).strip()
