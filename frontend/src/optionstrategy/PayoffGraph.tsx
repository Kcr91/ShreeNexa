import React, { useState, useMemo } from "react";
import {
  PayoffPoint,
  OpenInterestBar,
  StandardDeviationMetrics,
} from "./types";

interface PayoffGraphProps {
  underlying: string;
  spotPrice: number;
  strikeStep: number;
  payoffCurve: PayoffPoint[];
  minPrice: number;
  maxPrice: number;
  oiBars: OpenInterestBar[];
  sdMetrics: StandardDeviationMetrics;
  targetPrice: number;
  onTargetPriceChange: (val: number) => void;
  targetDayOffset: number;
  totalDteDays: number;
  onTargetDayOffsetChange: (val: number) => void;
  expiryDateStr: string;
}

export const PayoffGraph: React.FC<PayoffGraphProps> = ({
  underlying,
  spotPrice,
  strikeStep,
  payoffCurve,
  minPrice,
  maxPrice,
  oiBars,
  sdMetrics,
  targetPrice,
  onTargetPriceChange,
  targetDayOffset,
  totalDteDays,
  onTargetDayOffsetChange,
  expiryDateStr,
}) => {
  const [activeTab, setActiveTab] = useState<"graph" | "table" | "greeks" | "chart">("graph");
  const [showOi, setShowOi] = useState<boolean>(true);
  const [showSd, setShowSd] = useState<boolean>(true);
  const [hoverPoint, setHoverPoint] = useState<{ x: number; price: number; pnl: number } | null>(null);

  // Layout dimensions for SVG viewport
  const width = 760;
  const height = 300;
  const padLeft = 60;
  const padRight = 50;
  const padTop = 30;
  const padBottom = 40;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  // Price range mapping
  const pMin = minPrice || spotPrice * 0.92;
  const pMax = maxPrice || spotPrice * 1.08;
  const pSpan = Math.max(10, pMax - pMin);

  const scaleX = (price: number) => padLeft + ((price - pMin) / pSpan) * chartW;
  const unscaleX = (x: number) => pMin + ((x - padLeft) / chartW) * pSpan;

  // P&L range mapping
  const pnlMin = useMemo(() => {
    if (payoffCurve.length === 0) return -15000;
    const minPnl = Math.min(...payoffCurve.map((p) => Math.min(p.expiryPnl, p.targetPnl)));
    return Math.min(-5000, Math.floor(minPnl / 5000) * 5000);
  }, [payoffCurve]);

  const pnlMax = useMemo(() => {
    if (payoffCurve.length === 0) return 25000;
    const maxPnl = Math.max(...payoffCurve.map((p) => Math.max(p.expiryPnl, p.targetPnl)));
    return Math.max(5000, Math.ceil(maxPnl / 5000) * 5000);
  }, [payoffCurve]);

  const pnlSpan = Math.max(1000, pnlMax - pnlMin);
  const scaleY = (pnl: number) => padTop + chartH - ((pnl - pnlMin) / pnlSpan) * chartH;

  const zeroY = scaleY(0);

  // Maximum OI for right axis
  const maxOi = useMemo(() => {
    if (oiBars.length === 0) return 2000000;
    return Math.max(...oiBars.map((b) => Math.max(b.callOi, b.putOi))) * 1.5;
  }, [oiBars]);

  const scaleOiY = (oi: number) => padTop + chartH - (oi / maxOi) * (chartH * 0.85);

  // Build SVG Paths for On-Expiry and Target-Date
  const { expiryPath, targetPath, profitAreaPath, lossAreaPath } = useMemo(() => {
    if (payoffCurve.length === 0) {
      return { expiryPath: "", targetPath: "", profitAreaPath: "", lossAreaPath: "" };
    }

    let expD = "";
    let tgtD = "";

    payoffCurve.forEach((pt, idx) => {
      const x = scaleX(pt.price);
      const yExp = Math.max(padTop, Math.min(padTop + chartH, scaleY(pt.expiryPnl)));
      const yTgt = Math.max(padTop, Math.min(padTop + chartH, scaleY(pt.targetPnl)));

      if (idx === 0) {
        expD += `M ${x.toFixed(1)} ${yExp.toFixed(1)}`;
        tgtD += `M ${x.toFixed(1)} ${yTgt.toFixed(1)}`;
      } else {
        expD += ` L ${x.toFixed(1)} ${yExp.toFixed(1)}`;
        tgtD += ` L ${x.toFixed(1)} ${yTgt.toFixed(1)}`;
      }
    });

    // Area fill paths
    const firstX = scaleX(payoffCurve[0].price);
    const lastX = scaleX(payoffCurve[payoffCurve.length - 1].price);

    const profitArea = `${expD} L ${lastX} ${zeroY} L ${firstX} ${zeroY} Z`;
    const lossArea = `${expD} L ${lastX} ${zeroY} L ${firstX} ${zeroY} Z`;

    return {
      expiryPath: expD,
      targetPath: tgtD,
      profitAreaPath: profitArea,
      lossAreaPath: lossArea,
    };
  }, [payoffCurve, scaleX, scaleY, padTop, chartH, zeroY]);

  // Interpolate target price P&L for tooltip and projected profit badge
  const targetPointPnl = useMemo(() => {
    if (payoffCurve.length === 0) return 0;
    // Find closest point
    let closest = payoffCurve[0];
    let minDiff = Math.abs(closest.price - targetPrice);
    for (const pt of payoffCurve) {
      const diff = Math.abs(pt.price - targetPrice);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }
    return closest.targetPnl;
  }, [payoffCurve, targetPrice]);

  const targetPctChange = Number((((targetPrice - spotPrice) / spotPrice) * 100).toFixed(1));

  // ATM OI bar for legend display
  const atmOi = useMemo(() => {
    if (oiBars.length === 0) return { callOiFormatted: "13.13L", putOiFormatted: "13.51L", strike: Math.round(spotPrice) };
    const atm = Math.round(spotPrice / strikeStep) * strikeStep;
    return oiBars.find((b) => b.strike === atm) || oiBars[Math.floor(oiBars.length / 2)];
  }, [oiBars, spotPrice, strikeStep]);

  // Ticks for X axis
  const xTicks = useMemo(() => {
    const ticks: number[] = [];
    const step = strikeStep * 2 || 20;
    const start = Math.ceil(pMin / step) * step;
    for (let p = start; p <= pMax; p += step) {
      ticks.push(p);
    }
    return ticks;
  }, [pMin, pMax, strikeStep]);

  // Ticks for Left Y axis (P&L)
  const yTicks = useMemo(() => {
    const ticks: number[] = [];
    const step = 10000;
    const start = Math.ceil(pnlMin / step) * step;
    for (let val = start; val <= pnlMax; val += step) {
      ticks.push(val);
    }
    if (!ticks.includes(0)) ticks.push(0);
    return ticks.sort((a, b) => b - a);
  }, [pnlMin, pnlMax]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#111827",
        borderRadius: "8px",
        border: "1px solid #1f2937",
        overflow: "hidden",
      }}
    >
      {/* Sub Tabs and Controls Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 14px",
          borderBottom: "1px solid #1f2937",
          backgroundColor: "#0d131f",
        }}
      >
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <button
            onClick={() => setActiveTab("graph")}
            style={{
              background: "none",
              border: "none",
              color: activeTab === "graph" ? "#38bdf8" : "#94a3b8",
              fontWeight: activeTab === "graph" ? 600 : 400,
              fontSize: "12px",
              cursor: "pointer",
              paddingBottom: "2px",
              borderBottom: activeTab === "graph" ? "2px solid #38bdf8" : "none",
            }}
          >
            Payoff Graph
          </button>
          <button
            onClick={() => setActiveTab("table")}
            style={{
              background: "none",
              border: "none",
              color: activeTab === "table" ? "#38bdf8" : "#94a3b8",
              fontWeight: activeTab === "table" ? 600 : 400,
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            P&L Table
          </button>
          <button
            onClick={() => setActiveTab("greeks")}
            style={{
              background: "none",
              border: "none",
              color: activeTab === "greeks" ? "#38bdf8" : "#94a3b8",
              fontWeight: activeTab === "greeks" ? 600 : 400,
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            Greeks
          </button>
          <button
            onClick={() => setActiveTab("chart")}
            style={{
              background: "none",
              border: "none",
              color: activeTab === "chart" ? "#38bdf8" : "#94a3b8",
              fontWeight: activeTab === "chart" ? 600 : 400,
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            Strategy Chart
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "11px", color: "#94a3b8" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
            <input type="checkbox" defaultChecked={false} />
            <span>Add Booked P&L ⓘ</span>
          </label>

          <select
            value={showSd ? "fixed" : "none"}
            onChange={(e) => setShowSd(e.target.value === "fixed")}
            style={{
              backgroundColor: "#1f2937",
              color: "#e2e8f0",
              border: "1px solid #374151",
              borderRadius: "4px",
              padding: "2px 6px",
              fontSize: "11px",
            }}
          >
            <option value="fixed">SD Fixed</option>
            <option value="none">SD Off</option>
          </select>

          <select
            value={showOi ? "oi" : "none"}
            onChange={(e) => setShowOi(e.target.value === "oi")}
            style={{
              backgroundColor: "#1f2937",
              color: "#e2e8f0",
              border: "1px solid #374151",
              borderRadius: "4px",
              padding: "2px 6px",
              fontSize: "11px",
            }}
          >
            <option value="oi">Open Interest</option>
            <option value="none">Hide OI</option>
          </select>
        </div>
      </div>

      {/* Legend & Stats Banner */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "6px 14px",
          fontSize: "11px",
          color: "#94a3b8",
          backgroundColor: "#0d131f",
          borderBottom: "1px solid #1f2937",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <span>OI data at {atmOi.strike}</span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#f87171" }}>
            <span style={{ width: "8px", height: "8px", backgroundColor: "#f87171", display: "inline-block", borderRadius: "1px" }} />
            Call OI {atmOi.callOiFormatted}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "#4ade80" }}>
            <span style={{ width: "8px", height: "8px", backgroundColor: "#4ade80", display: "inline-block", borderRadius: "1px" }} />
            Put OI {atmOi.putOiFormatted}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#34d399" }}>
            <span style={{ width: "14px", height: "3px", backgroundColor: "#34d399", display: "inline-block", borderRadius: "1px" }} />
            On Expiry
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px", color: "#38bdf8" }}>
            <span style={{ width: "14px", height: "3px", backgroundColor: "#38bdf8", display: "inline-block", borderRadius: "1px" }} />
            On Target Date
          </span>
          <button
            onClick={() => onTargetPriceChange(spotPrice)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              background: "#1f2937",
              border: "1px solid #374151",
              color: "#e2e8f0",
              padding: "2px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              cursor: "pointer",
            }}
          >
            🔍 Zoom Out
          </button>
        </div>
      </div>

      {/* SVG Payoff Chart Canvas */}
      <div style={{ position: "relative", width: "100%", height: `${height}px`, userSelect: "none" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", height: "100%", display: "block" }}
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const relX = (e.clientX - rect.left) * (width / rect.width);
            if (relX >= padLeft && relX <= padLeft + chartW) {
              const price = unscaleX(relX);
              setHoverPoint({ x: relX, price, pnl: 0 });
            }
          }}
          onMouseLeave={() => setHoverPoint(null)}
        >
          <defs>
            <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="lossGrad" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0.0" />
            </linearGradient>
            <pattern id="diagonalHatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="8" stroke="#ef4444" strokeWidth="1" strokeOpacity="0.15" />
            </pattern>
          </defs>

          {/* Grid lines - horizontal */}
          {yTicks.map((val) => {
            const y = scaleY(val);
            return (
              <g key={`y-${val}`}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={padLeft + chartW}
                  y2={y}
                  stroke={val === 0 ? "#64748b" : "#1f2937"}
                  strokeWidth={val === 0 ? 1.5 : 1}
                  strokeDasharray={val === 0 ? "4 4" : undefined}
                />
                <text
                  x={padLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill={val === 0 ? "#94a3b8" : "#64748b"}
                  fontSize="10"
                >
                  {val === 0 ? "0" : val.toLocaleString("en-IN")}
                </text>
              </g>
            );
          })}

          {/* Right Y-Axis labels (Open Interest in Lakhs) */}
          {[0, 20, 40, 60, 80].map((lakh) => {
            const oi = lakh * 100000;
            const y = scaleOiY(oi);
            if (y < padTop || y > padTop + chartH) return null;
            return (
              <text
                key={`oi-${lakh}`}
                x={padLeft + chartW + 8}
                y={y + 3}
                textAnchor="start"
                fill="#64748b"
                fontSize="10"
              >
                {lakh}L
              </text>
            );
          })}

          {/* Open Interest Vertical Bars */}
          {showOi &&
            oiBars.map((bar) => {
              const x = scaleX(bar.strike);
              if (x < padLeft || x > padLeft + chartW) return null;

              const barW = 7;
              const callH = padTop + chartH - scaleOiY(bar.callOi);
              const putH = padTop + chartH - scaleOiY(bar.putOi);

              return (
                <g key={`bar-${bar.strike}`}>
                  {/* Call OI Red Bar */}
                  <rect
                    x={x - barW - 1}
                    y={padTop + chartH - callH}
                    width={barW}
                    height={callH}
                    fill="#ef4444"
                    opacity={0.65}
                    rx={1}
                  />
                  {/* Put OI Green Bar */}
                  <rect
                    x={x + 1}
                    y={padTop + chartH - putH}
                    width={barW}
                    height={putH}
                    fill="#22c55e"
                    opacity={0.65}
                    rx={1}
                  />
                </g>
              );
            })}

          {/* Standard Deviation Lines (-2SD, -1SD, 1SD, 2SD) */}
          {showSd && (
            <g>
              {/* -2SD */}
              {scaleX(sdMetrics.twoSdLow) >= padLeft && (
                <g>
                  <line
                    x1={scaleX(sdMetrics.twoSdLow)}
                    y1={padTop}
                    x2={scaleX(sdMetrics.twoSdLow)}
                    y2={padTop + chartH}
                    stroke="#475569"
                    strokeDasharray="3 3"
                  />
                  <text x={scaleX(sdMetrics.twoSdLow)} y={padTop - 8} textAnchor="middle" fill="#94a3b8" fontSize="9">
                    -2SD
                  </text>
                </g>
              )}

              {/* -1SD */}
              {scaleX(sdMetrics.oneSdLow) >= padLeft && (
                <g>
                  <line
                    x1={scaleX(sdMetrics.oneSdLow)}
                    y1={padTop}
                    x2={scaleX(sdMetrics.oneSdLow)}
                    y2={padTop + chartH}
                    stroke="#475569"
                    strokeDasharray="3 3"
                  />
                  <text x={scaleX(sdMetrics.oneSdLow)} y={padTop - 8} textAnchor="middle" fill="#94a3b8" fontSize="9">
                    -1SD
                  </text>
                </g>
              )}

              {/* 1SD */}
              {scaleX(sdMetrics.oneSdHigh) <= padLeft + chartW && (
                <g>
                  <line
                    x1={scaleX(sdMetrics.oneSdHigh)}
                    y1={padTop}
                    x2={scaleX(sdMetrics.oneSdHigh)}
                    y2={padTop + chartH}
                    stroke="#475569"
                    strokeDasharray="3 3"
                  />
                  <text x={scaleX(sdMetrics.oneSdHigh)} y={padTop - 8} textAnchor="middle" fill="#94a3b8" fontSize="9">
                    1SD
                  </text>
                </g>
              )}

              {/* 2SD */}
              {scaleX(sdMetrics.twoSdHigh) <= padLeft + chartW && (
                <g>
                  <line
                    x1={scaleX(sdMetrics.twoSdHigh)}
                    y1={padTop}
                    x2={scaleX(sdMetrics.twoSdHigh)}
                    y2={padTop + chartH}
                    stroke="#475569"
                    strokeDasharray="3 3"
                  />
                  <text x={scaleX(sdMetrics.twoSdHigh)} y={padTop - 8} textAnchor="middle" fill="#94a3b8" fontSize="9">
                    2SD
                  </text>
                </g>
              )}
            </g>
          )}

          {/* Shaded Profit & Loss Areas */}
          {profitAreaPath && (
            <path d={profitAreaPath} fill="url(#profitGrad)" clipPath="url(#profitClip)" />
          )}
          {lossAreaPath && (
            <path d={lossAreaPath} fill="url(#diagonalHatch)" />
          )}

          {/* On-Expiry Payoff Line (Green) */}
          {expiryPath && (
            <path
              d={expiryPath}
              fill="none"
              stroke="#10b981"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />
          )}

          {/* On-Target Date Payoff Line (Blue) */}
          {targetPath && (
            <path
              d={targetPath}
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />
          )}

          {/* Current Spot Price Vertical Line */}
          {scaleX(spotPrice) >= padLeft && scaleX(spotPrice) <= padLeft + chartW && (
            <g>
              <line
                x1={scaleX(spotPrice)}
                y1={padTop}
                x2={scaleX(spotPrice)}
                y2={padTop + chartH}
                stroke="#94a3b8"
                strokeWidth="1.2"
                strokeDasharray="2 2"
              />
              <rect
                x={scaleX(spotPrice) - 52}
                y={padTop + 6}
                width="104"
                height="18"
                rx="3"
                fill="#1e293b"
                stroke="#334155"
              />
              <text
                x={scaleX(spotPrice)}
                y={padTop + 19}
                textAnchor="middle"
                fill="#f8fafc"
                fontSize="9.5"
                fontWeight="500"
              >
                Current price: {spotPrice.toFixed(2)}
              </text>
            </g>
          )}

          {/* Target Price Vertical Indicator & Projected Profit Badge */}
          {scaleX(targetPrice) >= padLeft && scaleX(targetPrice) <= padLeft + chartW && (
            <g>
              <line
                x1={scaleX(targetPrice)}
                y1={padTop}
                x2={scaleX(targetPrice)}
                y2={padTop + chartH}
                stroke="#38bdf8"
                strokeWidth="1.5"
              />
              {/* Highlight circle on Target Curve */}
              <circle
                cx={scaleX(targetPrice)}
                cy={Math.max(padTop, Math.min(padTop + chartH, scaleY(targetPointPnl)))}
                r="4.5"
                fill="#38bdf8"
                stroke="#0f172a"
                strokeWidth="1.5"
              />
              {/* Projected profit pill */}
              <g transform={`translate(${scaleX(targetPrice)}, ${padTop + chartH - 24})`}>
                <rect
                  x="-70"
                  y="-12"
                  width="140"
                  height="22"
                  rx="4"
                  fill={targetPointPnl >= 0 ? "#059669" : "#dc2626"}
                />
                <text
                  x="0"
                  y="3"
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="10"
                  fontWeight="600"
                >
                  Projected profit: {targetPointPnl >= 0 ? targetPointPnl : targetPointPnl} ({targetPctChange >= 0 ? `+${targetPctChange}%` : `${targetPctChange}%`})
                </text>
              </g>
            </g>
          )}

          {/* Hover Crosshair Guide */}
          {hoverPoint && (
            <g>
              <line
                x1={hoverPoint.x}
                y1={padTop}
                x2={hoverPoint.x}
                y2={padTop + chartH}
                stroke="#64748b"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <rect
                x={hoverPoint.x - 30}
                y={padTop + chartH + 2}
                width="60"
                height="14"
                rx="2"
                fill="#1e293b"
                stroke="#475569"
              />
              <text
                x={hoverPoint.x}
                y={padTop + chartH + 12}
                textAnchor="middle"
                fill="#f8fafc"
                fontSize="9"
              >
                {hoverPoint.price.toFixed(1)}
              </text>
            </g>
          )}

          {/* Grid lines - vertical / X-axis ticks */}
          {xTicks.map((tick) => {
            const x = scaleX(tick);
            return (
              <g key={`xtick-${tick}`}>
                <line
                  x1={x}
                  y1={padTop + chartH}
                  x2={x}
                  y2={padTop + chartH + 5}
                  stroke="#475569"
                />
                <text
                  x={x}
                  y={padTop + chartH + 18}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                >
                  {tick.toLocaleString("en-IN")}
                </text>
              </g>
            );
          })}

          {/* Axis Labels */}
          <text
            x={padLeft - 10}
            y={padTop - 12}
            textAnchor="end"
            fill="#64748b"
            fontSize="9"
          >
            Profit / loss
          </text>
          <text
            x={padLeft + chartW + 10}
            y={padTop - 12}
            textAnchor="start"
            fill="#64748b"
            fontSize="9"
          >
            Open Interest
          </text>
        </svg>
      </div>

      {/* Target Price & Target Date Interactive Sliders */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "16px",
          padding: "10px 16px",
          borderTop: "1px solid #1f2937",
          backgroundColor: "#0d131f",
        }}
      >
        {/* Left: Target Price Slider */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "#f8fafc", fontWeight: 600 }}>
                {underlying} Target
              </span>
              <button
                onClick={() => onTargetPriceChange(spotPrice)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#38bdf8",
                  fontSize: "11px",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                Reset
              </button>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                {targetPctChange >= 0 ? `+${targetPctChange}%` : `${targetPctChange}%`}
              </span>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <button
                  onClick={() => onTargetPriceChange(Number((targetPrice - strikeStep * 0.5).toFixed(1)))}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#cbd5e1",
                    padding: "2px 6px",
                    cursor: "pointer",
                  }}
                >
                  -
                </button>
                <input
                  type="number"
                  value={targetPrice}
                  onChange={(e) => onTargetPriceChange(Number(e.target.value))}
                  style={{
                    width: "60px",
                    background: "none",
                    border: "none",
                    color: "#f8fafc",
                    fontSize: "11px",
                    textAlign: "center",
                  }}
                />
                <button
                  onClick={() => onTargetPriceChange(Number((targetPrice + strikeStep * 0.5).toFixed(1)))}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#cbd5e1",
                    padding: "2px 6px",
                    cursor: "pointer",
                  }}
                >
                  +
                </button>
              </div>
            </div>
          </div>

          <input
            type="range"
            min={spotPrice * 0.9}
            max={spotPrice * 1.1}
            step={strikeStep * 0.1}
            value={targetPrice}
            onChange={(e) => onTargetPriceChange(Number(e.target.value))}
            style={{ width: "100%", accentColor: "#38bdf8", cursor: "pointer" }}
            aria-label="Target Price Slider"
          />
        </div>

        {/* Right: Target Date & Time Slider */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "#f8fafc", fontWeight: 600 }}>
                Date: {totalDteDays - targetDayOffset}D to expiry ⓘ
              </span>
              <button
                onClick={() => onTargetDayOffsetChange(0)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#38bdf8",
                  fontSize: "11px",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                Reset
              </button>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <button
                onClick={() => onTargetDayOffsetChange(Math.max(0, targetDayOffset - 1))}
                style={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  color: "#cbd5e1",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                &lt;
              </button>
              <span
                style={{
                  fontSize: "11px",
                  color: "#f8fafc",
                  backgroundColor: "#1f2937",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  border: "1px solid #374151",
                }}
              >
                {`Day +${targetDayOffset} (${expiryDateStr})`}
              </span>
              <button
                onClick={() => onTargetDayOffsetChange(Math.min(totalDteDays, targetDayOffset + 1))}
                style={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  color: "#cbd5e1",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                &gt;
              </button>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
            <input
              type="range"
              min={0}
              max={totalDteDays}
              step={1}
              value={targetDayOffset}
              onChange={(e) => onTargetDayOffsetChange(Number(e.target.value))}
              style={{ width: "100%", accentColor: "#38bdf8", cursor: "pointer" }}
              aria-label="Target Date Slider"
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#64748b" }}>
              <span>Today</span>
              <span>Expiry ({expiryDateStr})</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
