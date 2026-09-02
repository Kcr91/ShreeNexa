import React, { useState } from "react";
import { useLayout } from "./LayoutContext";
import { TabBar } from "./TabBar";
import { GridContainer } from "./GridContainer";
import { WidgetPalette } from "../widgets/WidgetPalette";

export const LayoutManager: React.FC = () => {
  const { activeTab, addWidget } = useLayout();
  const [isPaletteOpen, setIsPaletteOpen] = useState<boolean>(false);

  const handleAddWidget = (widgetId: string) => {
    addWidget(activeTab.id, widgetId);
    setIsPaletteOpen(false);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <TabBar onOpenPalette={() => setIsPaletteOpen(true)} />
      <div style={{ flex: 1, overflow: "hidden" }}>
        <GridContainer />
      </div>

      {isPaletteOpen && (
        <div
          role="presentation"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.65)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
          onClick={() => setIsPaletteOpen(false)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <WidgetPalette
              onAddWidget={handleAddWidget}
              onClose={() => setIsPaletteOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
};
