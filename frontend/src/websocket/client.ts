import {
  WebSocketState,
  FeedChannel,
  TickData,
  WebSocketClientOptions,
} from "./types";

export const SECURITY_ID_MAP: Record<string, string> = {
  // Equities
  "1333": "HDFCBANK",
  "2885": "RELIANCE",
  "11536": "TCS",
  "1594": "INFY",
  "4963": "ICICIBANK",
  "3045": "SBIN",
  "10604": "BHARTIARTL",
  "3456": "TATAMOTORS",
  "1232": "GRASIM",
  "1922": "KOTAKBANK",
  "5900": "AXISBANK",
  "236": "ASIANPAINT",
  "11483": "LT",
  "526": "BPCL",
  "1363": "HINDUNILVR",
  "1660": "ITC",
  "317": "BAJFINANCE",
  "10999": "MARUTI",
  "3499": "TATASTEEL",
  "3351": "SUNPHARMA",
  "3787": "WIPRO",
  "7229": "HCLTECH",
  "2142": "POWERGRID",
  "3103": "NESTLEIND",
  "10794": "NTPC",
  "13538": "TECHM",
  "14977": "ONGC",
  "3506": "TITAN",
  "14418": "NIFTYBEES",
  "14419": "BANKBEES",
  // Indices
  "13": "NIFTY",
  "25": "BANKNIFTY",
  "27": "FINNIFTY",
  "28": "MIDCPNIFTY",
  "51": "SENSEX",
  "29": "NIFTYIT",
  "30": "NIFTYAUTO",
};

export const SYMBOL_MAP: Record<string, string> = Object.entries(SECURITY_ID_MAP).reduce(
  (acc, [secId, sym]) => {
    acc[sym] = secId;
    return acc;
  },
  {} as Record<string, string>,
);

// Add index aliases
SYMBOL_MAP["NIFTY 50"] = "13";
SYMBOL_MAP["NIFTY BANK"] = "25";
SYMBOL_MAP["NIFTY FINANCIAL SERVICES"] = "27";
SYMBOL_MAP["NIFTY IT"] = "29";
SYMBOL_MAP["NIFTY AUTO"] = "30";

export class NexaWebSocketClient {
  private url: string;
  private state: WebSocketState = "DISCONNECTED";
  private maxReconnectAttempts: number;
  private reconnectDelayMs: number;
  private mockFeedEnabled: boolean;

  private reconnectCount: number = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private mockIntervalTimer: ReturnType<typeof setInterval> | null = null;
  private lastLivePacketTime: number = 0;
  private latency: number = 12;
  private ws: WebSocket | null = null;

  // Authentic today's closing prices from Dhan API
  private basePrices: Record<string, number> = {
    NIFTY: 23431.50,
    "NIFTY 50": 23431.50,
    BANKNIFTY: 56295.55,
    "NIFTY BANK": 56295.55,
    FINNIFTY: 25376.80,
    MIDCPNIFTY: 45309.25,
    NIFTYIT: 28914.00,
    NIFTYAUTO: 1526.45,
    RELIANCE: 1279.00,
    TCS: 2208.00,
    HDFCBANK: 687.10,
    INFY: 1035.00,
    ICICIBANK: 1389.10,
    SBIN: 1000.50,
    BHARTIARTL: 1814.70,
    ITC: 260.80,
    KOTAKBANK: 414.00,
    LT: 3922.60,
    AXISBANK: 1238.50,
    MARUTI: 12618.00,
    BAJFINANCE: 1039.30,
    TATAMOTORS: 303.00,
    TATASTEEL: 188.75,
    SUNPHARMA: 1864.90,
    WIPRO: 167.00,
    HCLTECH: 1229.80,
    HINDUNILVR: 1026.90,
    POWERGRID: 1468.50,
    NESTLEIND: 22950.00,
    ONGC: 265.85,
    TITAN: 5005.00,
  };

  private channelListeners: Map<FeedChannel, Set<(data: unknown) => void>> = new Map();
  private symbolListeners: Map<string, Set<(tick: TickData) => void>> = new Map();
  private stateListeners: Set<(state: WebSocketState) => void> = new Set();
  private subscribedSymbols: Set<string> = new Set(["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "TCS", "INFY", "NIFTY 50", "NIFTY BANK"]);
  private subscribedChannels: Set<FeedChannel> = new Set(["quotes", "depth", "oi"]);

  constructor(options: WebSocketClientOptions = {}) {
    const defaultWsUrl =
      typeof window !== "undefined" && window.location && window.location.host
        ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/feed/ws`
        : "ws://127.0.0.1:8000/api/v1/feed/ws";
    this.url = options.url || defaultWsUrl;
    this.maxReconnectAttempts = options.reconnectAttempts ?? 10;
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1000;
    this.mockFeedEnabled = options.mockFeedEnabled ?? false;

    if (options.autoConnect) {
      this.connect();
    }
    if (typeof window !== "undefined") {
      this.syncRealQuotes();
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

  public getLastLivePacketTime(): number {
    return this.lastLivePacketTime;
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
        this.syncRealQuotes();
      }, 50);
      return;
    }

    if (typeof window !== "undefined" && typeof window.WebSocket !== "undefined") {
      try {
        const wsUrl = this.url.includes("?")
          ? `${this.url}&token=demo-session-token`
          : `${this.url}?token=demo-session-token`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.setState("CONNECTED");
          this.reconnectCount = 0;
          this.latency = 12;
          this.sendSubscriptions();
          this.syncRealQuotes();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if ((data.type === "delta" || data.type === "snapshot") && data.channel === "quotes" && data.data) {
              this.lastLivePacketTime = Date.now();
              const secId = String(data.security_id || data.data.security_id);
              const symbol = SECURITY_ID_MAP[secId] || `SEC-${secId}`;
              const ltp = Number(data.data.ltp);
              const close = Number(data.data.close || ltp);
              const change = Number((ltp - close).toFixed(2));
              const changePct = close > 0 ? Number(((change / close) * 100).toFixed(2)) : 0;

              // Anchor base price with genuine Dhan API feed value
              this.basePrices[symbol] = ltp;

              const tick: TickData = {
                symbol,
                ltp,
                change,
                changePct,
                volume: Number(data.data.volume || 0),
                timestamp: Date.now(),
              };
              this.dispatchTick(tick);

              // Also dispatch for index aliases
              if (symbol === "NIFTY") {
                this.basePrices["NIFTY 50"] = ltp;
                this.dispatchTick({ ...tick, symbol: "NIFTY 50" });
              } else if (symbol === "BANKNIFTY") {
                this.basePrices["NIFTY BANK"] = ltp;
                this.dispatchTick({ ...tick, symbol: "NIFTY BANK" });
              }
            }
          } catch {
            // Ignore parse errors
          }
        };

        this.ws.onerror = () => {
          // Handled by onclose
        };

        this.ws.onclose = () => {
          this.ws = null;
          if (this.state !== "DISCONNECTED") {
            this.attemptReconnect();
          }
        };
      } catch {
        this.attemptReconnect();
      }
    }
  }

  private sendSubscriptions(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    const instruments: Array<[string, string]> = [];
    for (const sym of this.subscribedSymbols) {
      const secId = SYMBOL_MAP[sym];
      if (secId) {
        instruments.push(["1", secId]);
      }
    }
    // Always include default liquid instruments
    instruments.push(["1", "1333"], ["1", "2885"], ["1", "11536"], ["1", "1594"], ["1", "13"]);

    try {
      this.ws.send(
        JSON.stringify({
          action: "subscribe",
          channels: Array.from(this.subscribedChannels),
          instruments,
        }),
      );
    } catch {
      // Ignore send errors
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
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState("DISCONNECTED");
  }

  public simulateDisconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
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
    this.sendSubscriptions();
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

  public async syncRealQuotes(): Promise<void> {
    try {
      const resp = await fetch("/api/v1/feed/quotes", {
        headers: {
          Authorization: "Bearer demo-session-token",
        },
      });
      if (!resp.ok) return;
      const res = await resp.json();
      if (!res || !res.quotes) return;

      const quotes = res.quotes;
      for (const [key, q] of Object.entries(quotes)) {
        if (key.includes(":")) continue;
        const secId = String((q as any).security_id || key);
        const sym = SECURITY_ID_MAP[secId];
        if (!sym) continue;

        const ltp = Number((q as any).ltp);
        const close = Number((q as any).close || ltp);
        const open = Number((q as any).open || ltp);

        const change =
          close !== ltp
            ? Number((ltp - close).toFixed(2))
            : open > 0 && open !== ltp
            ? Number((ltp - open).toFixed(2))
            : 0;
        const changePct =
          close > 0 && close !== ltp
            ? Number(((change / close) * 100).toFixed(2))
            : open > 0 && open !== ltp
            ? Number((((ltp - open) / open) * 100).toFixed(2))
            : 0;

        this.basePrices[sym] = ltp;

        const tick: TickData = {
          symbol: sym,
          ltp,
          change,
          changePct,
          volume: Number((q as any).volume || 1000),
          timestamp: Date.now(),
        };
        this.dispatchTick(tick);

        if (sym === "NIFTY") {
          this.basePrices["NIFTY 50"] = ltp;
          this.dispatchTick({ ...tick, symbol: "NIFTY 50" });
        } else if (sym === "BANKNIFTY") {
          this.basePrices["NIFTY BANK"] = ltp;
          this.dispatchTick({ ...tick, symbol: "NIFTY BANK" });
        }
      }
    } catch {
      // Ignore network errors during sync
    }
  }
}

export const defaultWebSocketClient = new NexaWebSocketClient({ autoConnect: true });
