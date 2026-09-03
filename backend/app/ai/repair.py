"""Repair engine for malformed or incomplete StrategyIR drafts."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.strategy.ir import StrategyIR


def repair_strategy_ir(raw_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Inspect and repair malformed StrategyIR, returning repaired dict and repair log."""
    data = dict(raw_data)
    repairs: list[str] = []

    # 1. ir_version
    if "ir_version" not in data or not isinstance(data["ir_version"], int):
        data["ir_version"] = 1
        repairs.append("Set default 'ir_version'=1")

    # 2. name
    if "name" not in data or not isinstance(data["name"], str) or not data["name"].strip():
        data["name"] = "Repaired Strategy Draft"
        repairs.append("Assigned default strategy name")

    # 3. timeframe
    if "timeframe" not in data or not isinstance(data["timeframe"], str):
        data["timeframe"] = "1d"
        repairs.append("Defaulted timeframe to '1d'")

    # 4. horizon
    if "horizon" not in data or data["horizon"] not in (
        "intraday",
        "swing",
        "positional",
        "investing",
    ):
        tf = data.get("timeframe", "1d")
        if tf in ("1m", "3m", "5m", "15m", "30m"):
            data["horizon"] = "intraday"
        elif tf in ("1h", "2h", "4h"):
            data["horizon"] = "swing"
        else:
            data["horizon"] = "positional"
        repairs.append(f"Inferred horizon='{data['horizon']}' from timeframe '{tf}'")

    # 5. strategy_type
    valid_types = ("trend_following", "swing_trading", "mean_reversion", "option_selling", "other")
    if "strategy_type" not in data or data["strategy_type"] not in valid_types:
        data["strategy_type"] = "trend_following"
        repairs.append("Defaulted strategy_type to 'trend_following'")

    # 6. kind
    valid_kinds = ("stock", "option", "investing", "composite")
    if "kind" not in data or data["kind"] not in valid_kinds:
        data["kind"] = "stock"
        repairs.append("Defaulted kind to 'stock'")

    # 7. universe
    if "universe" not in data or not isinstance(data["universe"], dict):
        if isinstance(data.get("universe"), str):
            sym = data["universe"]
            data["universe"] = {
                "type": "static",
                "instruments": [{"segment": "NSE_EQ", "security_id": sym, "symbol": sym}],
            }
            repairs.append(f"Normalized string universe '{sym}' to static instrument selector")
        elif isinstance(data.get("universe"), list):
            items = []
            for item in data["universe"]:
                if isinstance(item, str):
                    items.append({"segment": "NSE_EQ", "security_id": item, "symbol": item})
                elif isinstance(item, dict):
                    items.append(item)
            data["universe"] = {"type": "static", "instruments": items}
            repairs.append("Normalized list universe to static instrument selector")
        else:
            data["universe"] = {
                "type": "static",
                "instruments": [
                    {"segment": "NSE_EQ", "security_id": "RELIANCE", "symbol": "RELIANCE"}
                ],
            }
            repairs.append("Injected default RELIANCE universe")

    # 8. indicators
    if "indicators" not in data or not isinstance(data["indicators"], dict):
        data["indicators"] = {}
        repairs.append("Initialized empty indicators dictionary")
    else:
        for ind_name, ind_val in list(data["indicators"].items()):
            if isinstance(ind_val, dict):
                # Ensure params dict exists
                if "params" not in ind_val or not isinstance(ind_val["params"], dict):
                    ind_val["params"] = {}
                fn = ind_val.get("fn", "").upper()
                if fn in ("EMA", "SMA") and "period" not in ind_val["params"]:
                    ind_val["params"]["period"] = 20
                    repairs.append(f"Injected default period=20 for indicator '{ind_name}'")
                elif fn == "RSI" and "period" not in ind_val["params"]:
                    ind_val["params"]["period"] = 14
                    repairs.append(f"Injected default period=14 for RSI indicator '{ind_name}'")

    # 9. entries
    if "entries" not in data or not isinstance(data["entries"], list):
        data["entries"] = []
    else:
        for idx, entry in enumerate(data["entries"]):
            if isinstance(entry, dict):
                if "id" not in entry:
                    entry["id"] = f"entry_{idx + 1}"
                    repairs.append(f"Assigned ID '{entry['id']}' to entry rule {idx + 1}")
                if "side" not in entry or entry["side"] not in ("BUY", "SELL"):
                    entry["side"] = "BUY"
                    repairs.append(f"Defaulted side to 'BUY' for entry rule {entry['id']}")
                # Normalize compare operator in AST condition if present
                cond = entry.get("when")
                if isinstance(cond, dict):
                    op = cond.get("op")
                    op_map = {
                        "greater_than": ">",
                        "above": ">",
                        "gt": ">",
                        "less_than": "<",
                        "below": "<",
                        "lt": "<",
                        "equals": "==",
                        "eq": "==",
                    }
                    if op in op_map:
                        cond["op"] = op_map[op]
                        repairs.append(f"Normalized condition operator '{op}' to '{cond['op']}'")

    # 10. exits
    if "exits" not in data or not isinstance(data["exits"], list):
        data["exits"] = []
    else:
        repaired_exits = []
        for idx, ex in enumerate(data["exits"]):
            if isinstance(ex, dict):
                if "id" not in ex:
                    ex["id"] = f"exit_{idx + 1}"
                if "type" not in ex or ex["type"] not in (
                    "target",
                    "stop",
                    "time",
                    "signal",
                    "trailing_stop",
                ):
                    if "stop_loss_pct" in ex:
                        ex["type"] = "stop"
                        ex["pct"] = ex.pop("stop_loss_pct")
                    elif "target_pct" in ex:
                        ex["type"] = "target"
                        ex["pct"] = ex.pop("target_pct")
                    else:
                        ex["type"] = "stop"
                        ex["pct"] = 2.0
                    repairs.append(f"Repaired exit type to '{ex['type']}' for {ex['id']}")
                repaired_exits.append(ex)
        data["exits"] = repaired_exits

    # 11. sizing
    valid_sizing_types = (
        "fixed_qty",
        "fixed_value",
        "pct_capital",
        "risk_pct",
        "lots",
        "kelly_fraction",
    )
    if "sizing" not in data or not isinstance(data["sizing"], dict):
        data["sizing"] = {"type": "fixed_qty", "qty": 100}
        repairs.append("Assigned default sizing rule (fixed_qty=100)")
    else:
        stype = data["sizing"].get("type")
        if stype not in valid_sizing_types:
            if "fixed_capital" in str(stype):
                data["sizing"]["type"] = "fixed_value"
                data["sizing"]["value"] = data["sizing"].pop("capital", 100000.0)
            elif "pct_equity" in str(stype):
                data["sizing"]["type"] = "pct_capital"
            else:
                data["sizing"]["type"] = "fixed_qty"
                data["sizing"]["qty"] = 100
            repairs.append(f"Normalized sizing type to '{data['sizing']['type']}'")

    # 12. risk
    if "risk" not in data or not isinstance(data["risk"], dict):
        data["risk"] = {}

    # Validate against canonical StrategyIR
    try:
        StrategyIR.from_dict(data)
    except ValidationError as err:
        repairs.append(f"Validation notice: {err.errors()[0]['msg']}")

    return data, repairs
