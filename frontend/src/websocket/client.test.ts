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

  it("leaves change and volume unavailable when Dhan did not send them", () => {
    const listener = vi.fn();
    client.onChannel("quotes", listener);
    client.subscribeChannels(
      ["quotes"],
      ["RELIANCE"],
      [{ segment: "1", securityId: "2885", symbol: "RELIANCE" }],
    );

    (client as any).handleMessage(JSON.stringify({
      type: "delta",
      channel: "quotes",
      segment: "1",
      security_id: "2885",
      data: { ltp: 1412.5, market_state: "LIVE", source: "DHAN_WEBSOCKET" },
    }));

    expect(listener).toHaveBeenCalledWith(expect.objectContaining({
      symbol: "RELIANCE",
      ltp: 1412.5,
      change: undefined,
      changePct: undefined,
      volume: undefined,
    }));
  });

  it("reference-counts shared subscriptions before releasing them", () => {
    const instrument = [{ segment: "1", securityId: "2885", symbol: "RELIANCE" }];
    client.subscribeChannels(["quotes"], ["RELIANCE"], instrument);
    client.subscribeChannels(["quotes"], ["RELIANCE"], instrument);

    client.unsubscribeChannels(["quotes"], ["RELIANCE"], instrument);
    expect(client.getSubscribedSymbols()).toContain("RELIANCE");
    expect(client.getSubscribedChannels()).toContain("quotes");

    client.unsubscribeChannels(["quotes"], ["RELIANCE"], instrument);
    expect(client.getSubscribedSymbols()).not.toContain("RELIANCE");
    expect(client.getSubscribedChannels()).not.toContain("quotes");
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
