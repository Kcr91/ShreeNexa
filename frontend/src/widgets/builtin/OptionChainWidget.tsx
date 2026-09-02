import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import { OptionChainWidgetSettings, OptionContract } from "../../optionchain/types";
import { generateOptionChain } from "../../optionchain/greeks";
import { DriftBadge } from "../../optionchain/DriftBadge";

export const OptionChainWidget: React.FC<WidgetComponentProps<OptionChainWidgetSettings>> = ({
  settings,
}) => {
  const [underlying, setUnderlying] = useState<string>(settings.defaultUnderlying || "NIFTY");
  const [expiry, setExpiry] = useState<string>("2026-01-29");
  const [selectedLegInfo, setSelectedLegInfo] = useState<string | null>(null);

  const spotPrice = underlying === "NIFTY" ? 24520 : underlying === "BANKNIFTY" ? 51800 : 23100;
  const strikeStep = underlying === "NIFTY" ? 50 : 100;

  const chainData = useMemo(() => {
    return generateOptionChain(underlying, spotPrice, expiry, strikeStep, settings.strikesCount || 8);
  }, [underlying, spotPrice, expiry, strikeStep, settings.strikesCount]);

  const handleSelectContract = (contract: OptionContract, side: "BUY" | "SELL") => {
    setSelectedLegInfo(`Selected: ${contract.symbol} ${side} @ ₹${contract.ltp}`);
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Controls & Metrics Strip */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
            <span style={{ color: "var(--text-muted)" }}>Index:</span>
            <select
              value={underlying}
              onChange={(e) => setUnderlying(e.target.value)}
              aria-label="Select Underlying Index"
              style={{
                backgroundColor: "var(--bg-active)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 6px",
              }}
            >
              <option value="NIFTY">NIFTY</option>
              <option value="BANKNIFTY">BANKNIFTY</option>
            </select>
          </div>

          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Spot:</span>
            <strong data-testid="option-chain-spot" style={{ fontFamily: "var(--font-family-mono)", color: "var(--color-up)" }}>
              ₹{spotPrice.toLocaleString()}
            </strong>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
            <span style={{ color: "var(--text-muted)" }}>Expiry:</span>
            <select
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              aria-label="Select Expiry Date"
              style={{
                backgroundColor: "var(--bg-active)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 6px",
              }}
            >
              {chainData.expiries.map((exp) => (
                <option key={exp} value={exp}>
                  {exp}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Analytics Badges */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
          <DriftBadge underlying={underlying} />
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>PCR:</span>
            <strong style={{ fontFamily: "var(--font-family-mono)" }}>{chainData.pcrRatio}</strong>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)", marginRight: "4px" }}>Max Pain:</span>
            <strong style={{ fontFamily: "var(--font-family-mono)", color: "var(--color-primary)" }}>
              {chainData.maxPainStrike}
            </strong>
          </div>
        </div>
      </div>

      {/* Selected Leg Notification */}
      {selectedLegInfo && (
        <div
          role="status"
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--color-primary-bg)",
            color: "var(--color-primary)",
            fontSize: "var(--font-size-xs)",
            borderRadius: "var(--radius-sm)",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>{selectedLegInfo}</span>
          <button
            type="button"
            onClick={() => setSelectedLegInfo(null)}
            style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Symmetrical Dual-Sided Option Chain Table */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.6875rem" }}>
          <thead>
            <tr style={{ backgroundColor: "var(--bg-surface)", borderBottom: "1px solid var(--border-default)" }}>
              <th colSpan={5} style={{ padding: "4px", color: "var(--color-up)", textAlign: "center" }}>
                CALLS (CE)
              </th>
              <th style={{ padding: "4px", textAlign: "center", backgroundColor: "var(--bg-active)" }}>STRIKE</th>
              <th colSpan={5} style={{ padding: "4px", color: "var(--color-down)", textAlign: "center" }}>
                PUTS (PE)
              </th>
            </tr>
            <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
              {/* Call Headers */}
              <th style={{ padding: "4px", textAlign: "right" }}>OI</th>
              <th style={{ padding: "4px", textAlign: "right" }}>IV</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Delta</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Theta</th>
              <th style={{ padding: "4px", textAlign: "right" }}>LTP</th>

              {/* Center Strike */}
              <th style={{ padding: "4px", textAlign: "center", backgroundColor: "var(--bg-active)" }}>Price</th>

              {/* Put Headers */}
              <th style={{ padding: "4px", textAlign: "left" }}>LTP</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Theta</th>
              <th style={{ padding: "4px", textAlign: "right" }}>Delta</th>
              <th style={{ padding: "4px", textAlign: "right" }}>IV</th>
              <th style={{ padding: "4px", textAlign: "right" }}>OI</th>
            </tr>
          </thead>
          <tbody>
            {chainData.rows.map((row) => {
              const isCallItm = row.strike < spotPrice;
              const isPutItm = row.strike > spotPrice;

              return (
                <tr
                  key={row.strike}
                  data-testid={`strike-row-${row.strike}`}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    backgroundColor: row.isAtm ? "rgba(0, 210, 255, 0.08)" : undefined,
                  }}
                >
                  {/* Call Columns */}
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", color: "var(--text-muted)" }}>
                    {(row.call.oi / 1000).toFixed(0)}k
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {row.call.iv}%
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {row.call.greeks.delta.toFixed(2)}
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", color: "var(--color-down)" }}>
                    {row.call.greeks.theta.toFixed(1)}
                  </td>
                  <td
                    style={{
                      padding: "4px",
                      textAlign: "right",
                      fontFamily: "var(--font-family-mono)",
                      backgroundColor: isCallItm ? "rgba(0, 192, 118, 0.08)" : undefined,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelectContract(row.call, "BUY")}
                      aria-label={`Buy ${row.call.symbol}`}
                      style={{
                        padding: "1px 4px",
                        backgroundColor: "transparent",
                        border: "1px solid var(--border-default)",
                        color: "var(--color-up)",
                        borderRadius: "2px",
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      ₹{row.call.ltp.toFixed(2)}
                    </button>
                  </td>

                  {/* Center Strike Price */}
                  <td
                    style={{
                      padding: "4px",
                      textAlign: "center",
                      fontFamily: "var(--font-family-mono)",
                      fontWeight: 700,
                      backgroundColor: "var(--bg-active)",
                      color: row.isAtm ? "var(--color-primary)" : "var(--text-primary)",
                    }}
                  >
                    {row.strike}
                    {row.isAtm && (
                      <span
                        style={{
                          marginLeft: "4px",
                          fontSize: "0.5625rem",
                          padding: "1px 3px",
                          backgroundColor: "var(--color-primary)",
                          color: "var(--text-inverse)",
                          borderRadius: "2px",
                        }}
                      >
                        ATM
                      </span>
                    )}
                  </td>

                  {/* Put Columns */}
                  <td
                    style={{
                      padding: "4px",
                      textAlign: "left",
                      fontFamily: "var(--font-family-mono)",
                      backgroundColor: isPutItm ? "rgba(255, 77, 79, 0.08)" : undefined,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelectContract(row.put, "BUY")}
                      aria-label={`Buy ${row.put.symbol}`}
                      style={{
                        padding: "1px 4px",
                        backgroundColor: "transparent",
                        border: "1px solid var(--border-default)",
                        color: "var(--color-down)",
                        borderRadius: "2px",
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      ₹{row.put.ltp.toFixed(2)}
                    </button>
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", color: "var(--color-down)" }}>
                    {row.put.greeks.theta.toFixed(1)}
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {row.put.greeks.delta.toFixed(2)}
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)" }}>
                    {row.put.iv}%
                  </td>
                  <td style={{ padding: "4px", textAlign: "right", fontFamily: "var(--font-family-mono)", color: "var(--text-muted)" }}>
                    {(row.put.oi / 1000).toFixed(0)}k
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export const optionChainDefinition: WidgetDefinition<OptionChainWidgetSettings> = {
  id: "option-chain",
  title: "Option Chain & Greeks",
  description: "Symmetrical strike ladder with Black-Scholes Greeks, IV, PCR, and leg selector.",
  category: "analytics",
  icon: "⛓️",
  defaultWidth: 550,
  defaultHeight: 420,
  schema: {
    fields: [
      {
        name: "defaultUnderlying",
        label: "Default Index",
        type: "select",
        default: "NIFTY",
        options: [
          { label: "NIFTY", value: "NIFTY" },
          { label: "BANKNIFTY", value: "BANKNIFTY" },
        ],
      },
      {
        name: "strikesCount",
        label: "Strikes Count (± ATM)",
        type: "number",
        default: 8,
        min: 4,
        max: 20,
      },
      {
        name: "showGreeks",
        label: "Display Greeks",
        type: "boolean",
        default: true,
      },
      {
        name: "showIV",
        label: "Display IV",
        type: "boolean",
        default: true,
      },
    ],
  },
  component: OptionChainWidget,
};
