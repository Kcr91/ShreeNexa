import React, { useState } from "react";
import { useLayout } from "./LayoutContext";
import { TabBar } from "./TabBar";
import { GridContainer } from "./GridContainer";
import { WidgetPalette } from "../widgets/WidgetPalette";
import { TemplateModal } from "./TemplateModal";
import { ExportImportModal } from "./ExportImportModal";
import { useWorkspaceHotkeys } from "./hotkeys";
import { WorkspaceLayout } from "./types";

export const LayoutManager: React.FC = () => {
  const { layout, activeTab, setActiveTab, addWidget, applyLayout } = useLayout();
  const [isPaletteOpen, setIsPaletteOpen] = useState<boolean>(false);
  const [isTemplateOpen, setIsTemplateOpen] = useState<boolean>(false);
  const [isExportImportOpen, setIsExportImportOpen] = useState<boolean>(false);

  // Hook up global hotkeys
  useWorkspaceHotkeys({
    tabIds: layout.tabs.map((t) => t.id),
    onSelectTab: (tabId) => setActiveTab(tabId),
    onOpenTemplates: () => setIsTemplateOpen(true),
    onOpenPalette: () => setIsPaletteOpen(true),
    onOpenExportImport: () => setIsExportImportOpen(true),
  });

  const handleAddWidget = (widgetId: string) => {
    addWidget(activeTab.id, widgetId);
    setIsPaletteOpen(false);
  };

  const handleApplyTemplate = (newLayout: WorkspaceLayout) => {
    applyLayout(newLayout);
    setIsTemplateOpen(false);
  };

  const handleImportLayout = (newLayout: WorkspaceLayout) => {
    applyLayout(newLayout);
    setIsExportImportOpen(false);
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
      <TabBar
        onOpenPalette={() => setIsPaletteOpen(true)}
        onOpenTemplates={() => setIsTemplateOpen(true)}
        onOpenExportImport={() => setIsExportImportOpen(true)}
      />
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

      <TemplateModal
        isOpen={isTemplateOpen}
        onClose={() => setIsTemplateOpen(false)}
        onApplyTemplate={handleApplyTemplate}
      />

      <ExportImportModal
        isOpen={isExportImportOpen}
        onClose={() => setIsExportImportOpen(false)}
        currentLayout={layout}
        onImportLayout={handleImportLayout}
      />
    </div>
  );
};
