import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { WorkspaceLayout, LayoutTab, GridPosition } from "./types";
import { loadLayout, saveLayout, resetLayout, DEFAULT_LAYOUT } from "./storage";

interface LayoutContextType {
  layout: WorkspaceLayout;
  activeTab: LayoutTab;
  setActiveTab: (tabId: string) => void;
  addTab: (name: string) => void;
  removeTab: (tabId: string) => void;
  renameTab: (tabId: string, name: string) => void;
  addWidget: (tabId: string, widgetId: string, position?: GridPosition) => void;
  removeWidget: (tabId: string, instanceId: string) => void;
  updateWidgetPosition: (tabId: string, instanceId: string, position: Partial<GridPosition>) => void;
  updateWidgetSettings: (tabId: string, instanceId: string, settings: Record<string, unknown>) => void;
  resetToDefault: () => void;
}

const LayoutContext = createContext<LayoutContextType | undefined>(undefined);

export const LayoutProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [layout, setLayout] = useState<WorkspaceLayout>(() => loadLayout());

  useEffect(() => {
    saveLayout(layout);
  }, [layout]);

  const activeTab = layout.tabs.find((t) => t.id === layout.activeTabId) || layout.tabs[0] || DEFAULT_LAYOUT.tabs[0];

  const setActiveTab = (tabId: string) => {
    if (layout.tabs.some((t) => t.id === tabId)) {
      setLayout((prev) => ({ ...prev, activeTabId: tabId }));
    }
  };

  const addTab = (name: string) => {
    const newTabId = `tab-${Date.now()}`;
    const newTab: LayoutTab = {
      id: newTabId,
      name: name.trim() || `Workspace ${layout.tabs.length + 1}`,
      widgets: [],
    };
    setLayout((prev) => ({
      ...prev,
      activeTabId: newTabId,
      tabs: [...prev.tabs, newTab],
    }));
  };

  const removeTab = (tabId: string) => {
    if (layout.tabs.length <= 1) return; // Prevent deleting last tab
    const nextTabs = layout.tabs.filter((t) => t.id !== tabId);
    const nextActiveId = layout.activeTabId === tabId ? nextTabs[0].id : layout.activeTabId;
    setLayout({
      ...layout,
      activeTabId: nextActiveId,
      tabs: nextTabs,
    });
  };

  const renameTab = (tabId: string, name: string) => {
    setLayout((prev) => ({
      ...prev,
      tabs: prev.tabs.map((t) => (t.id === tabId ? { ...t, name } : t)),
    }));
  };

  const addWidget = (tabId: string, widgetId: string, position?: GridPosition) => {
    const instanceId = `inst-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const newPosition: GridPosition = position || {
      x: 0,
      y: 0,
      w: 4,
      h: 3,
    };

    setLayout((prev) => ({
      ...prev,
      tabs: prev.tabs.map((t) => {
        if (t.id !== tabId) return t;
        return {
          ...t,
          widgets: [
            ...t.widgets,
            {
              instanceId,
              widgetId,
              position: newPosition,
            },
          ],
        };
      }),
    }));
  };

  const removeWidget = (tabId: string, instanceId: string) => {
    setLayout((prev) => ({
      ...prev,
      tabs: prev.tabs.map((t) => {
        if (t.id !== tabId) return t;
        return {
          ...t,
          widgets: t.widgets.filter((w) => w.instanceId !== instanceId),
        };
      }),
    }));
  };

  const updateWidgetPosition = (tabId: string, instanceId: string, position: Partial<GridPosition>) => {
    setLayout((prev) => ({
      ...prev,
      tabs: prev.tabs.map((t) => {
        if (t.id !== tabId) return t;
        return {
          ...t,
          widgets: t.widgets.map((w) => {
            if (w.instanceId !== instanceId) return w;
            return {
              ...w,
              position: { ...w.position, ...position },
            };
          }),
        };
      }),
    }));
  };

  const updateWidgetSettings = (tabId: string, instanceId: string, settings: Record<string, unknown>) => {
    setLayout((prev) => ({
      ...prev,
      tabs: prev.tabs.map((t) => {
        if (t.id !== tabId) return t;
        return {
          ...t,
          widgets: t.widgets.map((w) => {
            if (w.instanceId !== instanceId) return w;
            return {
              ...w,
              settings: { ...w.settings, ...settings },
            };
          }),
        };
      }),
    }));
  };

  const resetToDefault = () => {
    const def = resetLayout();
    setLayout(def);
  };

  return (
    <LayoutContext.Provider
      value={{
        layout,
        activeTab,
        setActiveTab,
        addTab,
        removeTab,
        renameTab,
        addWidget,
        removeWidget,
        updateWidgetPosition,
        updateWidgetSettings,
        resetToDefault,
      }}
    >
      {children}
    </LayoutContext.Provider>
  );
};

export const useLayout = (): LayoutContextType => {
  const context = useContext(LayoutContext);
  if (!context) {
    throw new Error("useLayout must be used within a LayoutProvider");
  }
  return context;
};
