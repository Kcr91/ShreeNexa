import { WorkspaceLayout } from "./types";

export const LAYOUT_STORAGE_KEY = "shreenexa_terminal_layout_v1";

export const DEFAULT_LAYOUT: WorkspaceLayout = {
  version: 1,
  activeTabId: "tab-overview",
  tabs: [
    {
      id: "tab-overview",
      name: "Main Overview",
      icon: "📊",
      widgets: [
        {
          instanceId: "inst-watchlist",
          widgetId: "watchlist",
          position: { x: 0, y: 0, w: 7, h: 5 },
          settings: { universeName: "NIFTY 50", refreshIntervalSec: 1 },
        },
        {
          instanceId: "inst-backtest-summary",
          widgetId: "backtest-summary",
          position: { x: 7, y: 0, w: 5, h: 5 },
          settings: { strategyName: "NIFTY Alpha Trend", displayMode: "detailed" },
        },
      ],
    },
    {
      id: "tab-lab",
      name: "Strategy Lab",
      icon: "🧪",
      widgets: [
        {
          instanceId: "inst-lab-backtest",
          widgetId: "backtest-summary",
          position: { x: 0, y: 0, w: 6, h: 4 },
          settings: { strategyName: "BankNifty Multi-Leg Strangle", displayMode: "detailed" },
        },
      ],
    },
  ],
};

export function validateLayout(data: unknown): data is WorkspaceLayout {
  if (!data || typeof data !== "object") return false;

  const candidate = data as Partial<WorkspaceLayout>;
  if (typeof candidate.version !== "number" || candidate.version !== 1) return false;
  if (typeof candidate.activeTabId !== "string") return false;
  if (!Array.isArray(candidate.tabs) || candidate.tabs.length === 0) return false;

  for (const tab of candidate.tabs) {
    if (!tab || typeof tab !== "object") return false;
    if (typeof tab.id !== "string" || typeof tab.name !== "string") return false;
    if (!Array.isArray(tab.widgets)) return false;

    for (const w of tab.widgets) {
      if (!w || typeof w !== "object") return false;
      if (typeof w.instanceId !== "string" || typeof w.widgetId !== "string") return false;
      if (!w.position || typeof w.position !== "object") return false;
      const pos = w.position;
      if (
        typeof pos.x !== "number" ||
        typeof pos.y !== "number" ||
        typeof pos.w !== "number" ||
        typeof pos.h !== "number"
      ) {
        return false;
      }
    }
  }

  // Ensure activeTabId points to an existing tab
  const hasActiveTab = candidate.tabs.some((t) => t.id === candidate.activeTabId);
  if (!hasActiveTab) {
    candidate.activeTabId = candidate.tabs[0].id;
  }

  return true;
}

export function loadLayout(): WorkspaceLayout {
  try {
    const raw = localStorage.getItem(LAYOUT_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_LAYOUT;
    }
    const parsed = JSON.parse(raw);
    if (validateLayout(parsed)) {
      return parsed;
    }
    console.warn("Stored workspace layout was invalid, falling back to default layout.");
    return DEFAULT_LAYOUT;
  } catch (err) {
    console.warn("Failed to load stored workspace layout, falling back to default:", err);
    return DEFAULT_LAYOUT;
  }
}

export function saveLayout(layout: WorkspaceLayout): void {
  try {
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(layout));
  } catch (err) {
    console.error("Failed to save workspace layout to localStorage:", err);
  }
}

export function resetLayout(): WorkspaceLayout {
  try {
    localStorage.removeItem(LAYOUT_STORAGE_KEY);
  } catch (err) {
    console.error("Failed to reset workspace layout:", err);
  }
  return DEFAULT_LAYOUT;
}
