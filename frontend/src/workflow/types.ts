import { PositionItem, ActiveOrderItem } from "../blotter/types";

export type WorkflowStep =
  | "FEED_INGEST"
  | "INDICATOR_EVAL"
  | "RULE_TRIGGER"
  | "ORDER_DISPATCH"
  | "BLOTTER_UPDATE"
  | "PNL_RECONCILE";

export interface WorkflowEvent {
  step: WorkflowStep;
  timestamp: number;
  symbol: string;
  data: Record<string, unknown>;
  status: "SUCCESS" | "FAILED" | "PENDING";
}

export interface WorkflowEvaluationResult {
  signal: "BUY" | "SELL" | "HOLD";
  fastEma: number;
  slowEma: number;
  rsi: number;
  generatedOrder?: ActiveOrderItem;
  updatedPositions: PositionItem[];
  totalUnrealizedPnl: number;
  events: WorkflowEvent[];
}
