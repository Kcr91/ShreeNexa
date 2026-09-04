import React, { useMemo, useState } from "react";

export type ActiveRoute =
  | "dashboard"
  | "research"
  | "screener"
  | "pnl"
  | "settings"
  | "watchlist"
  | "sector-drill-in"
  | "market-depth"
  | "chart"
  | "option-chain"
  | "option-strategy-builder"
  | "options-analytics"
  | "order-ticket"
  | "blotter"
  | "paper_trading"
  | "grading-thresholds"
  | "live-feed-status"
  | "alerts-log"
  | "pnl-calendar"
  | "returns-timeline"
  | "backtest-summary"
  | "backtest-analytics"
  | "strategy-marketplace"
  | "strategy-builder"
  | "market-heatmap"
  | (string & {});

export interface NavItem {
  id: ActiveRoute;
  label: string;
  badge?: string;
  icon: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    title: "Workspace",
    items: [
      { id: "dashboard", label: "Dashboard", icon: "📊" },
      { id: "settings", label: "Settings", icon: "⚙️" },
    ],
  },
  {
    title: "Watchlist & Markets",
    items: [
      { id: "watchlist", label: "Market Watchlist", icon: "📋" },
      { id: "sector-drill-in", label: "Sector & Index Drill-In", icon: "📊" },
      { id: "market-depth", label: "Market Depth Ladder", icon: "🪜" },
      { id: "market-heatmap", label: "Market Heatmap & Breadth", icon: "🗺️" },
      { id: "screener", label: "PIT Screener", icon: "🔍" },
    ],
  },
  {
    title: "Charts & Orders",
    items: [
      { id: "chart", label: "Candlestick Chart", icon: "📈" },
      { id: "order-ticket", label: "Order Ticket & Leg Builder", icon: "🎫" },
      { id: "blotter", label: "Positions & Orders Blotter", icon: "📑" },
      { id: "paper_trading", label: "Paper Trading Blotter", icon: "💼" },
    ],
  },
  {
    title: "Options Desk",
    items: [
      { id: "option-chain", label: "Option Chain & Greeks", icon: "⛓️" },
      { id: "option-strategy-builder", label: "Multi-Leg Option Builder", icon: "📐" },
      { id: "options-analytics", label: "Options Analytics & Volatility", icon: "📊" },
    ],
  },
  {
    title: "Quant & Strategy",
    items: [
      { id: "strategy-builder", label: "Visual Strategy Builder", icon: "🧱", badge: "Engine" },
      { id: "research", label: "Strategy Lab", icon: "🔬" },
      { id: "backtest-summary", label: "Backtest Performance Summary", icon: "📜" },
      { id: "backtest-analytics", label: "Backtest Analytics & Scorecard", icon: "🔬" },
      { id: "grading-thresholds", label: "Grading Thresholds", icon: "🎯" },
      { id: "strategy-marketplace", label: "Strategy Marketplace", icon: "🛍️" },
    ],
  },
  {
    title: "Performance & Logs",
    items: [
      { id: "pnl-calendar", label: "P&L Calendar", icon: "📅" },
      { id: "returns-timeline", label: "Returns & Timeline", icon: "⏱️" },
      { id: "pnl", label: "Daily P&L / TWR", icon: "📈" },
      { id: "live-feed-status", label: "Live Feed & Telemetry", icon: "📡" },
      { id: "alerts-log", label: "Alerts & Audit Log", icon: "🔔" },
    ],
  },
];

interface Props {
  activeRoute: ActiveRoute;
  onRouteChange: (route: ActiveRoute) => void;
}

export const Navigation: React.FC<Props> = ({ activeRoute, onRouteChange }) => {
  const [searchFilter, setSearchFilter] = useState("");

  const filteredGroups = useMemo(() => {
    if (!searchFilter.trim()) return navGroups;
    const q = searchFilter.toLowerCase().trim();

    return navGroups
      .map((group) => ({
        ...group,
        items: group.items.filter(
          (item) =>
            item.label.toLowerCase().includes(q) ||
            item.id.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.items.length > 0);
  }, [searchFilter]);

  return (
    <nav
      role="navigation"
      aria-label="Terminal primary navigation"
      style={{
        width: "var(--nav-width, 240px)",
        minWidth: "var(--nav-width, 240px)",
        height: "100%",
        backgroundColor: "var(--bg-secondary)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        overflowY: "auto",
        overflowX: "hidden",
        userSelect: "none",
        boxSizing: "border-box",
      }}
    >
      {/* Navigation Header */}
      <div
        style={{
          padding: "var(--spacing-3) var(--spacing-4) var(--spacing-2)",
          display: "flex",
          flexDirection: "column",
          gap: "var(--spacing-2)",
          borderBottom: "1px solid var(--border-subtle)",
          position: "sticky",
          top: 0,
          backgroundColor: "var(--bg-secondary)",
          zIndex: 2,
        }}
      >
        <div
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: "1px",
            fontWeight: "bold",
          }}
        >
          Navigation
        </div>

        {/* Quick Filter Input */}
        <input
          type="text"
          placeholder="Filter views & apps..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          aria-label="Filter navigation"
          style={{
            width: "100%",
            padding: "4px 8px",
            fontSize: "11px",
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm, 4px)",
            outline: "none",
            boxSizing: "border-box",
          }}
        />
      </div>

      {/* Nav Groups */}
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", padding: "var(--spacing-2) 0" }}>
        {filteredGroups.length === 0 ? (
          <div
            style={{
              padding: "var(--spacing-4)",
              textAlign: "center",
              fontSize: "var(--font-size-xs)",
              color: "var(--text-muted)",
            }}
          >
            No matches found
          </div>
        ) : (
          filteredGroups.map((group) => (
            <div key={group.title} style={{ display: "flex", flexDirection: "column" }}>
              <div
                style={{
                  padding: "var(--spacing-2) var(--spacing-4) var(--spacing-1)",
                  fontSize: "0.6875rem",
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.75px",
                  fontWeight: 700,
                }}
              >
                {group.title}
              </div>

              {group.items.map((item) => {
                const isActive = activeRoute === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    id={`nav-tab-${item.id}`}
                    aria-selected={isActive}
                    role="tab"
                    onClick={() => onRouteChange(item.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "var(--spacing-2) var(--spacing-4)",
                      backgroundColor: isActive ? "var(--bg-active)" : "transparent",
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      border: "none",
                      borderLeft: isActive ? "3px solid var(--color-primary)" : "3px solid transparent",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: "var(--font-size-xs, 12px)",
                      fontWeight: isActive ? 600 : 400,
                      transition: "background-color 0.15s ease",
                      width: "100%",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = "transparent";
                      }
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--spacing-2)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      <span style={{ fontSize: "14px", flexShrink: 0 }}>{item.icon}</span>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {item.label}
                      </span>
                    </div>

                    {item.badge && (
                      <span
                        style={{
                          fontSize: "0.625rem",
                          padding: "1px 5px",
                          borderRadius: "var(--radius-full)",
                          backgroundColor: "var(--color-primary-bg)",
                          color: "var(--color-primary)",
                          fontWeight: 600,
                          flexShrink: 0,
                          marginLeft: "4px",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))
        )}
      </div>
    </nav>
  );
};
