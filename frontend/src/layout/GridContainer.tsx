import React from "react";
import { useLayout } from "./LayoutContext";
import { WidgetFrame } from "../widgets/WidgetFrame";

export const GridContainer: React.FC = () => {
  const { activeTab, removeWidget, updateWidgetSettings } = useLayout();

  if (activeTab.widgets.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          padding: "var(--spacing-8)",
          color: "var(--text-muted)",
        }}
      >
        <div style={{ fontSize: "var(--font-size-2xl)", marginBottom: "var(--spacing-2)" }}>📋</div>
        <div style={{ fontSize: "var(--font-size-base)", fontWeight: 600 }}>This workspace tab is empty</div>
        <p style={{ fontSize: "var(--font-size-xs)", marginTop: "var(--spacing-1)" }}>
          Click <strong>+ Add Widget</strong> above to add charts, watchlists, or strategy performance widgets.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
        gap: "var(--spacing-4)",
        padding: "var(--spacing-4)",
        overflowY: "auto",
        height: "100%",
      }}
    >
      {activeTab.widgets.map((item) => (
        <div
          key={item.instanceId}
          data-testid={`grid-widget-${item.instanceId}`}
          style={{
            minHeight: "260px",
            height: "100%",
          }}
        >
          <WidgetFrame
            instanceId={item.instanceId}
            widgetId={item.widgetId}
            settings={item.settings}
            onClose={(id) => removeWidget(activeTab.id, id)}
            onUpdateSettings={(id, newSettings) => updateWidgetSettings(activeTab.id, id, newSettings)}
          />
        </div>
      ))}
    </div>
  );
};
