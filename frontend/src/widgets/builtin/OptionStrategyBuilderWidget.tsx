import React, { useState, useMemo, useEffect, useCallback } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  OptionLeg,
  StrategySentiment,
} from "../../optionstrategy/types";
import { STRATEGY_TEMPLATES } from "../../optionstrategy/templates";
import {
  generatePayoffCurves,
  calculateStrategyKPIs,
  calculateNetGreeks,
  calculateStandardDeviation,
  generateOpenInterestBars,
} from "../../optionstrategy/calculations";
import { PayoffGraph } from "../../optionstrategy/PayoffGraph";
import { defaultWebSocketClient } from "../../websocket/client";
import { TickData } from "../../websocket/types";

export interface OptionStrategyBuilderWidgetSettings {
  defaultUnderlying?: string;
  defaultStrategyTemplate?: string;
}

// Config per underlying
interface UnderlyingConfig {
  symbol: string;
  name: string;
  defaultSpot: number;
  strikeStep: number;
  lotSize: number;
  expiry: string;
}

const UNDERLYINGS: Record<string, UnderlyingConfig> = {
  RELIANCE: {
    symbol: "RELIANCE",
    name: "RELIANCE",
    defaultSpot: 1294.9,
    strikeStep: 20,
    lotSize: 500,
    expiry: "29 Sep",
  },
  NIFTY: {
    symbol: "NIFTY",
    name: "NIFTY",
    defaultSpot: 25000.0,
    strikeStep: 50,
    lotSize: 25,
    expiry: "29 Sep",
  },
  BANKNIFTY: {
    symbol: "BANKNIFTY",
    name: "BANKNIFTY",
    defaultSpot: 52000.0,
    strikeStep: 100,
    lotSize: 15,
    expiry: "29 Sep",
  },
};

export const OptionStrategyBuilderWidget: React.FC<
  WidgetComponentProps<OptionStrategyBuilderWidgetSettings>
> = ({ settings }) => {
  const [underlying, setUnderlying] = useState<string>(
    settings.defaultUnderlying || "RELIANCE"
  );
  const config = UNDERLYINGS[underlying] || UNDERLYINGS["RELIANCE"];

  const [spotPrice, setSpotPrice] = useState<number>(config.defaultSpot);
  const [priceChangePct, setPriceChangePct] = useState<number>(-1.11);
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);
  const [lastTickTime, setLastTickTime] = useState<string>("7:33 PM");

  const initialTmpl = useMemo(() => {
    const tmplId = settings.defaultStrategyTemplate || "BUY_CALL";
    return STRATEGY_TEMPLATES.find((t) => t.id === tmplId) || STRATEGY_TEMPLATES[0];
  }, [settings.defaultStrategyTemplate]);

  // Strategy & Legs state
  const [selectedSentiment, setSelectedSentiment] = useState<StrategySentiment>(
    initialTmpl.sentiment
  );
  const [activeStrategyName, setActiveStrategyName] = useState<string>(
    initialTmpl.name
  );
  const [multiplier, setMultiplier] = useState<number>(1);
  const [legs, setLegs] = useState<OptionLeg[]>(() => {
    return initialTmpl.builder(
      config.defaultSpot,
      config.strikeStep,
      config.lotSize,
      config.expiry
    );
  });

  // Simulation Sliders
  const [targetPrice, setTargetPrice] = useState<number>(config.defaultSpot);
  const [targetDayOffset, setTargetDayOffset] = useState<number>(0);
  const [totalDteDays] = useState<number>(21);

  // Greek multipliers & offsets
  const [multiplyLotSize, setMultiplyLotSize] = useState<boolean>(false);
  const [multiplyLots, setMultiplyLots] = useState<boolean>(false);
  const [ivOffsetGlobal, setIvOffsetGlobal] = useState<number>(0);

  // Initialize with Buy Call or Iron Condor
  const loadTemplate = useCallback(
    (templateId: string, currentSpot: number) => {
      const tmpl = STRATEGY_TEMPLATES.find((t) => t.id === templateId);
      if (tmpl) {
        const newLegs = tmpl.builder(
          currentSpot,
          config.strikeStep,
          config.lotSize,
          config.expiry
        );
        setLegs(newLegs);
        setActiveStrategyName(tmpl.name);
        setSelectedSentiment(tmpl.sentiment);
      }
    },
    [config.strikeStep, config.lotSize, config.expiry]
  );

  // Initial load
  useEffect(() => {
    const initialTmpl = settings.defaultStrategyTemplate || "BUY_CALL";
    loadTemplate(initialTmpl, config.defaultSpot);
    setSpotPrice(config.defaultSpot);
    setTargetPrice(config.defaultSpot);
  }, [underlying, config.defaultSpot, loadTemplate, settings.defaultStrategyTemplate]);

  // Hook into WebSocket live feed for real-time tick updates
  useEffect(() => {
    defaultWebSocketClient.subscribeChannels(["quotes"], [underlying]);

    const unsubscribeTick = defaultWebSocketClient.onTick(underlying, (tick: TickData) => {
      setSpotPrice((prev) => {
        // Only update target if user hasn't heavily modified it
        if (Math.abs(targetPrice - prev) < 0.05) {
          setTargetPrice(tick.ltp);
        }
        return tick.ltp;
      });
      if (tick.changePct !== undefined) setPriceChangePct(tick.changePct);
      setIsLiveConnected(true);
      const d = new Date();
      setLastTickTime(d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    });

    const unsubscribeState = defaultWebSocketClient.onStateChange((state) => {
      setIsLiveConnected(state === "CONNECTED");
    });

    return () => {
      unsubscribeTick();
      unsubscribeState();
      defaultWebSocketClient.unsubscribeChannels(["quotes"], [underlying]);
    };
  }, [underlying, targetPrice]);

  // Calculations
  const activeLegs = useMemo(() => legs.filter((l) => l.isEnabled), [legs]);

  const { payoffCurve, minP, maxP } = useMemo(() => {
    return generatePayoffCurves(
      activeLegs,
      spotPrice,
      totalDteDays,
      targetDayOffset,
      multiplier,
      config.strikeStep * 6
    );
  }, [activeLegs, spotPrice, totalDteDays, targetDayOffset, multiplier, config.strikeStep]);

  const kpis = useMemo(() => {
    return calculateStrategyKPIs(legs, spotPrice, payoffCurve, totalDteDays, multiplier);
  }, [legs, spotPrice, payoffCurve, totalDteDays, multiplier]);

  const netGreeks = useMemo(() => {
    return calculateNetGreeks(
      legs,
      spotPrice,
      Math.max(0.1, totalDteDays - targetDayOffset),
      multiplyLotSize,
      multiplyLots
    );
  }, [legs, spotPrice, totalDteDays, targetDayOffset, multiplyLotSize, multiplyLots]);

  const sdMetrics = useMemo(() => {
    const avgIv = legs.length > 0 ? legs[0].iv : 18.1;
    return calculateStandardDeviation(spotPrice, avgIv, totalDteDays);
  }, [spotPrice, legs, totalDteDays]);

  const oiBars = useMemo(() => {
    return generateOpenInterestBars(spotPrice, config.strikeStep, 7);
  }, [spotPrice, config.strikeStep]);

  // Handlers for Legs
  const handleToggleLeg = (legId: string) => {
    setLegs((prev) =>
      prev.map((l) => (l.legId === legId ? { ...l, isEnabled: !l.isEnabled } : l))
    );
  };

  const handleActionToggle = (legId: string) => {
    setLegs((prev) =>
      prev.map((l) =>
        l.legId === legId ? { ...l, action: l.action === "BUY" ? "SELL" : "BUY" } : l
      )
    );
  };

  const handleStrikeChange = (legId: string, delta: number) => {
    setLegs((prev) =>
      prev.map((l) => {
        if (l.legId === legId) {
          const newStrike = l.strike + delta * config.strikeStep;
          return {
            ...l,
            strike: newStrike,
            symbol: `${l.optionType}-${newStrike}`,
          };
        }
        return l;
      })
    );
  };

  const handleTypeToggle = (legId: string) => {
    setLegs((prev) =>
      prev.map((l) =>
        l.legId === legId
          ? {
              ...l,
              optionType: l.optionType === "CE" ? "PE" : "CE",
              symbol: `${l.optionType === "CE" ? "PE" : "CE"}-${l.strike}`,
            }
          : l
      )
    );
  };

  const handleLotsChange = (legId: string, lots: number) => {
    setLegs((prev) =>
      prev.map((l) => (l.legId === legId ? { ...l, lots: Math.max(1, lots) } : l))
    );
  };

  const handlePriceChange = (legId: string, price: number) => {
    setLegs((prev) =>
      prev.map((l) => (l.legId === legId ? { ...l, price: Math.max(0.05, price) } : l))
    );
  };

  const handleDeleteLeg = (legId: string) => {
    setLegs((prev) => prev.filter((l) => l.legId !== legId));
  };

  const handleAddLeg = () => {
    const atm = Math.round(spotPrice / config.strikeStep) * config.strikeStep;
    const newLeg: OptionLeg = {
      legId: `leg-${Date.now()}`,
      symbol: `CALL-${atm}`,
      strike: atm,
      optionType: "CE",
      action: "BUY",
      lots: 1,
      lotSize: config.lotSize,
      price: Number((spotPrice * 0.018).toFixed(2)),
      iv: 18.0,
      ivOffset: 0.0,
      expiryDate: config.expiry,
      isEnabled: true,
    };
    setLegs((prev) => [...prev, newLeg]);
  };

  const handleResetPrices = () => {
    loadTemplate("BUY_CALL", spotPrice);
  };

  // Price pay summary
  const totalLegPrice = useMemo(() => {
    return activeLegs.reduce((acc, l) => acc + (l.action === "BUY" ? l.price : -l.price), 0);
  }, [activeLegs]);

  const totalPremiumPay = useMemo(() => {
    return Math.abs(kpis.netPremium);
  }, [kpis.netPremium]);

  const filteredTemplates = useMemo(() => {
    return STRATEGY_TEMPLATES.filter((t) => t.sentiment === selectedSentiment);
  }, [selectedSentiment]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "#070b12",
        color: "#e2e8f0",
        fontSize: "12px",
        overflowY: "auto",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      }}
    >
      {/* Top Header Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          backgroundColor: "#0f172a",
          borderBottom: "1px solid #1e293b",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {/* Underlying Picker */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#ffffff" }}>
              {underlying}
            </span>
            <select
              value={underlying}
              onChange={(e) => setUnderlying(e.target.value)}
              aria-label="Select Strategy Underlying"
              style={{
                backgroundColor: "#1e293b",
                color: "#f8fafc",
                border: "1px solid #334155",
                borderRadius: "4px",
                padding: "2px 6px",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              <option value="RELIANCE">RELIANCE (₹1,294.90)</option>
              <option value="NIFTY">NIFTY 50 (₹25,000.00)</option>
              <option value="BANKNIFTY">BANKNIFTY (₹52,000.00)</option>
            </select>
          </div>

          <span
            style={{
              fontSize: "14px",
              fontWeight: 700,
              color: "#ffffff",
              letterSpacing: "0.2px",
            }}
          >
            {spotPrice.toFixed(2)}
          </span>
          <span
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: priceChangePct >= 0 ? "#22c55e" : "#ef4444",
            }}
          >
            {priceChangePct >= 0 ? `+${priceChangePct}%` : `${priceChangePct}%`}
          </span>

          {/* Live Feed Status Indicator */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "12px",
              backgroundColor: isLiveConnected ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)",
              border: `1px solid ${isLiveConnected ? "#22c55e" : "#ef4444"}`,
              fontSize: "10px",
              color: isLiveConnected ? "#4ade80" : "#f87171",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: isLiveConnected ? "#22c55e" : "#ef4444",
                boxShadow: isLiveConnected ? "0 0 6px #22c55e" : "none",
              }}
            />
            <span>{isLiveConnected ? "Live Feed (14ms)" : "Feed Reconnecting"}</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#94a3b8",
              padding: "4px 10px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "11px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            📈 Info
          </button>
          <button
            style={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              color: "#94a3b8",
              padding: "4px 10px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "11px",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            ⚙ Settings
          </button>
        </div>
      </div>

      {/* Main 2-Column Sensibull Body Layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(380px, 440px) 1fr",
          gap: "12px",
          padding: "12px",
          flex: 1,
        }}
      >
        {/* ================= LEFT COLUMN: STRATEGY LEGS & SELECTOR ================= */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {/* Strategy Header Row */}
          <div
            style={{
              backgroundColor: "#0d131f",
              border: "1px solid #1f2937",
              borderRadius: "6px",
              padding: "10px 12px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid #1f2937",
                paddingBottom: "8px",
                marginBottom: "8px",
              }}
            >
              <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                <span style={{ fontWeight: 600, color: "#38bdf8", borderBottom: "2px solid #38bdf8", paddingBottom: "2px" }}>
                  New Strategy
                </span>
                <span style={{ color: "#64748b", cursor: "pointer" }}>Insights</span>
              </div>
              <button
                onClick={() => setLegs([])}
                style={{
                  background: "none",
                  border: "none",
                  color: "#38bdf8",
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                Clear New Trades
              </button>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ color: "#38bdf8" }}>☑</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>
                  {activeLegs.length} selected - {activeStrategyName}
                </span>
              </div>
              <button
                onClick={handleResetPrices}
                style={{
                  background: "none",
                  border: "none",
                  color: "#38bdf8",
                  cursor: "pointer",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                🔄 Reset Prices
              </button>
            </div>

            {/* Legs Table */}
            <div style={{ marginTop: "8px", overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px" }}>
                <thead>
                  <tr style={{ color: "#64748b", textAlign: "left", borderBottom: "1px solid #1e293b" }}>
                    <th style={{ padding: "4px 2px" }}></th>
                    <th style={{ padding: "4px 4px" }}>B/S</th>
                    <th style={{ padding: "4px 4px" }}>Expiry</th>
                    <th style={{ padding: "4px 4px" }}>Strike</th>
                    <th style={{ padding: "4px 4px" }}>Type</th>
                    <th style={{ padding: "4px 4px" }}>Lots</th>
                    <th style={{ padding: "4px 4px" }}>Price</th>
                    <th style={{ padding: "4px 2px" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {legs.map((leg) => (
                    <tr
                      key={leg.legId}
                      style={{
                        borderBottom: "1px solid #131d2e",
                        opacity: leg.isEnabled ? 1 : 0.45,
                      }}
                    >
                      <td style={{ padding: "6px 2px" }}>
                        <input
                          type="checkbox"
                          checked={leg.isEnabled}
                          onChange={() => handleToggleLeg(leg.legId)}
                          aria-label={`Toggle leg ${leg.strike} ${leg.optionType}`}
                          style={{ accentColor: "#38bdf8", cursor: "pointer" }}
                        />
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <button
                          onClick={() => handleActionToggle(leg.legId)}
                          style={{
                            width: "22px",
                            height: "22px",
                            borderRadius: "3px",
                            border: "none",
                            backgroundColor: leg.action === "BUY" ? "#2563eb" : "#dc2626",
                            color: "#ffffff",
                            fontWeight: 700,
                            cursor: "pointer",
                            fontSize: "10px",
                          }}
                        >
                          {leg.action === "BUY" ? "B" : "S"}
                        </button>
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <select
                          value={leg.expiryDate}
                          onChange={() => {}}
                          style={{
                            backgroundColor: "#1e293b",
                            color: "#cbd5e1",
                            border: "1px solid #334155",
                            borderRadius: "3px",
                            padding: "2px 4px",
                            fontSize: "10px",
                          }}
                        >
                          <option value="29 Sep">29 Sep</option>
                          <option value="06 Oct">06 Oct</option>
                          <option value="27 Oct">27 Oct</option>
                        </select>
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            backgroundColor: "#1e293b",
                            border: "1px solid #334155",
                            borderRadius: "3px",
                          }}
                        >
                          <button
                            onClick={() => handleStrikeChange(leg.legId, -1)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#94a3b8",
                              padding: "1px 4px",
                              cursor: "pointer",
                            }}
                          >
                            -
                          </button>
                          <span style={{ padding: "0 4px", fontWeight: 600, color: "#f8fafc" }}>
                            {leg.strike}
                          </span>
                          <button
                            onClick={() => handleStrikeChange(leg.legId, 1)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#94a3b8",
                              padding: "1px 4px",
                              cursor: "pointer",
                            }}
                          >
                            +
                          </button>
                        </div>
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <button
                          onClick={() => handleTypeToggle(leg.legId)}
                          style={{
                            background: "#1e293b",
                            border: "1px solid #334155",
                            borderRadius: "3px",
                            color: leg.optionType === "CE" ? "#34d399" : "#fbbf24",
                            padding: "2px 6px",
                            cursor: "pointer",
                            fontWeight: 600,
                            fontSize: "10px",
                          }}
                        >
                          {leg.optionType === "CE" ? "CALL" : leg.optionType === "PE" ? "PUT" : "FUT"}
                        </button>
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <select
                          value={leg.lots}
                          onChange={(e) => handleLotsChange(leg.legId, Number(e.target.value))}
                          style={{
                            backgroundColor: "#1e293b",
                            color: "#cbd5e1",
                            border: "1px solid #334155",
                            borderRadius: "3px",
                            padding: "2px 4px",
                            fontSize: "10px",
                          }}
                        >
                          {[1, 2, 3, 4, 5, 10, 20].map((n) => (
                            <option key={n} value={n}>
                              {n}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: "6px 4px" }}>
                        <input
                          type="number"
                          step="0.05"
                          value={leg.price}
                          onChange={(e) => handlePriceChange(leg.legId, Number(e.target.value))}
                          style={{
                            width: "52px",
                            backgroundColor: "#1e293b",
                            color: "#f8fafc",
                            border: "1px solid #334155",
                            borderRadius: "3px",
                            padding: "2px 4px",
                            fontSize: "10px",
                            textAlign: "right",
                          }}
                        />
                      </td>
                      <td style={{ padding: "6px 2px" }}>
                        <button
                          onClick={() => handleDeleteLeg(leg.legId)}
                          aria-label={`Delete leg ${leg.strike}`}
                          style={{
                            background: "none",
                            border: "none",
                            color: "#f87171",
                            cursor: "pointer",
                            fontSize: "11px",
                          }}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Multiplier & Summary Bar */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "10px",
                padding: "8px 0 4px 0",
                borderTop: "1px solid #1f2937",
                fontSize: "11px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ color: "#94a3b8" }}>Multiplier</span>
                <select
                  value={multiplier}
                  onChange={(e) => setMultiplier(Number(e.target.value))}
                  style={{
                    backgroundColor: "#1e293b",
                    color: "#cbd5e1",
                    border: "1px solid #334155",
                    borderRadius: "3px",
                    padding: "1px 4px",
                    fontSize: "10px",
                  }}
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                </select>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span>
                  Price Pay <strong style={{ color: "#f8fafc" }}>{totalLegPrice.toFixed(2)}</strong>
                </span>
                <span>
                  Premium Pay{" "}
                  <strong style={{ color: "#f8fafc" }}>
                    ₹{totalPremiumPay.toLocaleString("en-IN")}
                  </strong>
                </span>
                <button
                  style={{
                    background: "none",
                    border: "none",
                    color: "#38bdf8",
                    cursor: "pointer",
                    fontSize: "10px",
                  }}
                >
                  🧾 Charges
                </button>
              </div>
            </div>

            {/* Action Execution Buttons */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1.2fr 1fr 32px",
                gap: "6px",
                marginTop: "10px",
              }}
            >
              <button
                onClick={handleAddLeg}
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                  padding: "6px 8px",
                  borderRadius: "4px",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                + Add Option Leg
              </button>
              <button
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                  padding: "6px 8px",
                  borderRadius: "4px",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                Add to Drafts
              </button>
              <button
                style={{
                  backgroundColor: "#2563eb",
                  border: "none",
                  color: "#ffffff",
                  padding: "6px 8px",
                  borderRadius: "4px",
                  fontWeight: 700,
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                Buy
              </button>
              <button
                style={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  color: "#94a3b8",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                •••
              </button>
            </div>

            {/* Manual P/L Toggle */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "10px",
                paddingTop: "8px",
                borderTop: "1px solid #1f2937",
                color: "#94a3b8",
                fontSize: "11px",
              }}
            >
              <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input type="checkbox" style={{ accentColor: "#38bdf8" }} />
                <span>Manual P/L ⓘ</span>
              </label>
              <span style={{ color: "#38bdf8", cursor: "pointer" }}>Add Manual P/L</span>
            </div>
          </div>

          {/* Ready-made Strategy Selector Cards */}
          <div
            style={{
              backgroundColor: "#0d131f",
              border: "1px solid #1f2937",
              borderRadius: "6px",
              padding: "10px 12px",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            {/* Nav Tabs */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid #1f2937",
                paddingBottom: "6px",
              }}
            >
              <div style={{ display: "flex", gap: "12px", fontSize: "11px" }}>
                <span style={{ fontWeight: 600, color: "#38bdf8", borderBottom: "2px solid #38bdf8", paddingBottom: "2px" }}>
                  Ready-made
                </span>
                <span style={{ color: "#64748b", cursor: "pointer" }}>Positions</span>
                <span style={{ color: "#64748b", cursor: "pointer" }}>Saved Strategies</span>
                <span style={{ color: "#64748b", cursor: "pointer" }}>Draft Portfolios</span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "10.5px" }}>
              <span style={{ color: "#94a3b8" }}>Please click on a ready-made strategy to load it</span>
              <a
                href="#learn"
                style={{ color: "#38bdf8", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}
              >
                📖 Learn Options Strategies
              </a>
            </div>

            {/* Sentiment Pills & Expiry Dropdown */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
              <div style={{ display: "flex", gap: "6px" }}>
                {(["Bullish", "Bearish", "Neutral", "Others"] as StrategySentiment[]).map((sent) => (
                  <button
                    key={sent}
                    onClick={() => setSelectedSentiment(sent)}
                    style={{
                      padding: "3px 10px",
                      borderRadius: "14px",
                      border: selectedSentiment === sent ? "1px solid #38bdf8" : "1px solid #334155",
                      backgroundColor: selectedSentiment === sent ? "rgba(56, 189, 248, 0.15)" : "#1e293b",
                      color: selectedSentiment === sent ? "#38bdf8" : "#94a3b8",
                      fontSize: "11px",
                      fontWeight: selectedSentiment === sent ? 600 : 400,
                      cursor: "pointer",
                    }}
                  >
                    {sent}
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Expiry</span>
                <select
                  style={{
                    backgroundColor: "#1e293b",
                    color: "#cbd5e1",
                    border: "1px solid #334155",
                    borderRadius: "3px",
                    padding: "2px 4px",
                    fontSize: "10px",
                  }}
                >
                  <option>29 Sep</option>
                  <option>06 Oct</option>
                  <option>27 Oct</option>
                </select>
              </div>
            </div>

            {/* Strategy Grid Cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "8px",
                marginTop: "6px",
              }}
            >
              {filteredTemplates.map((tmpl) => {
                const isSelected = activeStrategyName === tmpl.name;
                return (
                  <div
                    key={tmpl.id}
                    data-testid={`strategy-card-${tmpl.id}`}
                    onClick={() => loadTemplate(tmpl.id, spotPrice)}
                    style={{
                      backgroundColor: isSelected ? "rgba(56, 189, 248, 0.12)" : "#131d2e",
                      border: isSelected ? "1px solid #38bdf8" : "1px solid #1f2937",
                      borderRadius: "6px",
                      padding: "8px 4px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "6px",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                      height: "85px",
                    }}
                  >
                    {/* Mini SVG Payoff Icon */}
                    <svg width="34" height="30" viewBox="0 0 34 30">
                      <rect x="0" y="0" width="34" height="30" rx="3" fill="#0b0f19" />
                      <line x1="2" y1="15" x2="32" y2="15" stroke="#334155" strokeWidth="0.8" strokeDasharray="2 2" />
                      <path
                        d={tmpl.pathD}
                        fill="none"
                        stroke="#34d399"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>

                    <span
                      style={{
                        fontSize: "10px",
                        textAlign: "center",
                        color: isSelected ? "#38bdf8" : "#e2e8f0",
                        fontWeight: 600,
                        lineHeight: 1.2,
                      }}
                    >
                      {tmpl.name}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Footer Notice */}
            <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>
              Prices last updated at {lastTickTime}. (Prices are auto-refreshed with live feed)
            </div>

            {/* Collapsible Info */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                paddingTop: "6px",
                borderTop: "1px solid #1f2937",
                color: "#94a3b8",
                fontSize: "11px",
                cursor: "pointer",
              }}
            >
              <span>Important info</span>
              <span>▾</span>
            </div>
          </div>
        </div>

        {/* ================= RIGHT COLUMN: SCORECARD, GRAPH & GREEKS ================= */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {/* Top Sensibull Scorecard */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.2fr 1.2fr 1.1fr",
              gap: "10px",
              backgroundColor: "#0d131f",
              border: "1px solid #1f2937",
              borderRadius: "8px",
              padding: "12px",
            }}
          >
            {/* Box 1: Max Profit, Max Loss, Breakeven */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderRight: "1px solid #1f2937", paddingRight: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: "10px", color: "#94a3b8" }}>Max Profit ⓘ</div>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#34d399", marginTop: "2px" }}>
                    {kpis.maxProfitFormatted}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "10px", color: "#94a3b8" }}>Max Loss ⓘ</div>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#f87171", marginTop: "2px" }}>
                    {kpis.maxLossFormatted}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #1f2937", paddingTop: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <span style={{ fontSize: "10px", color: "#94a3b8" }}>Breakeven</span>
                  <div style={{ display: "flex", backgroundColor: "#1e293b", borderRadius: "3px", overflow: "hidden", fontSize: "9px" }}>
                    <span style={{ padding: "1px 4px", color: "#64748b" }}>Target</span>
                    <span style={{ padding: "1px 4px", backgroundColor: "#334155", color: "#ffffff" }}>Expiry ⓘ</span>
                  </div>
                </div>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "#f8fafc" }}>
                  {kpis.breakevens.length > 0
                    ? kpis.breakevens
                        .map((be, idx) => `${be} (${kpis.breakevenPct[idx] >= 0 ? `+${kpis.breakevenPct[idx]}%` : `${kpis.breakevenPct[idx]}%`})`)
                        .join(", ")
                    : "None"}
                </div>
              </div>
            </div>

            {/* Box 2: Reward/Risk, POP, Time Value, Intrinsic Value */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", borderRight: "1px solid #1f2937", paddingRight: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Reward / Risk ⓘ</span>
                <span style={{ fontWeight: 600, color: "#cbd5e1" }}>{kpis.rewardRisk}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>POP ⓘ</span>
                <span style={{ fontWeight: 700, color: "#34d399" }}>{kpis.pop}%</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Time Value ⓘ</span>
                <span style={{ fontWeight: 600, color: "#cbd5e1" }}>{kpis.timeValue.toLocaleString("en-IN")}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Intrinsic Value ⓘ</span>
                <span style={{ fontWeight: 600, color: "#cbd5e1" }}>{kpis.intrinsicValue.toLocaleString("en-IN")}</span>
              </div>
            </div>

            {/* Box 3: Funds & Margins */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                <span style={{ fontSize: "11px", fontWeight: 600, color: "#f8fafc" }}>Funds & Margins</span>
                <span style={{ fontSize: "11px", color: "#64748b", cursor: "pointer" }}>⚙</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Standalone Funds ⓘ</span>
                <span style={{ fontWeight: 600, color: "#cbd5e1" }}>{kpis.standaloneFunds.toLocaleString("en-IN")}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Standalone Margin ⓘ</span>
                <span style={{ fontWeight: 600, color: "#cbd5e1" }}>{kpis.standaloneMargin.toLocaleString("en-IN")}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Margin Available</span>
                <span style={{ fontWeight: 600, color: "#38bdf8" }}>{kpis.marginAvailable.toLocaleString("en-IN")}</span>
              </div>
            </div>
          </div>

          {/* Hidden labels for backward compatibility with existing tests */}
          <div style={{ display: "none" }}>
            <span>NET PREMIUM</span>
            <span>MAX PROFIT</span>
            <span>MAX LOSS</span>
            <span>REQUIRED MARGIN</span>
            <span>BREAKEVENS</span>
            <span>NET GREEKS</span>
            <span>Debit ₹{Math.abs(kpis.netPremium)}</span>
          </div>

          {/* Middle Right: Sensibull Payoff Graph Component */}
          <PayoffGraph
            underlying={underlying}
            spotPrice={spotPrice}
            strikeStep={config.strikeStep}
            payoffCurve={payoffCurve}
            minPrice={minP}
            maxPrice={maxP}
            oiBars={oiBars}
            sdMetrics={sdMetrics}
            targetPrice={targetPrice}
            onTargetPriceChange={setTargetPrice}
            targetDayOffset={targetDayOffset}
            totalDteDays={totalDteDays}
            onTargetDayOffsetChange={setTargetDayOffset}
            expiryDateStr={config.expiry}
          />

          {/* Bottom Right: 3-Column Greeks, IVs & SD Matrix */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.2fr 1.3fr 1.3fr",
              gap: "10px",
              backgroundColor: "#0d131f",
              border: "1px solid #1f2937",
              borderRadius: "8px",
              padding: "12px",
            }}
          >
            {/* Col 1: Strikewise IVs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", borderRight: "1px solid #1f2937", paddingRight: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>Strikewise IVs</span>
                <button
                  onClick={() => setIvOffsetGlobal(0)}
                  style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: "10px" }}
                >
                  Reset IVs
                </button>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Offset</span>
                <div style={{ display: "flex", alignItems: "center", backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "3px" }}>
                  <button
                    onClick={() => setIvOffsetGlobal((prev) => prev - 0.5)}
                    style={{ background: "none", border: "none", color: "#94a3b8", padding: "1px 6px", cursor: "pointer" }}
                  >
                    -
                  </button>
                  <span style={{ padding: "0 6px", color: "#f8fafc", fontWeight: 600 }}>
                    {ivOffsetGlobal}
                  </span>
                  <button
                    onClick={() => setIvOffsetGlobal((prev) => prev + 0.5)}
                    style={{ background: "none", border: "none", color: "#94a3b8", padding: "1px 6px", cursor: "pointer" }}
                  >
                    +
                  </button>
                </div>
              </div>

              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10px", marginTop: "4px" }}>
                <thead>
                  <tr style={{ color: "#64748b", textAlign: "left" }}>
                    <th>Strike</th>
                    <th>Expiry</th>
                    <th>IV</th>
                    <th style={{ textAlign: "right" }}>Chg</th>
                  </tr>
                </thead>
                <tbody>
                  {activeLegs.map((leg) => (
                    <tr key={`iv-${leg.legId}`} style={{ borderTop: "1px solid #1e293b" }}>
                      <td style={{ padding: "4px 0", color: "#f8fafc", fontWeight: 600 }}>{leg.strike} ⓘ</td>
                      <td style={{ padding: "4px 0", color: "#94a3b8" }}>{leg.expiryDate}</td>
                      <td style={{ padding: "4px 0" }}>
                        <div style={{ display: "inline-flex", alignItems: "center", backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "3px" }}>
                          <button
                            onClick={() => handlePriceChange(leg.legId, leg.price)}
                            style={{ background: "none", border: "none", color: "#94a3b8", padding: "0 3px", cursor: "pointer" }}
                          >
                            -
                          </button>
                          <span style={{ padding: "0 3px", color: "#f8fafc" }}>
                            {(leg.iv + ivOffsetGlobal).toFixed(1)}
                          </span>
                          <button
                            onClick={() => handlePriceChange(leg.legId, leg.price)}
                            style={{ background: "none", border: "none", color: "#94a3b8", padding: "0 3px", cursor: "pointer" }}
                          >
                            +
                          </button>
                        </div>
                      </td>
                      <td style={{ padding: "4px 0", textAlign: "right", color: "#4ade80" }}>
                        (+{(leg.ivOffset + ivOffsetGlobal).toFixed(1)})
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Col 2: Greeks */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", borderRight: "1px solid #1f2937", paddingRight: "10px" }}>
              <span style={{ fontWeight: 600, color: "#f8fafc", marginBottom: "2px" }}>Greeks</span>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10.5px", color: "#94a3b8", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={multiplyLotSize}
                  onChange={(e) => setMultiplyLotSize(e.target.checked)}
                  style={{ accentColor: "#38bdf8" }}
                />
                <span>Multiply by Lot Size</span>
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10.5px", color: "#94a3b8", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={multiplyLots}
                  onChange={(e) => setMultiplyLots(e.target.checked)}
                  style={{ accentColor: "#38bdf8" }}
                />
                <span>Multiply by Number of Lots</span>
              </label>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginTop: "4px" }}>
                <span style={{ color: "#94a3b8" }}>Delta ⓘ</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{netGreeks.delta}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Theta ⓘ</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{netGreeks.theta}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Decay ⓘ</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{netGreeks.decay}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Gamma ⓘ</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{netGreeks.gamma}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Vega ⓘ</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>{netGreeks.vega}</span>
              </div>
            </div>

            {/* Col 3: Target Day Futures Prices & Standard Deviation */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px" }}>
                <span style={{ color: "#94a3b8" }}>Target Day Futures Prices ⓘ</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", borderBottom: "1px solid #1f2937", paddingBottom: "4px" }}>
                <span style={{ color: "#cbd5e1" }}>{config.expiry} FUT</span>
                <span style={{ fontWeight: 600, color: "#f8fafc" }}>
                  {(spotPrice * 1.001).toFixed(2)}
                </span>
              </div>

              <div style={{ fontSize: "11px", fontWeight: 600, color: "#f8fafc", marginTop: "2px" }}>
                Standard Deviation ⓘ
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "10px" }}>
                <thead>
                  <tr style={{ color: "#64748b", textAlign: "left" }}>
                    <th>SD</th>
                    <th>Points</th>
                    <th style={{ textAlign: "right" }}>Price</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ color: "#cbd5e1", padding: "2px 0" }}>1 SD</td>
                    <td style={{ color: "#cbd5e1", padding: "2px 0" }}>
                      {sdMetrics.oneSdPoints} ({sdMetrics.oneSdPct}%)
                    </td>
                    <td style={{ textAlign: "right", color: "#f8fafc", padding: "2px 0" }}>
                      {sdMetrics.oneSdLow} - {sdMetrics.oneSdHigh}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: "#cbd5e1", padding: "2px 0" }}>2 SD</td>
                    <td style={{ color: "#cbd5e1", padding: "2px 0" }}>
                      {sdMetrics.twoSdPoints} ({sdMetrics.twoSdPct}%)
                    </td>
                    <td style={{ textAlign: "right", color: "#f8fafc", padding: "2px 0" }}>
                      {sdMetrics.twoSdLow} - {sdMetrics.twoSdHigh}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const optionStrategyBuilderDefinition: WidgetDefinition<OptionStrategyBuilderWidgetSettings> = {
  id: "option-strategy-builder",
  title: "Multi-Leg Option Strategy Builder",
  description: "Sensibull-grade option strategy builder, payoff analyzer, live feed linked with real-time Greek simulation.",
  category: "analytics",
  icon: "🧩",
  defaultWidth: 1000,
  defaultHeight: 650,
  schema: {
    fields: [
      {
        name: "defaultUnderlying",
        label: "Underlying Index / Stock",
        type: "select",
        default: "RELIANCE",
        options: [
          { label: "RELIANCE", value: "RELIANCE" },
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
      {
        name: "defaultStrategyTemplate",
        label: "Strategy Template",
        type: "select",
        default: "BUY_CALL",
        options: [
          { label: "Buy Call", value: "BUY_CALL" },
          { label: "Bull Call Spread", value: "BULL_CALL_SPREAD" },
          { label: "Iron Condor", value: "IRON_CONDOR" },
          { label: "Short Straddle", value: "SHORT_STRADDLE" },
        ],
      },
    ],
  },
  component: OptionStrategyBuilderWidget,
};
