import React, { useState } from "react";
import { widgetRegistry } from "./registry";
import { WidgetDefinition } from "./types";

interface Props {
  onAddWidget: (widgetId: string) => void;
  onClose?: () => void;
}

export const WidgetPalette: React.FC<Props> = ({ onAddWidget, onClose }) => {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const allWidgets = widgetRegistry.getAll();

  const filteredWidgets = allWidgets.filter((w) => {
    const matchesCategory = selectedCategory === "all" || w.category === selectedCategory;
    const matchesSearch =
      w.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categories: { id: string; label: string }[] = [
    { id: "all", label: "All Widgets" },
    { id: "analytics", label: "Analytics & Strategy" },
    { id: "watchlist", label: "Watchlists" },
    { id: "chart", label: "Charts" },
    { id: "system", label: "System & Feed" },
    { id: "custom", label: "Custom" },
  ];

  return (
    <div
      role="dialog"
      aria-label="Widget Palette"
      style={{
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--bg-secondary)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--spacing-4)",
        maxHeight: "600px",
        width: "500px",
        gap: "var(--spacing-4)",
        boxShadow: "var(--shadow-lg)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: "bold" }}>Widget Palette</h3>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
            Select a widget to add to your workspace.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            aria-label="Close Palette"
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--font-size-base)",
              color: "var(--text-muted)",
            }}
          >
            ✕
          </button>
        )}
      </div>

      <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
        <input
          type="text"
          placeholder="Search widgets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Search widgets"
          style={{
            flex: 1,
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-2) var(--spacing-3)",
            fontSize: "var(--font-size-sm)",
            color: "var(--text-primary)",
          }}
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          aria-label="Filter by category"
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--spacing-2)",
            fontSize: "var(--font-size-sm)",
            color: "var(--text-primary)",
          }}
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "var(--spacing-2)",
          paddingRight: "var(--spacing-1)",
        }}
      >
        {filteredWidgets.length === 0 ? (
          <div style={{ textAlign: "center", padding: "var(--spacing-6)", color: "var(--text-muted)" }}>
            No widgets match your search criteria.
          </div>
        ) : (
          filteredWidgets.map((widget: WidgetDefinition) => (
            <div
              key={widget.id}
              data-testid={`palette-item-${widget.id}`}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "var(--spacing-3)",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
                <span style={{ fontSize: "var(--font-size-xl)" }}>{widget.icon}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "var(--font-size-sm)" }}>{widget.title}</div>
                  <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>{widget.description}</div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onAddWidget(widget.id)}
                style={{
                  padding: "var(--spacing-1) var(--spacing-3)",
                  backgroundColor: "var(--color-primary)",
                  color: "var(--text-inverse)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-xs)",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                + Add
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
