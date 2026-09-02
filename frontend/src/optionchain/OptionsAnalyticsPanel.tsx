import React, { useState } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../widgets/types";

export interface OptionsAnalyticsPanelSettings {
  underlying: string;
  defaultTab?: "skew" | "term" | "maxpain" | "ivrank";
}

export interface SmilePointUI {
  strike: number;
  moneyness: number;
  callIv: number;
  putIv: number;
  blendedIv: number;
  delta: number;
}

export interface TermStructurePointUI {
  expiryDate: string;
  daysToExpiry: number;
  atmIv: number;
  forwardPrice: number;
}

export interface OptionsAnalyticsData {
  underlying: string;
  spotPrice: number;
  atmIv: number;
  ivRank: {
    currentIv: number;
    ivMin52w: number | null;
    ivMax52w: number | null;
    ivRank: number | null;
    ivPercentile: number | null;
    historyDaysCount: number;
    isValid: boolean;
    unreliableReason?: string;
  };
  pcr: {
    pcrOi: number;
    pcrVolume: number;
    totalCallOi: number;
    totalPutOi: number;
    totalCallVolume: number;
    totalPutVolume: number;
  };
  maxPain: {
    maxPainStrike: number;
    strikeDistanceFromSpot: number;
    strikeDistancePct: number;
    totalCashLossAtPain: number;
    painCurve: Array<{ strike: number; totalLoss: number }>;
  };
  skew: {
    atmIv: number;
    riskReversal25d: number;
    butterfly25d: number;
    smilePoints: SmilePointUI[];
  };
  termStructure: {
    regime: string;
    slope: number;
    points: TermStructurePointUI[];
  };
}

export const OptionsAnalyticsPanel: React.FC<WidgetComponentProps<OptionsAnalyticsPanelSettings>> = ({
  settings,
}) => {
  const [underlying, setUnderlying] = useState<string>(settings.underlying || "NIFTY");
  const [activeTab, setActiveTab] = useState<"skew" | "term" | "maxpain" | "ivrank">(
    settings.defaultTab || "skew"
  );

  const spot = underlying === "NIFTY" ? 25000 : 52000;
  const step = underlying === "NIFTY" ? 50 : 100;
  const atmStrike = Math.round(spot / step) * step;

  // Mock initial high-fidelity analytics data
  const data: OptionsAnalyticsData = {
    underlying,
    spotPrice: spot,
    atmIv: 0.138,
    ivRank: {
      currentIv: 0.138,
      ivMin52w: 0.105,
      ivMax52w: 0.215,
      ivRank: 30.0,
      ivPercentile: 34.5,
      historyDaysCount: 252,
      isValid: true,
    },
    pcr: {
      pcrOi: 1.18,
      pcrVolume: 1.05,
      totalCallOi: 1450000,
      totalPutOi: 1711000,
      totalCallVolume: 920000,
      totalPutVolume: 966000,
    },
    maxPain: {
      maxPainStrike: atmStrike,
      strikeDistanceFromSpot: 0.0,
      strikeDistancePct: 0.0,
      totalCashLossAtPain: 25400000,
      painCurve: [-3, -2, -1, 0, 1, 2, 3].map((i) => ({
        strike: atmStrike + i * step,
        totalLoss: 25400000 + Math.abs(i) * 3500000,
      })),
    },
    skew: {
      atmIv: 0.138,
      riskReversal25d: 0.024,
      butterfly25d: 0.008,
      smilePoints: [-4, -3, -2, -1, 0, 1, 2, 3, 4].map((i) => {
        const k = atmStrike + i * step;
        const cIv = Math.max(0.08, 0.138 - 0.004 * i + 0.001 * (i * i));
        const pIv = Math.max(0.08, 0.138 + 0.007 * -i + 0.001 * (i * i));
        return {
          strike: k,
          moneyness: Number((k / (spot * 1.003)).toFixed(3)),
          callIv: Number((cIv * 100).toFixed(1)),
          putIv: Number((pIv * 100).toFixed(1)),
          blendedIv: Number(((i <= 0 ? pIv : cIv) * 100).toFixed(1)),
          delta: +(0.5 - 0.1 * i).toFixed(2),
        };
      }),
    },
    termStructure: {
      regime: "CONTANGO",
      slope: 0.042,
      points: [
        { expiryDate: "2026-09-10", daysToExpiry: 7, atmIv: 13.8, forwardPrice: spot * 1.001 },
        { expiryDate: "2026-09-17", daysToExpiry: 14, atmIv: 14.2, forwardPrice: spot * 1.003 },
        { expiryDate: "2026-09-24", daysToExpiry: 21, atmIv: 14.6, forwardPrice: spot * 1.005 },
        { expiryDate: "2026-10-01", daysToExpiry: 28, atmIv: 15.0, forwardPrice: spot * 1.007 },
        { expiryDate: "2026-10-29", daysToExpiry: 56, atmIv: 15.8, forwardPrice: spot * 1.014 },
      ],
    },
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)", backgroundColor: "#0b0f19", color: "#e2e8f0", fontSize: "12px" }}>
      {/* Top Header Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "#1e293b", padding: "6px 10px", borderRadius: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ color: "#94a3b8" }}>Underlying:</span>
          <select
            value={underlying}
            onChange={(e) => setUnderlying(e.target.value)}
            aria-label="Select Analytics Underlying"
            style={{ backgroundColor: "#0f172a", color: "#f8fafc", border: "1px solid #334155", borderRadius: "4px", padding: "2px 6px" }}
          >
            <option value="NIFTY">NIFTY (₹25,000)</option>
            <option value="BANKNIFTY">BANKNIFTY (₹52,000)</option>
          </select>
        </div>

        {/* Quick KPI Strip */}
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div>
            <span style={{ color: "#94a3b8" }}>ATM IV: </span>
            <strong style={{ color: "#38bdf8" }}>{(data.atmIv * 100).toFixed(1)}%</strong>
          </div>
          <div>
            <span style={{ color: "#94a3b8" }}>PCR (OI): </span>
            <strong style={{ color: data.pcr.pcrOi >= 1.0 ? "#34d399" : "#f87171" }}>{data.pcr.pcrOi}</strong>
          </div>
          <div>
            <span style={{ color: "#94a3b8" }}>Max Pain: </span>
            <strong style={{ color: "#f59e0b" }}>{data.maxPain.maxPainStrike}</strong>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid #1e293b", paddingBottom: "4px" }}>
        <button
          onClick={() => setActiveTab("skew")}
          style={{
            padding: "4px 10px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: activeTab === "skew" ? "#2563eb" : "#1e293b",
            color: "#ffffff",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          📈 Volatility Skew & Smile
        </button>
        <button
          onClick={() => setActiveTab("term")}
          style={{
            padding: "4px 10px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: activeTab === "term" ? "#2563eb" : "#1e293b",
            color: "#ffffff",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          ⏳ Term Structure
        </button>
        <button
          onClick={() => setActiveTab("maxpain")}
          style={{
            padding: "4px 10px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: activeTab === "maxpain" ? "#2563eb" : "#1e293b",
            color: "#ffffff",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          🎯 Max Pain & Loss Curve
        </button>
        <button
          onClick={() => setActiveTab("ivrank")}
          style={{
            padding: "4px 10px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: activeTab === "ivrank" ? "#2563eb" : "#1e293b",
            color: "#ffffff",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          📊 IV Rank & Percentile
        </button>
      </div>

      {/* Tab Content Panels */}
      <div style={{ flex: 1, overflowY: "auto", padding: "4px" }}>
        {activeTab === "skew" && (
          <div data-testid="tab-skew">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <div>
                <strong>25Δ Risk Reversal: </strong>
                <span style={{ color: "#38bdf8", fontWeight: 700 }}>+{(data.skew.riskReversal25d * 100).toFixed(2)}%</span> (Put Skew)
              </div>
              <div>
                <strong>25Δ Butterfly: </strong>
                <span style={{ color: "#a78bfa", fontWeight: 700 }}>+{(data.skew.butterfly25d * 100).toFixed(2)}%</span> (Smile Curvature)
              </div>
            </div>

            {/* Skew Table */}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "right" }}>
              <thead>
                <tr style={{ backgroundColor: "#1e293b", color: "#94a3b8" }}>
                  <th style={{ padding: "4px", textAlign: "center" }}>Strike</th>
                  <th style={{ padding: "4px" }}>Moneyness (K/F)</th>
                  <th style={{ padding: "4px", color: "#38bdf8" }}>Call IV</th>
                  <th style={{ padding: "4px", color: "#f87171" }}>Put IV</th>
                  <th style={{ padding: "4px", color: "#34d399" }}>Blended Smile IV</th>
                </tr>
              </thead>
              <tbody>
                {data.skew.smilePoints.map((pt) => (
                  <tr key={pt.strike} style={{ borderBottom: "1px solid #1e293b", backgroundColor: pt.strike === atmStrike ? "rgba(56, 189, 248, 0.1)" : undefined }}>
                    <td style={{ padding: "4px", textAlign: "center", fontWeight: pt.strike === atmStrike ? 700 : 400 }}>
                      {pt.strike} {pt.strike === atmStrike && "(ATM)"}
                    </td>
                    <td style={{ padding: "4px" }}>{pt.moneyness}</td>
                    <td style={{ padding: "4px", color: "#38bdf8" }}>{pt.callIv}%</td>
                    <td style={{ padding: "4px", color: "#f87171" }}>{pt.putIv}%</td>
                    <td style={{ padding: "4px", color: "#34d399", fontWeight: 600 }}>{pt.blendedIv}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "term" && (
          <div data-testid="tab-term">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px", alignItems: "center" }}>
              <div>
                <strong>Term Regime: </strong>
                <span style={{ padding: "2px 6px", borderRadius: "4px", backgroundColor: "#064e3b", color: "#34d399", fontWeight: 700 }}>
                  {data.termStructure.regime}
                </span>
              </div>
              <div>
                <strong>Annualized Slope: </strong>
                <span style={{ color: "#38bdf8" }}>+{(data.termStructure.slope * 100).toFixed(2)}% / yr</span>
              </div>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "right" }}>
              <thead>
                <tr style={{ backgroundColor: "#1e293b", color: "#94a3b8" }}>
                  <th style={{ padding: "4px", textAlign: "left" }}>Expiry Date</th>
                  <th style={{ padding: "4px" }}>DTE</th>
                  <th style={{ padding: "4px" }}>Forward Price</th>
                  <th style={{ padding: "4px", color: "#38bdf8" }}>ATM IV</th>
                </tr>
              </thead>
              <tbody>
                {data.termStructure.points.map((p) => (
                  <tr key={p.expiryDate} style={{ borderBottom: "1px solid #1e293b" }}>
                    <td style={{ padding: "4px", textAlign: "left", fontWeight: 600 }}>{p.expiryDate}</td>
                    <td style={{ padding: "4px" }}>{p.daysToExpiry} days</td>
                    <td style={{ padding: "4px" }}>₹{p.forwardPrice.toFixed(2)}</td>
                    <td style={{ padding: "4px", color: "#38bdf8", fontWeight: 700 }}>{p.atmIv}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "maxpain" && (
          <div data-testid="tab-maxpain">
            <div style={{ backgroundColor: "#1e293b", padding: "10px", borderRadius: "6px", marginBottom: "10px" }}>
              <div style={{ fontSize: "11px", color: "#94a3b8" }}>Max Pain Theory Expiration Settlement</div>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "#f59e0b" }}>
                ₹{data.maxPain.maxPainStrike}
              </div>
              <div style={{ color: "#94a3b8", fontSize: "11px" }}>
                Option buyers experience maximum total loss of ₹{(data.maxPain.totalCashLossAtPain / 10000000).toFixed(2)} Cr at this strike.
              </div>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11px", textAlign: "right" }}>
              <thead>
                <tr style={{ backgroundColor: "#1e293b", color: "#94a3b8" }}>
                  <th style={{ padding: "4px", textAlign: "center" }}>Hypothetical Expiry Price</th>
                  <th style={{ padding: "4px" }}>Total Buyer Cash Payout (Loss)</th>
                </tr>
              </thead>
              <tbody>
                {data.maxPain.painCurve.map((pt) => (
                  <tr key={pt.strike} style={{ borderBottom: "1px solid #1e293b", backgroundColor: pt.strike === data.maxPain.maxPainStrike ? "rgba(245, 158, 11, 0.15)" : undefined }}>
                    <td style={{ padding: "4px", textAlign: "center", fontWeight: pt.strike === data.maxPain.maxPainStrike ? 700 : 400 }}>
                      ₹{pt.strike} {pt.strike === data.maxPain.maxPainStrike && "🎯 Max Pain"}
                    </td>
                    <td style={{ padding: "4px" }}>₹{(pt.totalLoss / 10000000).toFixed(2)} Cr</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === "ivrank" && (
          <div data-testid="tab-ivrank">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "12px" }}>
              <div style={{ backgroundColor: "#1e293b", padding: "10px", borderRadius: "6px" }}>
                <div style={{ fontSize: "10px", color: "#94a3b8", textTransform: "uppercase" }}>IV Rank (52-Week)</div>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#38bdf8" }}>
                  {data.ivRank.ivRank?.toFixed(1)}%
                </div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>
                  Min: {((data.ivRank.ivMin52w || 0) * 100).toFixed(1)}% | Max: {((data.ivRank.ivMax52w || 0) * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ backgroundColor: "#1e293b", padding: "10px", borderRadius: "6px" }}>
                <div style={{ fontSize: "10px", color: "#94a3b8", textTransform: "uppercase" }}>IV Percentile</div>
                <div style={{ fontSize: "24px", fontWeight: 700, color: "#34d399" }}>
                  {data.ivRank.ivPercentile?.toFixed(1)}%
                </div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>
                  Based on {data.ivRank.historyDaysCount} trading days history
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: "#1e293b", padding: "10px", borderRadius: "6px", fontSize: "11px", color: "#cbd5e1" }}>
              <strong>Trading Context: </strong>
              IV Rank &lt; 30 indicates relatively low implied volatility regimes (favoring debit spreads and long volatility), while IV Rank &gt; 70 favors credit spreads, strangles, and premium collection.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const optionsAnalyticsDefinition: WidgetDefinition<OptionsAnalyticsPanelSettings> = {
  id: "options-analytics",
  title: "Options Analytics & Volatility",
  description: "Advanced ATM IV, IV Rank/Percentile, Max Pain, Volatility Smile/Skew, and Term Structure.",
  category: "analytics",
  icon: "📊",
  defaultWidth: 550,
  defaultHeight: 400,
  schema: {
    fields: [
      {
        name: "underlying",
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
  component: OptionsAnalyticsPanel,
};
