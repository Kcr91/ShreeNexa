"""Explainer generating human-readable natural language descriptions from StrategyIR."""

from __future__ import annotations

from typing import Any

from app.strategy.ir import StrategyIR


def _explain_operand(op: Any) -> str:
    """Format an operand into human-readable text."""
    if isinstance(op, dict):
        if "field" in op:
            return f"bar {op['field']}"
        if "ref" in op:
            return f"indicator '{op['ref']}'"
        if "const" in op:
            return str(op["const"])
    return str(op)


def _explain_condition(node: dict[str, Any] | Any) -> str:
    """Recursively format condition AST node into plain English."""
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("node")
    if node_type == "IndicatorCompare":
        left = _explain_operand(node.get("left"))
        op = node.get("op", "==")
        right = _explain_operand(node.get("right"))
        op_words = {
            ">": "is greater than",
            "<": "is less than",
            ">=": "is at least",
            "<=": "is at most",
            "==": "equals",
            "!=": "does not equal",
        }
        word = op_words.get(op, op)
        return f"{left} {word} {right}"

    if node_type == "CrossOver":
        left = _explain_operand(node.get("left"))
        right = _explain_operand(node.get("right"))
        return f"{left} crosses above {right}"

    if node_type == "CrossUnder":
        left = _explain_operand(node.get("left"))
        right = _explain_operand(node.get("right"))
        return f"{left} crosses below {right}"

    if node_type == "And":
        children = node.get("children", [])
        return " AND ".join(f"({_explain_condition(c)})" for c in children)

    if node_type == "Or":
        children = node.get("children", [])
        return " OR ".join(f"({_explain_condition(c)})" for c in children)

    if node_type == "Not":
        child = node.get("child", {})
        return f"NOT ({_explain_condition(child)})"

    if node_type == "TimeWindow":
        f = node.get("from", node.get("from_time", "09:15"))
        t = node.get("to", node.get("to_time", "15:30"))
        return f"time is between {f} and {t}"

    return str(node)


def explain_strategy_ir(ir_data: dict[str, Any] | StrategyIR) -> str:
    """Generate structured human-readable natural language summary of StrategyIR rules."""
    if isinstance(ir_data, StrategyIR):
        data = ir_data.to_dict()
    else:
        data = dict(ir_data)

    lines: list[str] = []
    name = data.get("name", "Unnamed Strategy")
    kind = data.get("kind", "stock")
    horizon = data.get("horizon", "positional")
    st_type = data.get("strategy_type", "trend_following")
    tf = data.get("timeframe", "1d")

    lines.append(f"### Strategy: {name}")
    lines.append(
        f"- **Profile**: {horizon.capitalize()} {st_type.replace('_', ' ')} strategy "
        f"for {kind} trading on {tf} timeframe."
    )

    # Universe
    univ = data.get("universe", {})
    if isinstance(univ, dict):
        insts = univ.get("instruments", [])
        if insts:
            symbols = [i.get("symbol") or i.get("security_id") for i in insts]
            lines.append(f"- **Traded Universe**: {', '.join(str(s) for s in symbols)}")

    # Indicators
    inds = data.get("indicators", {})
    if inds:
        lines.append("- **Indicators**:")
        for k, v in inds.items():
            fn = v.get("fn", "CUSTOM")
            params = v.get("params", {})
            param_str = ", ".join(f"{pk}={pv}" for pk, pv in params.items())
            lines.append(f"  - `{k}`: {fn}({param_str}) on {v.get('source', 'close')}")

    # Entries
    entries = data.get("entries", [])
    if entries:
        lines.append("- **Entry Rules**:")
        for e in entries:
            side = e.get("side", "BUY")
            eid = e.get("id", "entry")
            cond_str = _explain_condition(e.get("when", {}))
            lines.append(f"  - [{side}] `{eid}`: Enter when {cond_str}")

    # Exits
    exits = data.get("exits", [])
    if exits:
        lines.append("- **Exit Rules**:")
        for x in exits:
            xid = x.get("id", "exit")
            xtype = x.get("type", "stop")
            pct = x.get("pct")
            desc_parts = []
            if pct is not None:
                desc_parts.append(f"{xtype.replace('_', ' ').capitalize()} at {pct}%")
            else:
                desc_parts.append(xtype.replace("_", " ").capitalize())
            if "when" in x:
                desc_parts.append(f"Condition: {_explain_condition(x['when'])}")
            lines.append(f"  - `{xid}`: {', '.join(desc_parts)}")

    # Sizing
    sizing = data.get("sizing", {})
    if sizing:
        stype = sizing.get("type", "fixed_qty")
        if stype == "fixed_qty":
            lines.append(
                f"- **Position Sizing**: Fixed quantity of {sizing.get('qty', 100)} shares."
            )
        elif stype == "fixed_value":
            lines.append(
                f"- **Position Sizing**: Fixed value of ₹{sizing.get('value', 100000)} per trade."
            )
        elif stype in ("pct_capital", "pct_equity"):
            lines.append(
                f"- **Position Sizing**: {sizing.get('pct', 5.0)}% of total portfolio capital."
            )

    return "\n".join(lines)
