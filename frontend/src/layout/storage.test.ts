import { describe, expect, it, beforeEach } from "vitest";
import {
  loadLayout,
  saveLayout,
  resetLayout,
  validateLayout,
  DEFAULT_LAYOUT,
  LAYOUT_STORAGE_KEY,
} from "./storage";
import { WorkspaceLayout } from "./types";

describe("Workspace Layout Storage and Persistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("loads DEFAULT_LAYOUT when localStorage is empty", () => {
    const layout = loadLayout();
    expect(layout.version).toBe(1);
    expect(layout.tabs).toHaveLength(2);
    expect(layout.tabs[0].name).toBe("Main Overview");
  });

  it("saves and reloads a valid custom workspace layout", () => {
    const customLayout: WorkspaceLayout = {
      version: 1,
      activeTabId: "custom-tab-1",
      tabs: [
        {
          id: "custom-tab-1",
          name: "My Custom Grid",
          icon: "🚀",
          widgets: [
            {
              instanceId: "w1",
              widgetId: "market-clock",
              position: { x: 0, y: 0, w: 6, h: 4 },
              settings: { showSeconds: false },
            },
          ],
        },
      ],
    };

    saveLayout(customLayout);
    const restored = loadLayout();

    expect(restored.activeTabId).toBe("custom-tab-1");
    expect(restored.tabs).toHaveLength(1);
    expect(restored.tabs[0].name).toBe("My Custom Grid");
    expect(restored.tabs[0].widgets[0].settings?.showSeconds).toBe(false);
  });

  it("gracefully falls back to DEFAULT_LAYOUT when storage has corrupt JSON", () => {
    localStorage.setItem(LAYOUT_STORAGE_KEY, "{ invalid json corrupt string");

    const layout = loadLayout();
    expect(layout.version).toBe(DEFAULT_LAYOUT.version);
    expect(layout.tabs).toHaveLength(DEFAULT_LAYOUT.tabs.length);
  });

  it("gracefully falls back to DEFAULT_LAYOUT when storage has schema-invalid structure", () => {
    // Missing required fields
    const invalidSchema = {
      version: 999, // invalid version
      tabs: "not-an-array",
    };
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(invalidSchema));

    expect(validateLayout(invalidSchema)).toBe(false);
    const layout = loadLayout();
    expect(layout.version).toBe(1);
    expect(layout.tabs[0].id).toBe("tab-overview");
  });

  it("resetLayout removes item from localStorage and returns DEFAULT_LAYOUT", () => {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify({ version: 1, activeTabId: "x", tabs: [] }));
    const reset = resetLayout();

    expect(localStorage.getItem(LAYOUT_STORAGE_KEY)).toBeNull();
    expect(reset.tabs).toHaveLength(DEFAULT_LAYOUT.tabs.length);
  });
});
