export interface BarData {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export type IndicatorPaneType = "overlay" | "subpane";

export interface ChartIndicatorConfig {
  id: string;
  name: string;
  type: "SMA" | "EMA" | "RSI" | "MACD" | "VWAP";
  pane: IndicatorPaneType;
  color: string;
  params: Record<string, number | string>;
}

export type DrawingToolType = "trendline" | "horizontal" | "rectangle";

export interface ChartDrawingPoint {
  time: string | number;
  price: number;
}

export interface ChartDrawing {
  id: string;
  tool: DrawingToolType;
  points: ChartDrawingPoint[];
  color?: string;
  lineWidth?: number;
}

export interface SessionBreak {
  time: string | number;
  sessionName: string;
  date: string;
}

export interface ChartWidgetSettings {
  symbol: string;
  timeframe: "1m" | "5m" | "15m" | "1h" | "1d";
  showSessionBreaks: boolean;
  showVolume: boolean;
}
