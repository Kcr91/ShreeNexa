import React from "react";
import { useLayout } from "./LayoutContext";

interface Props {
  onOpenPalette: () => void;
  onOpenTemplates: () => void;
  onOpenExportImport: () => void;
}

export const TabBar: React.FC<Props> = ({
  onOpenPalette,
  onOpenTemplates,
  onOpenExportImport,
}) => {
  const { layout, activeTab, setActiveTab, addTab, removeTab, resetToDefault } = useLayout();

  const handleAddTab = () => {
    const tabName = prompt("Enter new workspace tab name:", `Workspace ${layout.tabs.length + 1}`);
    if (tabName !== null) {
      addTab(tabName);
    }
  };

  return (
    <div
      role="tablist"
      aria-label="Workspace tabs"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border-default)",
        padding: "0 var(--spacing-4)",
        userSelect: "none",
        minHeight: "40px",
      }}
    >
      {/* Tabs list */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)", overflowX: "auto" }}>
        {layout.tabs.map((tab, idx) => {
          const isActive = tab.id === activeTab.id;
          return (
            <div
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--spacing-2)",
                padding: "var(--spacing-2) var(--spacing-3)",
                backgroundColor: isActive ? "var(--bg-surface)" : "transparent",
                color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                borderTopLeftRadius: "var(--radius-sm)",
                borderTopRightRadius: "var(--radius-sm)",
                borderBottom: isActive ? "2px solid var(--color-primary)" : "2px solid transparent",
                cursor: "pointer",
                fontSize: "var(--font-size-xs)",
                fontWeight: isActive ? 600 : 400,
                transition: "all 0.15s ease",
              }}
            >
              <span style={{ opacity: 0.5, fontSize: "0.625rem" }}>{idx + 1}</span>
              <span>{tab.icon || "📁"}</span>
              <span>{tab.name}</span>
              {layout.tabs.length > 1 && (
                <button
                  type="button"
                  aria-label={`Close ${tab.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    removeTab(tab.id);
                  }}
                  style={{
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    fontSize: "0.6875rem",
                    color: "var(--text-muted)",
                    padding: "0 2px",
                  }}
                >
                  ✕
                </button>
              )}
            </div>
          );
        })}

        <button
          type="button"
          aria-label="Add Tab"
          onClick={handleAddTab}
          style={{
            background: "transparent",
            border: "1px dashed var(--border-default)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-muted)",
            cursor: "pointer",
            fontSize: "var(--font-size-xs)",
            padding: "var(--spacing-1) var(--spacing-2)",
            marginLeft: "var(--spacing-2)",
          }}
        >
          + Tab
        </button>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
        <button
          type="button"
          aria-label="Workspace Templates"
          onClick={onOpenTemplates}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          📋 Templates
        </button>

        <button
          type="button"
          aria-label="Export Import Layout"
          onClick={onOpenExportImport}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "var(--bg-surface)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          💾 JSON
        </button>

        <button
          type="button"
          aria-label="Add Widget"
          onClick={onOpenPalette}
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
          + Add Widget
        </button>

        <button
          type="button"
          aria-label="Reset Workspace Layout"
          onClick={resetToDefault}
          style={{
            padding: "var(--spacing-1) var(--spacing-2)",
            backgroundColor: "transparent",
            color: "var(--text-muted)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
            cursor: "pointer",
          }}
        >
          ↺ Reset
        </button>
      </div>
    </div>
  );
};
