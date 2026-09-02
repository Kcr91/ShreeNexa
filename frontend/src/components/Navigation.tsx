import React from "react";

export type ActiveRoute = "dashboard" | "research" | "screener" | "pnl" | "settings";

interface NavItem {
  id: ActiveRoute;
  label: string;
  badge?: string;
  icon: string;
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "research", label: "Strategy Lab", icon: "🧪", badge: "Engine" },
  { id: "screener", label: "PIT Screener", icon: "🔍" },
  { id: "pnl", label: "Daily P&L / TWR", icon: "📈" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

interface Props {
  activeRoute: ActiveRoute;
  onRouteChange: (route: ActiveRoute) => void;
}

export const Navigation: React.FC<Props> = ({ activeRoute, onRouteChange }) => {
  return (
    <nav
      role="navigation"
      aria-label="Terminal primary navigation"
      style={{
        width: "var(--nav-width)",
        backgroundColor: "var(--bg-secondary)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        padding: "var(--spacing-3) 0",
        gap: "var(--spacing-1)",
        userSelect: "none",
      }}
    >
      <div
        style={{
          padding: "0 var(--spacing-4)",
          marginBottom: "var(--spacing-2)",
          fontSize: "var(--font-size-xs)",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "1px",
          fontWeight: "bold",
        }}
      >
        Navigation
      </div>

      {navItems.map((item) => {
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
              fontSize: "var(--font-size-sm)",
              fontWeight: isActive ? 600 : 400,
              transition: "background-color 0.15s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
              <span style={{ fontSize: "var(--font-size-base)" }}>{item.icon}</span>
              <span>{item.label}</span>
            </div>
            {item.badge && (
              <span
                style={{
                  fontSize: "0.6875rem",
                  padding: "1px 6px",
                  borderRadius: "var(--radius-full)",
                  backgroundColor: "var(--color-primary-bg)",
                  color: "var(--color-primary)",
                  fontWeight: 600,
                }}
              >
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
};
