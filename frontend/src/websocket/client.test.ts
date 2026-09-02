import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { NexaWebSocketClient } from "./client";
import { TickData } from "./types";

describe("NexaWebSocketClient Multiplexing and Auto-Reconnect", () => {
  let client: NexaWebSocketClient;

  beforeEach(() => {
    vi.useFakeTimers();
    client = new NexaWebSocketClient({
      mockFeedEnabled: false,
      reconnectAttempts: 3,
      reconnectDelayMs: 200,
    });
  });

  afterEach(() => {
    client.disconnect();
    vi.useRealTimers();
  });

  it("manages channel and symbol subscriptions", () => {
    client.subscribeChannels(["quotes", "depth"], ["TATAMOTORS"]);
    expect(client.getSubscribedChannels()).toContain("quotes");
    expect(client.getSubscribedChannels()).toContain("depth");
    expect(client.getSubscribedSymbols()).toContain("TATAMOTORS");

    client.unsubscribeChannels(["depth"], ["TATAMOTORS"]);
    expect(client.getSubscribedChannels()).not.toContain("depth");
    expect(client.getSubscribedSymbols()).not.toContain("TATAMOTORS");
  });

  it("routes incoming tick data to channel and symbol listeners", () => {
    const quoteListener = vi.fn();
    const symbolListener = vi.fn();

    const unsubQuote = client.onChannel("quotes", quoteListener);
    const unsubSymbol = client.onTick("RELIANCE", symbolListener);

    const testTick: TickData = {
      symbol: "RELIANCE",
      ltp: 2955.5,
      change: 15.5,
      changePct: 0.53,
      volume: 12000,
      timestamp: Date.now(),
    };

    client.dispatchTick(testTick);

    expect(quoteListener).toHaveBeenCalledWith(testTick);
    expect(symbolListener).toHaveBeenCalledWith(testTick);

    unsubQuote();
    unsubSymbol();
  });

  it("transitions state and attempts auto-reconnect on disconnect", () => {
    const states: string[] = [];
    client.onStateChange((st) => states.push(st));

    client.simulateDisconnect();
    expect(client.getState()).toBe("RECONNECTING");

    // Fast-forward reconnect timer
    vi.advanceTimersByTime(300);
    expect(client.getState()).toBe("CONNECTING");
  });
});
