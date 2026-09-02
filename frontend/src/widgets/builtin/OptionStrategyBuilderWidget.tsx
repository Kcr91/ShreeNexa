import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface OptionStrategyBuilderWidgetSettings {
  defaultUnderlying?: string;
  defaultStrategyTemplate?: string;
}

export interface OptionLegUI {
  legId: string;
  symbol: string;
  strike: number;
  optionType: "CALL" | "PUT";
  action: "BUY" | "SELL";
  quantity: number;
  lotSize: number;
  entryPrice: number;
  iv: number;
  expiryDate: string;
  isEnabled: boolean;
}

export const OptionStrategyBuilderWidget: React.FC<
  WidgetComponentProps<OptionStrategyBuilderWidgetSettings>
> = ({ settings }) => {
  const [underlying, setUnderlying] = useState<string>(
    settings.defaultUnderlying || "NIFTY"
  );
  const [targetDaysForward, setTargetDaysForward] = useState<number>(0);

  const spot = underlying === "NIFTY" ? 25000 : 52000;
  const step = underlying === "NIFTY" ? 50 : 100;
  const lotSize = underlying === "NIFTY" ? 25 : 15;
  const atmStrike = Math.round(spot / step) * step;

  const [legs, setLegs] = useState<OptionLegUI[]>([
    {
      legId: "leg-1",
      symbol: `${underlying}-${atmStrike - 2 * step}-PE`,
      strike: atmStrike - 2 * step,
      optionType: "PUT",
      action: "BUY",
      quantity: 1,
      lotSize,
      entryPrice: 15.0,
      iv: 0.14,
      expiryDate: "2026-09-17",
      isEnabled: true,
    },
    {
      legId: "leg-2",
      symbol: `${underlying}-${atmStrike - step}-PE`,
      strike: atmStrike - step,
      optionType: "PUT",
      action: "SELL",
      quantity: 1,
      lotSize,
      entryPrice: 35.0,
      iv: 0.14,
      expiryDate: "2026-09-17",
      isEnabled: true,
    },
    {
      legId: "leg-3",
      symbol: `${underlying}-${atmStrike + step}-CE`,
      strike: atmStrike + step,
      optionType: "CALL",
      action: "SELL",
      quantity: 1,
      lotSize,
      entryPrice: 35.0,
      iv: 0.14,
      expiryDate: "2026-09-17",
      isEnabled: true,
    },
    {
      legId: "leg-4",
      symbol: `${underlying}-${atmStrike + 2 * step}-CE`,
      strike: atmStrike + 2 * step,
      optionType: "CALL",
      action: "BUY",
      quantity: 1,
      lotSize,
      entryPrice: 15.0,
      iv: 0.14,
      expiryDate: "2026-09-17",
      isEnabled: true,
    },
  ]);

  const activeLegs = useMemo(() => legs.filter((l) => l.isEnabled), [legs]);

  // Compute Net Premium & Net Position Greeks
  const analytics = useMemo(() => {
    let netPremium = 0;
    let netDelta = 0;
    let netGamma = 0;
    let netTheta = 0;
    let netVega = 0;

    for (const leg of activeLegs) {
      const mult = leg.action === "BUY" ? 1 : -1;
      const totalUnits = leg.quantity * leg.lotSize;
      netPremium += mult * leg.entryPrice * totalUnits;

      // Approximate Greeks
      const moneyness = leg.strike / spot;
      const deltaApprox =
        leg.optionType === "CALL"
          ? Math.max(0.01, Math.min(0.99, 0.5 - (moneyness - 1.0) * 4))
          : Math.max(-0.99, Math.min(-0.01, -0.5 - (moneyness - 1.0) * 4));

      netDelta += mult * totalUnits * deltaApprox;
      netGamma += mult * totalUnits * 0.0003;
      netTheta += mult * totalUnits * (leg.action === "SELL" ? 18.5 : -18.5);
      netVega += mult * totalUnits * (leg.action === "BUY" ? 42.0 : -42.0);
    }

    // Generate payoff points
    const minPrice = spot * 0.95;
    const maxPrice = spot * 1.05;
    const numPts = 31;
    const priceStep = (maxPrice - minPrice) / (numPts - 1);
    const payoffCurve: Array<{ price: number; expiryPnl: number; targetPnl: number }> = [];

    for (let i = 0; i < numPts; i++) {
      const p = Math.round(minPrice + i * priceStep);
      let expiryPnl = 0;
      for (const leg of activeLegs) {
        const mult = leg.action === "BUY" ? 1 : -1;
        const totalUnits = leg.quantity * leg.lotSize;
        const intrinsic =
          leg.optionType === "CALL" ? Math.max(0, p - leg.strike) : Math.max(0, leg.strike - p);
        expiryPnl += mult * (intrinsic - leg.entryPrice) * totalUnits;
      }
      payoffCurve.push({
        price: p,
        expiryPnl,
        targetPnl: expiryPnl * 0.85,
      });
    }

    // Find Breakevens
    const breakevens: number[] = [];
    for (let i = 0; i < payoffCurve.length - 1; i++) {
      const p1 = payoffCurve[i];
      const p2 = payoffCurve[i + 1];
      if ((p1.expiryPnl < 0 && p2.expiryPnl > 0) || (p1.expiryPnl > 0 && p2.expiryPnl < 0)) {
        const root = p1.price + (0 - p1.expiryPnl) * (p2.price - p1.price) / (p2.expiryPnl - p1.expiryPnl);
        breakevens.push(Math.round(root));
      }
    }

    const pnls = payoffCurve.map((pt) => pt.expiryPnl);
    const maxProfit = Math.max(...pnls);
    const maxLoss = Math.min(...pnls);

    return {
      netPremium,
      netDelta,
      netGamma,
      netTheta,
      netVega,
      maxProfit,
      maxLoss,
      breakevens,
      payoffCurve,
    };
  }, [activeLegs, spot]);

  const handleApplyTemplate = (type: string) => {
    if (type === "BULL_CALL_SPREAD") {
      setLegs([
        {
          legId: "leg-1",
          symbol: `${underlying}-${atmStrike}-CE`,
          strike: atmStrike,
          optionType: "CALL",
          action: "BUY",
          quantity: 1,
          lotSize,
          entryPrice: 150.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
        {
          legId: "leg-2",
          symbol: `${underlying}-${atmStrike + step}-CE`,
          strike: atmStrike + step,
          optionType: "CALL",
          action: "SELL",
          quantity: 1,
          lotSize,
          entryPrice: 90.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
      ]);
    } else if (type === "STRADDLE") {
      setLegs([
        {
          legId: "leg-1",
          symbol: `${underlying}-${atmStrike}-CE`,
          strike: atmStrike,
          optionType: "CALL",
          action: "BUY",
          quantity: 1,
          lotSize,
          entryPrice: 150.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
        {
          legId: "leg-2",
          symbol: `${underlying}-${atmStrike}-PE`,
          strike: atmStrike,
          optionType: "PUT",
          action: "BUY",
          quantity: 1,
          lotSize,
          entryPrice: 145.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
      ]);
    } else if (type === "IRON_CONDOR") {
      setLegs([
        {
          legId: "leg-1",
          symbol: `${underlying}-${atmStrike - 2 * step}-PE`,
          strike: atmStrike - 2 * step,
          optionType: "PUT",
          action: "BUY",
          quantity: 1,
          lotSize,
          entryPrice: 15.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
        {
          legId: "leg-2",
          symbol: `${underlying}-${atmStrike - step}-PE`,
          strike: atmStrike - step,
          optionType: "PUT",
          action: "SELL",
          quantity: 1,
          lotSize,
          entryPrice: 35.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
        {
          legId: "leg-3",
          symbol: `${underlying}-${atmStrike + step}-CE`,
          strike: atmStrike + step,
          optionType: "CALL",
          action: "SELL",
          quantity: 1,
          lotSize,
          entryPrice: 35.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
        {
          legId: "leg-4",
          symbol: `${underlying}-${atmStrike + 2 * step}-CE`,
          strike: atmStrike + 2 * step,
          optionType: "CALL",
          action: "BUY",
          quantity: 1,
          lotSize,
          entryPrice: 15.0,
          iv: 0.14,
          expiryDate: "2026-09-17",
          isEnabled: true,
        },
      ]);
    }
  };

  const handleToggleLeg = (index: number) => {
    setLegs((prev) =>
      prev.map((l, idx) => (idx === index ? { ...l, isEnabled: !l.isEnabled } : l))
    );
  };

  const handleDeleteLeg = (index: number) => {
    setLegs((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleAddLeg = () => {
    const newLeg: OptionLegUI = {
      legId: `leg-${Date.now()}`,
      symbol: `${underlying}-${atmStrike}-CE`,
      strike: atmStrike,
      optionType: "CALL",
      action: "BUY",
      quantity: 1,
      lotSize,
      entryPrice: 100.0,
      iv: 0.14,
      expiryDate: "2026-09-17",
      isEnabled: true,
    };
    setLegs((prev) => [...prev, newLeg]);
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        padding: "var(--spacing-2)",
        gap: "var(--spacing-2)",
        backgroundColor: "#0b0f19",
        color: "#e2e8f0",
        fontSize: "12px",
      }}
    >
      {/* Top Header Controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "#1e293b",
          padding: "6px 10px",
          borderRadius: "6px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div>
            <span style={{ color: "#94a3b8" }}>Underlying: </span>
            <select
              value={underlying}
              onChange={(e) => setUnderlying(e.target.value)}
              aria-label="Select Strategy Underlying"
              style={{
                backgroundColor: "#0f172a",
                color: "#f8fafc",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "2px 6px",
              }}
            >
              <option value="NIFTY">NIFTY (₹25,000)</option>
              <option value="BANKNIFTY">BANKNIFTY (₹52,000)</option>
            </select>
          </div>

          <div>
            <span style={{ color: "#94a3b8" }}>Template: </span>
            <select
              defaultValue="IRON_CONDOR"
              onChange={(e) => handleApplyTemplate(e.target.value)}
              aria-label="Select Strategy Template"
              style={{
                backgroundColor: "#0f172a",
                color: "#f8fafc",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "2px 6px",
              }}
            >
              <option value="IRON_CONDOR">Iron Condor</option>
              <option value="BULL_CALL_SPREAD">Bull Call Spread</option>
              <option value="STRADDLE">Long Straddle</option>
            </select>
          </div>
        </div>

        {/* T+n slider */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "#94a3b8" }}>Target Date (T+{targetDaysForward}d):</span>
          <input
            type="range"
            min={0}
            max={7}
            value={targetDaysForward}
            onChange={(e) => setTargetDaysForward(Number(e.target.value))}
            aria-label="Target Days Forward"
            style={{ width: "80px" }}
          />
        </div>
      </div>

      {/* KPI & Greek Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "6px" }}>
        <div style={{ backgroundColor: "#1e293b", padding: "6px 8px", borderRadius: "4px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8" }}>NET PREMIUM</div>
          <div
            style={{
              fontSize: "14px",
              fontWeight: 700,
              color: analytics.netPremium <= 0 ? "#34d399" : "#f87171",
            }}
          >
            {analytics.netPremium <= 0
              ? `Credit ₹${Math.abs(analytics.netPremium).toFixed(0)}`
              : `Debit ₹${analytics.netPremium.toFixed(0)}`}
          </div>
        </div>

        <div style={{ backgroundColor: "#1e293b", padding: "6px 8px", borderRadius: "4px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8" }}>MAX PROFIT</div>
          <div style={{ fontSize: "14px", fontWeight: 700, color: "#34d399" }}>
            ₹{analytics.maxProfit.toFixed(0)}
          </div>
        </div>

        <div style={{ backgroundColor: "#1e293b", padding: "6px 8px", borderRadius: "4px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8" }}>MAX LOSS</div>
          <div style={{ fontSize: "14px", fontWeight: 700, color: "#f87171" }}>
            ₹{analytics.maxLoss.toFixed(0)}
          </div>
        </div>

        <div style={{ backgroundColor: "#1e293b", padding: "6px 8px", borderRadius: "4px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8" }}>BREAKEVENS</div>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "#f59e0b" }}>
            {analytics.breakevens.length > 0 ? analytics.breakevens.join(", ") : "None"}
          </div>
        </div>

        <div style={{ backgroundColor: "#1e293b", padding: "6px 8px", borderRadius: "4px" }}>
          <div style={{ fontSize: "10px", color: "#94a3b8" }}>NET GREEKS</div>
          <div style={{ fontSize: "11px", color: "#e2e8f0" }}>
            Δ: {analytics.netDelta.toFixed(1)} | θ: ₹{analytics.netTheta.toFixed(0)}/d
          </div>
        </div>
      </div>

      {/* Legs Editor Table */}
      <div style={{ flex: 1, overflowY: "auto", border: "1px solid #1e293b", borderRadius: "6px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
          <thead>
            <tr style={{ backgroundColor: "#1e293b", color: "#94a3b8", textAlign: "left" }}>
              <th style={{ padding: "4px 8px" }}>Active</th>
              <th style={{ padding: "4px 8px" }}>Action</th>
              <th style={{ padding: "4px 8px" }}>Strike</th>
              <th style={{ padding: "4px 8px" }}>Type</th>
              <th style={{ padding: "4px 8px" }}>Lots</th>
              <th style={{ padding: "4px 8px" }}>Premium (₹)</th>
              <th style={{ padding: "4px 8px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {legs.map((leg, idx) => (
              <tr
                key={leg.legId}
                style={{
                  borderBottom: "1px solid #1e293b",
                  opacity: leg.isEnabled ? 1.0 : 0.4,
                  backgroundColor: idx % 2 === 0 ? "rgba(30, 41, 59, 0.4)" : "transparent",
                }}
              >
                <td style={{ padding: "4px 8px" }}>
                  <input
                    type="checkbox"
                    checked={leg.isEnabled}
                    onChange={() => handleToggleLeg(idx)}
                    aria-label={`Toggle leg ${leg.strike} ${leg.optionType}`}
                  />
                </td>
                <td style={{ padding: "4px 8px", fontWeight: 700, color: leg.action === "BUY" ? "#38bdf8" : "#f87171" }}>
                  {leg.action}
                </td>
                <td style={{ padding: "4px 8px", fontWeight: 600 }}>{leg.strike}</td>
                <td style={{ padding: "4px 8px", color: leg.optionType === "CALL" ? "#34d399" : "#fbbf24" }}>
                  {leg.optionType}
                </td>
                <td style={{ padding: "4px 8px" }}>{leg.quantity}</td>
                <td style={{ padding: "4px 8px" }}>₹{leg.entryPrice.toFixed(2)}</td>
                <td style={{ padding: "4px 8px" }}>
                  <button
                    onClick={() => handleDeleteLeg(idx)}
                    style={{
                      backgroundColor: "transparent",
                      border: "none",
                      color: "#f87171",
                      cursor: "pointer",
                      fontSize: "12px",
                    }}
                    aria-label={`Delete leg ${leg.strike}`}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Leg Button */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button
          onClick={handleAddLeg}
          style={{
            padding: "4px 12px",
            backgroundColor: "#2563eb",
            color: "#ffffff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          + Add Option Leg
        </button>

        <div style={{ fontSize: "11px", color: "#64748b" }}>
          Indian lot size: {lotSize} contracts per lot
        </div>
      </div>
    </div>
  );
};

export const optionStrategyBuilderDefinition: WidgetDefinition<OptionStrategyBuilderWidgetSettings> = {
  id: "option-strategy-builder",
  title: "Multi-Leg Option Strategy Builder",
  description: "Interactive multi-leg option payoff builder, breakevens, extrema, and net Greeks.",
  category: "analytics",
  icon: "🧩",
  defaultWidth: 600,
  defaultHeight: 450,
  schema: {
    fields: [
      {
        name: "defaultUnderlying",
        label: "Underlying Index",
        type: "select",
        default: "NIFTY",
        options: [
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
    ],
  },
  component: OptionStrategyBuilderWidget,
};
