import React, { useState, useMemo } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";
import {
  MarketplaceStrategy,
  MarketplaceWidgetSettings,
  StrategyCategory,
} from "../../marketplace/types";
import { MARKETPLACE_CATALOG } from "../../marketplace/catalog";
import { TearSheetModal } from "../../marketplace/TearSheetModal";
import { useNotifications } from "../../notifications/NotificationContext";

export const StrategyMarketplaceWidget: React.FC<
  WidgetComponentProps<MarketplaceWidgetSettings>
> = ({ settings }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<StrategyCategory>(
    (settings?.defaultCategory as StrategyCategory) || "ALL"
  );
  const [selectedAssetClass, setSelectedAssetClass] = useState<string>(
    settings?.defaultAssetClass || "ALL"
  );
  const [selectedStrategyForPreview, setSelectedStrategyForPreview] =
    useState<MarketplaceStrategy | null>(null);
  const [clonedSuccessId, setClonedSuccessId] = useState<string | null>(null);

  const { sendNotification } = useNotifications();

  const filteredStrategies = useMemo(() => {
    return MARKETPLACE_CATALOG.filter((s) => {
      // Category filter
      if (selectedCategory !== "ALL" && s.category !== selectedCategory) {
        return false;
      }
      // Asset class filter
      if (selectedAssetClass !== "ALL" && s.assetClass !== selectedAssetClass) {
        return false;
      }
      // Search query
      if (searchQuery.trim() !== "") {
        const q = searchQuery.toLowerCase();
        const matchesTitle = s.title.toLowerCase().includes(q);
        const matchesAuthor = s.author.name.toLowerCase().includes(q);
        const matchesTags = s.tags.some((t) => t.toLowerCase().includes(q));
        if (!matchesTitle && !matchesAuthor && !matchesTags) {
          return false;
        }
      }
      return true;
    });
  }, [searchQuery, selectedCategory, selectedAssetClass]);

  const handleCloneStrategy = (strategy: MarketplaceStrategy) => {
    // Clone StrategyIR into localStorage or workspace memory
    try {
      localStorage.setItem("shreenexa_active_strategy_ir", JSON.stringify(strategy.strategyIR));
    } catch {
      // fallback
    }

    setClonedSuccessId(strategy.id);
    setTimeout(() => setClonedSuccessId(null), 3000);

    sendNotification({
      title: "Strategy Cloned",
      message: `Cloned '${strategy.title}' into your strategy builder workspace.`,
      severity: "SUCCESS",
      category: "SYSTEM",
    });
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", padding: "var(--spacing-2)", gap: "var(--spacing-2)" }}>
      {/* Top Search & Filter Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "var(--bg-surface)",
          padding: "var(--spacing-2) var(--spacing-3)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          gap: "var(--spacing-2)",
          fontSize: "var(--font-size-xs)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)", flex: 1 }}>
          <input
            aria-label="Search Marketplace"
            type="text"
            placeholder="Search quant strategies, authors, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              flex: 1,
              backgroundColor: "var(--bg-active)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              fontSize: "var(--font-size-xs)",
            }}
          />
        </div>

        {/* Asset Class Filter */}
        <div style={{ display: "flex", gap: "2px" }}>
          {["ALL", "EQUITY", "OPTIONS", "FUTURES"].map((ac) => (
            <button
              key={ac}
              type="button"
              onClick={() => setSelectedAssetClass(ac)}
              style={{
                padding: "2px 8px",
                backgroundColor: selectedAssetClass === ac ? "var(--color-primary)" : "transparent",
                color: selectedAssetClass === ac ? "var(--text-inverse)" : "var(--text-muted)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.6875rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {ac}
            </button>
          ))}
        </div>
      </div>

      {/* Category Pills Strip */}
      <div style={{ display: "flex", gap: "var(--spacing-1)", overflowX: "auto", paddingBottom: "2px" }}>
        {[
          { id: "ALL", label: "All Categories" },
          { id: "OPTIONS_INCOME", label: "Options Income" },
          { id: "MOMENTUM", label: "Momentum" },
          { id: "BREAKOUT", label: "Breakout" },
          { id: "VOLATILITY", label: "Volatility" },
        ].map((cat) => (
          <button
            key={cat.id}
            type="button"
            onClick={() => setSelectedCategory(cat.id as StrategyCategory)}
            style={{
              padding: "2px 10px",
              backgroundColor: selectedCategory === cat.id ? "var(--bg-active)" : "transparent",
              color: selectedCategory === cat.id ? "var(--color-primary)" : "var(--text-muted)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "12px",
              fontSize: "var(--font-size-xs)",
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Strategy Card Grid */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: "var(--spacing-2)",
          alignContent: "start",
        }}
      >
        {filteredStrategies.map((strategy) => (
          <div
            key={strategy.id}
            data-testid={`strategy-card-${strategy.id}`}
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "var(--spacing-3)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              gap: "var(--spacing-2)",
            }}
          >
            {/* Card Header: Author & Asset Badge */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>{strategy.author.avatar}</span>
                  <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {strategy.author.name}
                  </span>
                  {strategy.author.verified && <span title="Verified Creator" style={{ color: "var(--color-primary)", fontSize: "0.625rem" }}>✓</span>}
                </div>
                <span
                  style={{
                    padding: "1px 6px",
                    borderRadius: "3px",
                    backgroundColor: "var(--bg-active)",
                    color: "var(--color-primary)",
                    fontWeight: 700,
                    fontSize: "0.625rem",
                  }}
                >
                  {strategy.assetClass}
                </span>
              </div>

              {/* Title & Description */}
              <strong style={{ fontSize: "var(--font-size-sm)", color: "var(--text-primary)", display: "block" }}>
                {strategy.title}
              </strong>
              <p
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--text-secondary)",
                  margin: "4px 0 8px 0",
                  lineHeight: "1.3",
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {strategy.description}
              </p>

              {/* Performance Metrics Bar */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  backgroundColor: "var(--bg-active)",
                  padding: "6px",
                  borderRadius: "var(--radius-sm)",
                  textAlign: "center",
                  fontSize: "0.625rem",
                }}
              >
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>CAGR</span>
                  <strong style={{ color: "var(--color-up)" }}>+{strategy.performance.cagrPct}%</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Sharpe</span>
                  <strong style={{ color: "var(--color-primary)" }}>{strategy.performance.sharpeRatio}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Max DD</span>
                  <strong style={{ color: "var(--color-down)" }}>-{strategy.performance.maxDrawdownPct}%</strong>
                </div>
              </div>
            </div>

            {/* Card Actions */}
            <div style={{ display: "flex", gap: "var(--spacing-1)", marginTop: "4px" }}>
              <button
                type="button"
                onClick={() => setSelectedStrategyForPreview(strategy)}
                style={{
                  flex: 1,
                  padding: "4px 8px",
                  backgroundColor: "transparent",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.6875rem",
                  cursor: "pointer",
                }}
              >
                Preview Tear Sheet
              </button>

              <button
                type="button"
                data-testid={`clone-btn-${strategy.id}`}
                onClick={() => handleCloneStrategy(strategy)}
                style={{
                  flex: 1,
                  padding: "4px 8px",
                  backgroundColor: clonedSuccessId === strategy.id ? "var(--color-up)" : "var(--color-primary)",
                  color: "var(--text-inverse)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.6875rem",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {clonedSuccessId === strategy.id ? "✓ Cloned!" : "⚡ Clone"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Tear Sheet Modal */}
      {selectedStrategyForPreview && (
        <TearSheetModal
          strategy={selectedStrategyForPreview}
          isOpen={true}
          onClose={() => setSelectedStrategyForPreview(null)}
          onClone={handleCloneStrategy}
        />
      )}
    </div>
  );
};

export const strategyMarketplaceDefinition: WidgetDefinition<MarketplaceWidgetSettings> = {
  id: "strategy-marketplace",
  title: "Strategy Marketplace",
  description: "Browse curated quantitative strategy library, preview backtest tear sheets, and clone to workspace.",
  category: "analytics",
  icon: "🏪",
  defaultWidth: 720,
  defaultHeight: 480,
  schema: {
    fields: [
      {
        name: "defaultCategory",
        label: "Default Category",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Categories", value: "ALL" },
          { label: "Options Income", value: "OPTIONS_INCOME" },
          { label: "Momentum", value: "MOMENTUM" },
          { label: "Breakout", value: "BREAKOUT" },
          { label: "Volatility", value: "VOLATILITY" },
        ],
      },
      {
        name: "defaultAssetClass",
        label: "Default Asset Class",
        type: "select",
        default: "ALL",
        options: [
          { label: "All Assets", value: "ALL" },
          { label: "Equity", value: "EQUITY" },
          { label: "Options", value: "OPTIONS" },
          { label: "Futures", value: "FUTURES" },
        ],
      },
    ],
  },
  component: StrategyMarketplaceWidget,
};
