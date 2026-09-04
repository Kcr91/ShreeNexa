import {
  WebSocketState,
  FeedChannel,
  TickData,
  WebSocketClientOptions,
} from "./types";

export class NexaWebSocketClient {
  private url: string;
  private state: WebSocketState = "DISCONNECTED";
  private maxReconnectAttempts: number;
  private reconnectDelayMs: number;
  private mockFeedEnabled: boolean;

  private reconnectCount: number = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private mockIntervalTimer: ReturnType<typeof setInterval> | null = null;
  private latency: number = 14;

  private channelListeners: Map<FeedChannel, Set<(data: unknown) => void>> = new Map();
  private symbolListeners: Map<string, Set<(tick: TickData) => void>> = new Map();
  private stateListeners: Set<(state: WebSocketState) => void> = new Set();
  private subscribedSymbols: Set<string> = new Set(["NIFTY", "BANKNIFTY", "RELIANCE"]);
  private subscribedChannels: Set<FeedChannel> = new Set(["quotes", "positions", "orders"]);

  constructor(options: WebSocketClientOptions = {}) {
    const defaultWsUrl =
      typeof window !== "undefined" && window.location && window.location.host
        ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/feed/ws`
        : "ws://127.0.0.1:8000/api/v1/feed/ws";
    this.url = options.url || defaultWsUrl;
    this.maxReconnectAttempts = options.reconnectAttempts ?? 5;
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1000;
    this.mockFeedEnabled = options.mockFeedEnabled ?? true;

    if (options.autoConnect) {
      this.connect();
    }
  }

  public getUrl(): string {
    return this.url;
  }

  public getState(): WebSocketState {
    return this.state;
  }

  public getLatency(): number {
    return this.latency;
  }

  public getSubscribedSymbols(): string[] {
    return Array.from(this.subscribedSymbols);
  }

  public getSubscribedChannels(): FeedChannel[] {
    return Array.from(this.subscribedChannels);
  }

  public connect(): void {
    if (this.state === "CONNECTED" || this.state === "CONNECTING") return;

    this.setState("CONNECTING");

    if (this.mockFeedEnabled) {
      setTimeout(() => {
        this.setState("CONNECTED");
        this.reconnectCount = 0;
        this.startMockFeed();
      }, 50);
    }
  }

  public disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.mockIntervalTimer) {
      clearInterval(this.mockIntervalTimer);
      this.mockIntervalTimer = null;
    }
    this.setState("DISCONNECTED");
  }

  public simulateDisconnect(): void {
    if (this.mockIntervalTimer) {
      clearInterval(this.mockIntervalTimer);
      this.mockIntervalTimer = null;
    }
    this.setState("DISCONNECTED");
    this.attemptReconnect();
  }

  private attemptReconnect(): void {
    if (this.reconnectCount >= this.maxReconnectAttempts) {
      this.setState("ERROR");
      return;
    }

    this.reconnectCount++;
    this.setState("RECONNECTING");

    const delay = this.reconnectDelayMs * Math.pow(1.5, this.reconnectCount - 1);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private setState(nextState: WebSocketState): void {
    this.state = nextState;
    for (const listener of this.stateListeners) {
      listener(this.state);
    }
  }

  public onStateChange(listener: (state: WebSocketState) => void): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  public subscribeChannels(channels: FeedChannel[], symbols?: string[]): void {
    for (const ch of channels) {
      this.subscribedChannels.add(ch);
    }
    if (symbols) {
      for (const s of symbols) {
        this.subscribedSymbols.add(s.toUpperCase());
      }
    }
  }

  public unsubscribeChannels(channels: FeedChannel[], symbols?: string[]): void {
    for (const ch of channels) {
      this.subscribedChannels.delete(ch);
    }
    if (symbols) {
      for (const s of symbols) {
        this.subscribedSymbols.delete(s.toUpperCase());
      }
    }
  }

  public onChannel(channel: FeedChannel, listener: (data: unknown) => void): () => void {
    if (!this.channelListeners.has(channel)) {
      this.channelListeners.set(channel, new Set());
    }
    this.channelListeners.get(channel)!.add(listener);

    return () => {
      this.channelListeners.get(channel)?.delete(listener);
    };
  }

  public onTick(symbol: string, listener: (tick: TickData) => void): () => void {
    const sym = symbol.toUpperCase();
    if (!this.symbolListeners.has(sym)) {
      this.symbolListeners.set(sym, new Set());
    }
    this.symbolListeners.get(sym)!.add(listener);

    return () => {
      this.symbolListeners.get(sym)?.delete(listener);
    };
  }

  public dispatchTick(tick: TickData): void {
    // Dispatch to quotes channel
    const channelSubs = this.channelListeners.get("quotes");
    if (channelSubs) {
      for (const cb of channelSubs) {
        cb(tick);
      }
    }

    // Dispatch to symbol specific listener
    const symSubs = this.symbolListeners.get(tick.symbol.toUpperCase());
    if (symSubs) {
      for (const cb of symSubs) {
        cb(tick);
      }
    }
  }

  private startMockFeed(): void {
    if (this.mockIntervalTimer) clearInterval(this.mockIntervalTimer);

    const basePrices: Record<string, number> = {
      NIFTY: 24520.0,
      BANKNIFTY: 51800.0,
      RELIANCE: 2950.0,
      HDFCBANK: 1680.0,
      INFY: 1820.0,
    };

    this.mockIntervalTimer = setInterval(() => {
      if (this.state !== "CONNECTED") return;

      const symbols = Array.from(this.subscribedSymbols);
      if (symbols.length === 0) return;

      // Pick a random subscribed symbol
      const sym = symbols[Math.floor(Math.random() * symbols.length)];
      const base = basePrices[sym] || 1000.0;
      const drift = (Math.random() - 0.49) * (base * 0.001);
      const ltp = Number((base + drift).toFixed(2));
      basePrices[sym] = ltp;

      const tick: TickData = {
        symbol: sym,
        ltp,
        change: Number(drift.toFixed(2)),
        changePct: Number(((drift / base) * 100).toFixed(2)),
        volume: Math.floor(Math.random() * 5000) + 100,
        timestamp: Date.now(),
      };

      this.latency = Math.floor(Math.random() * 8) + 8; // 8-16ms
      this.dispatchTick(tick);
    }, 400);
  }
}

export const defaultWebSocketClient = new NexaWebSocketClient({ autoConnect: true });
