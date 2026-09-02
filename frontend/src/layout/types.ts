export interface GridPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutWidgetItem {
  instanceId: string;
  widgetId: string;
  position: GridPosition;
  settings?: Record<string, unknown>;
}

export interface LayoutTab {
  id: string;
  name: string;
  icon?: string;
  widgets: LayoutWidgetItem[];
}

export interface WorkspaceLayout {
  version: number;
  activeTabId: string;
  tabs: LayoutTab[];
}
