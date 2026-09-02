import { WorkflowEvaluationResult, WorkflowEvent } from "./types";
import { PositionItem, ActiveOrderItem } from "../blotter/types";
import { computePositionPnl } from "../blotter/pnl";

export class TerminalWorkflowEngine {
  public symbol: string;
  public priceHistory: number[] = [];
  public fastPeriod: number;
  public slowPeriod: number;
  public rsiPeriod: number;
  public positions: PositionItem[] = [];
  public orders: ActiveOrderItem[] = [];
  public events: WorkflowEvent[] = [];

  private prevFastEma: number | null = null;
  private prevSlowEma: number | null = null;

  constructor(
    symbol: string = "RELIANCE",
    fastPeriod: number = 9,
    slowPeriod: number = 21,
    rsiPeriod: number = 14
  ) {
    this.symbol = symbol;
    this.fastPeriod = fastPeriod;
    this.slowPeriod = slowPeriod;
    this.rsiPeriod = rsiPeriod;
  }

  public processTick(price: number, timestamp: number = Date.now()): WorkflowEvaluationResult {
    const events: WorkflowEvent[] = [];

    // Step 1: FEED_INGEST
    this.priceHistory.push(price);
    events.push({
      step: "FEED_INGEST",
      timestamp,
      symbol: this.symbol,
      data: { price, totalTicks: this.priceHistory.length },
      status: "SUCCESS",
    });

    // Step 2: INDICATOR_EVAL
    const fastEma = this.calculateEma(this.priceHistory, this.fastPeriod);
    const slowEma = this.calculateEma(this.priceHistory, this.slowPeriod);
    const rsi = this.calculateRsi(this.priceHistory, this.rsiPeriod);

    events.push({
      step: "INDICATOR_EVAL",
      timestamp,
      symbol: this.symbol,
      data: { fastEma, slowEma, rsi },
      status: "SUCCESS",
    });

    // Step 3: RULE_TRIGGER
    let signal: "BUY" | "SELL" | "HOLD" = "HOLD";

    if (
      this.prevFastEma !== null &&
      this.prevSlowEma !== null &&
      this.prevFastEma <= this.prevSlowEma &&
      fastEma > slowEma &&
      rsi >= 50
    ) {
      signal = "BUY";
    } else if (
      this.prevFastEma !== null &&
      this.prevSlowEma !== null &&
      this.prevFastEma >= this.prevSlowEma &&
      fastEma < slowEma &&
      this.positions.some((p) => p.symbol === this.symbol && p.quantity > 0)
    ) {
      signal = "SELL";
    }

    this.prevFastEma = fastEma;
    this.prevSlowEma = slowEma;

    events.push({
      step: "RULE_TRIGGER",
      timestamp,
      symbol: this.symbol,
      data: { signal, condition: signal !== "HOLD" ? "EMA_CROSSOVER" : "NONE" },
      status: "SUCCESS",
    });

    let generatedOrder: ActiveOrderItem | undefined;

    // Step 4: ORDER_DISPATCH
    if (signal === "BUY" && !this.positions.some((p) => p.symbol === this.symbol && p.quantity > 0)) {
      generatedOrder = {
        orderId: `ord-wf-${timestamp}-${Math.floor(Math.random() * 1000)}`,
        symbol: this.symbol,
        product: "CNC",
        orderType: "MARKET",
        side: "BUY",
        quantity: 25,
        filledQuantity: 25,
        price,
        status: "FILLED",
        placedAt: new Date(timestamp).toLocaleTimeString(),
      };

      this.orders.push(generatedOrder);

      events.push({
        step: "ORDER_DISPATCH",
        timestamp,
        symbol: this.symbol,
        data: { orderId: generatedOrder.orderId, quantity: 25, price },
        status: "SUCCESS",
      });

      // Step 5: BLOTTER_UPDATE
      const newPosition: PositionItem = {
        symbol: this.symbol,
        product: "CNC",
        quantity: 25,
        buyAvgPrice: price,
        ltp: price,
        dayChange: 0,
        dayChangePct: 0,
        unrealizedPnl: 0,
        realizedPnl: 0,
        totalPnl: 0,
      };

      this.positions = [...this.positions.filter((p) => p.symbol !== this.symbol), newPosition];

      events.push({
        step: "BLOTTER_UPDATE",
        timestamp,
        symbol: this.symbol,
        data: { symbol: newPosition.symbol, qty: 25, avgPrice: price },
        status: "SUCCESS",
      });
    }

    // Step 6: PNL_RECONCILE
    this.positions = this.positions.map((pos) => {
      if (pos.symbol === this.symbol) {
        return computePositionPnl(pos, price);
      }
      return pos;
    });

    const totalUnrealizedPnl = this.positions.reduce((acc, p) => acc + p.unrealizedPnl, 0);

    events.push({
      step: "PNL_RECONCILE",
      timestamp,
      symbol: this.symbol,
      data: { ltp: price, totalUnrealizedPnl },
      status: "SUCCESS",
    });

    this.events.push(...events);

    return {
      signal,
      fastEma,
      slowEma,
      rsi,
      generatedOrder,
      updatedPositions: this.positions,
      totalUnrealizedPnl,
      events,
    };
  }

  private calculateEma(prices: number[], period: number): number {
    if (prices.length === 0) return 0;
    if (prices.length === 1) return prices[0];

    const k = 2 / (period + 1);
    let ema = prices[0];
    for (let i = 1; i < prices.length; i++) {
      ema = prices[i] * k + ema * (1 - k);
    }
    return Number(ema.toFixed(2));
  }

  private calculateRsi(prices: number[], period: number): number {
    if (prices.length < period + 1) return 55;

    let gains = 0;
    let losses = 0;

    const recent = prices.slice(-period - 1);
    for (let i = 1; i < recent.length; i++) {
      const diff = recent[i] - recent[i - 1];
      if (diff >= 0) {
        gains += diff;
      } else {
        losses += Math.abs(diff);
      }
    }

    if (losses === 0) return 100;
    const rs = (gains / period) / (losses / period);
    const rsi = 100 - 100 / (1 + rs);
    return Number(rsi.toFixed(2));
  }
}
