import { FeedChannel, InstrumentSubscription, TickData, WebSocketClientOptions, WebSocketState } from "./types";

interface InstrumentIdentity extends InstrumentSubscription {
  symbol: string;
}

const IDENTITIES: InstrumentIdentity[] = [
  { symbol: "HDFCBANK", segment: "1", securityId: "1333" },
  { symbol: "RELIANCE", segment: "1", securityId: "2885" },
  { symbol: "TCS", segment: "1", securityId: "11536" },
  { symbol: "INFY", segment: "1", securityId: "1594" },
  { symbol: "ICICIBANK", segment: "1", securityId: "4963" },
  { symbol: "SBIN", segment: "1", securityId: "3045" },
  { symbol: "BHARTIARTL", segment: "1", securityId: "10604" },
  { symbol: "ITC", segment: "1", securityId: "1660" },
  { symbol: "KOTAKBANK", segment: "1", securityId: "1922" },
  { symbol: "AXISBANK", segment: "1", securityId: "5900" },
  { symbol: "NIFTY 50", segment: "0", securityId: "13" },
  { symbol: "NIFTY BANK", segment: "0", securityId: "25" },
  { symbol: "NIFTY FIN SERVICE", segment: "0", securityId: "27" },
  { symbol: "NIFTY MID SELECT", segment: "0", securityId: "28" },
  { symbol: "NIFTY IT", segment: "0", securityId: "29" },
  { symbol: "NIFTY AUTO", segment: "0", securityId: "30" },
];

export const SECURITY_ID_MAP: Record<string, string> = Object.fromEntries(
  IDENTITIES.map((item) => [`${item.segment}:${item.securityId}`, item.symbol]),
);

const identityBySymbol = new Map(IDENTITIES.map((item) => [item.symbol, item]));
identityBySymbol.set("NIFTY", identityBySymbol.get("NIFTY 50")!);
identityBySymbol.set("NIFTY50", identityBySymbol.get("NIFTY 50")!);
identityBySymbol.set("BANKNIFTY", identityBySymbol.get("NIFTY BANK")!);
identityBySymbol.set("BANK NIFTY", identityBySymbol.get("NIFTY BANK")!);

export const SYMBOL_MAP: Record<string, string> = Object.fromEntries(
  [...identityBySymbol].map(([symbol, item]) => [symbol, item.securityId]),
);

const instrumentKey = (instrument: InstrumentSubscription): string =>
  `${instrument.segment}:${instrument.securityId}`;

export class NexaWebSocketClient {
  private readonly url: string;
  private state: WebSocketState = "DISCONNECTED";
  private readonly maxReconnectAttempts: number;
  private readonly reconnectDelayMs: number;
  private readonly mockFeedEnabled: boolean;
  private reconnectCount = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private ws: WebSocket | null = null;
  private lastLivePacketTime = 0;
  private latency = 0;
  private readonly channelListeners = new Map<FeedChannel, Set<(data: unknown) => void>>();
  private readonly symbolListeners = new Map<string, Set<(tick: TickData) => void>>();
  private readonly stateListeners = new Set<(state: WebSocketState) => void>();
  private readonly subscribedSymbols = new Set<string>();
  private readonly subscribedChannels = new Set<FeedChannel>();
  private readonly subscribedInstruments = new Map<string, InstrumentSubscription>();
  private readonly channelRefCounts = new Map<FeedChannel, number>();
  private readonly symbolRefCounts = new Map<string, number>();
  private readonly instrumentRefCounts = new Map<string, number>();

  constructor(options: WebSocketClientOptions = {}) {
    const defaultUrl = typeof window !== "undefined" && window.location
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/feed/ws`
      : "ws://127.0.0.1:8000/api/v1/feed/ws";
    this.url = options.url || defaultUrl;
    this.maxReconnectAttempts = options.reconnectAttempts ?? 10;
    this.reconnectDelayMs = options.reconnectDelayMs ?? 1000;
    this.mockFeedEnabled = options.mockFeedEnabled ?? false;
    if (options.autoConnect) this.connect();
  }

  public getUrl(): string { return this.url; }
  public getState(): WebSocketState { return this.state; }
  public getLatency(): number { return this.latency; }
  public getLastLivePacketTime(): number { return this.lastLivePacketTime; }
  public getSubscribedSymbols(): string[] { return [...this.subscribedSymbols]; }
  public getSubscribedChannels(): FeedChannel[] { return [...this.subscribedChannels]; }

  public connect(): void {
    if (this.state === "CONNECTED" || this.state === "CONNECTING") return;
    this.setState("CONNECTING");
    if (this.mockFeedEnabled) {
      setTimeout(() => { this.reconnectCount = 0; this.setState("CONNECTED"); }, 50);
      return;
    }
    if (typeof window === "undefined" || typeof window.WebSocket === "undefined") return;
    try {
      // Same-origin HttpOnly master-session cookie is sent by the browser handshake.
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this.reconnectCount = 0;
        this.latency = 0;
        this.setState("CONNECTED");
        this.sendSubscriptions();
      };
      this.ws.onmessage = (event) => this.handleMessage(event.data);
      this.ws.onerror = () => undefined;
      this.ws.onclose = () => {
        this.ws = null;
        if (this.state !== "DISCONNECTED") this.attemptReconnect();
      };
    } catch {
      this.attemptReconnect();
    }
  }

  private handleMessage(raw: string): void {
    try {
      const message = JSON.parse(raw);
      if (message.type === "feed_error") {
        this.setState("ERROR");
        return;
      }
      if ((message.type !== "delta" && message.type !== "snapshot") || message.channel !== "quotes") return;
      const data = message.data ?? {};
      if (typeof data.ltp !== "number") return;
      const segment = String(message.segment ?? data.segment);
      const securityId = String(message.security_id ?? data.security_id);
      const subscribed = this.subscribedInstruments.get(`${segment}:${securityId}`);
      const symbol = subscribed?.symbol ?? SECURITY_ID_MAP[`${segment}:${securityId}`] ?? `SEC-${securityId}`;
      const previousClose = typeof data.previous_close === "number" ? data.previous_close : undefined;
      const change = previousClose === undefined
        ? undefined
        : Number((data.ltp - previousClose).toFixed(2));
      const changePct = previousClose && change !== undefined
        ? Number((change / previousClose * 100).toFixed(2))
        : undefined;
      this.lastLivePacketTime = Date.now();
      this.dispatchTick({
        symbol,
        ltp: data.ltp,
        change,
        changePct,
        volume: typeof data.volume === "number" ? data.volume : undefined,
        timestamp: typeof data.received_at === "number" ? data.received_at * 1000 : Date.now(),
        sourceTimestamp: typeof data.ltt === "number" || typeof data.ltt === "string"
          ? data.ltt
          : undefined,
        previousClose,
        marketState: data.market_state,
        source: data.source,
        isStale: Boolean(data.is_stale),
      });
    } catch {
      this.setState("ERROR");
    }
  }

  private sendSubscriptions(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this.subscribedInstruments.size) return;
    this.ws.send(JSON.stringify({
      action: "subscribe",
      channels: [...this.subscribedChannels],
      instruments: [...this.subscribedInstruments.values()].map((item) => [item.segment, item.securityId]),
    }));
  }

  public disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.ws?.close();
    this.ws = null;
    this.setState("DISCONNECTED");
  }

  public simulateDisconnect(): void {
    this.ws?.close();
    this.ws = null;
    this.setState("DISCONNECTED");
    this.attemptReconnect();
  }

  private attemptReconnect(): void {
    if (this.reconnectCount >= this.maxReconnectAttempts) {
      this.setState("ERROR");
      return;
    }
    this.reconnectCount += 1;
    this.setState("RECONNECTING");
    const delay = this.reconnectDelayMs * Math.pow(1.5, this.reconnectCount - 1);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private setState(state: WebSocketState): void {
    this.state = state;
    this.stateListeners.forEach((listener) => listener(state));
  }

  public onStateChange(listener: (state: WebSocketState) => void): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => { this.stateListeners.delete(listener); };
  }

  public subscribeChannels(
    channels: FeedChannel[],
    symbols?: string[],
    instruments?: InstrumentSubscription[],
  ): void {
    channels.forEach((channel) => {
      this.channelRefCounts.set(channel, (this.channelRefCounts.get(channel) ?? 0) + 1);
      this.subscribedChannels.add(channel);
    });
    const explicitSymbols = new Set(
      instruments?.flatMap((instrument) => instrument.symbol ? [instrument.symbol.toUpperCase()] : []) ?? [],
    );
    const requestedInstruments = new Map<string, InstrumentSubscription>();
    symbols?.forEach((rawSymbol) => {
      const symbol = rawSymbol.toUpperCase();
      this.symbolRefCounts.set(symbol, (this.symbolRefCounts.get(symbol) ?? 0) + 1);
      this.subscribedSymbols.add(symbol);
      const identity = identityBySymbol.get(symbol);
      if (identity && !explicitSymbols.has(symbol)) {
        requestedInstruments.set(instrumentKey(identity), identity);
      }
    });
    instruments?.forEach((instrument) => {
      requestedInstruments.set(instrumentKey(instrument), instrument);
    });
    requestedInstruments.forEach((instrument, key) => {
      this.instrumentRefCounts.set(key, (this.instrumentRefCounts.get(key) ?? 0) + 1);
      this.subscribedInstruments.set(key, instrument);
    });
    this.sendSubscriptions();
  }

  public unsubscribeChannels(
    channels: FeedChannel[],
    symbols?: string[],
    instruments?: InstrumentSubscription[],
  ): void {
    channels.forEach((channel) => {
      const remaining = (this.channelRefCounts.get(channel) ?? 1) - 1;
      if (remaining <= 0) {
        this.channelRefCounts.delete(channel);
        this.subscribedChannels.delete(channel);
      } else {
        this.channelRefCounts.set(channel, remaining);
      }
    });
    const explicitSymbols = new Set(
      instruments?.flatMap((instrument) => instrument.symbol ? [instrument.symbol.toUpperCase()] : []) ?? [],
    );
    const requestedKeys = new Set<string>();
    symbols?.forEach((rawSymbol) => {
      const symbol = rawSymbol.toUpperCase();
      const remaining = (this.symbolRefCounts.get(symbol) ?? 1) - 1;
      if (remaining <= 0) {
        this.symbolRefCounts.delete(symbol);
        this.subscribedSymbols.delete(symbol);
      } else {
        this.symbolRefCounts.set(symbol, remaining);
      }
      const identity = identityBySymbol.get(symbol);
      if (identity && !explicitSymbols.has(symbol)) requestedKeys.add(instrumentKey(identity));
    });
    instruments?.forEach((instrument) => requestedKeys.add(instrumentKey(instrument)));

    const released: InstrumentSubscription[] = [];
    requestedKeys.forEach((key) => {
      const remaining = (this.instrumentRefCounts.get(key) ?? 1) - 1;
      if (remaining <= 0) {
        this.instrumentRefCounts.delete(key);
        const instrument = this.subscribedInstruments.get(key);
        if (instrument) released.push(instrument);
        this.subscribedInstruments.delete(key);
      } else {
        this.instrumentRefCounts.set(key, remaining);
      }
    });
    if (released.length && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: "unsubscribe",
        channels,
        instruments: released.map((item) => [item.segment, item.securityId]),
      }));
    }
  }

  public onChannel(channel: FeedChannel, listener: (data: unknown) => void): () => void {
    if (!this.channelListeners.has(channel)) this.channelListeners.set(channel, new Set());
    this.channelListeners.get(channel)!.add(listener);
    return () => { this.channelListeners.get(channel)?.delete(listener); };
  }

  public onTick(symbol: string, listener: (tick: TickData) => void): () => void {
    const normalized = symbol.toUpperCase();
    if (!this.symbolListeners.has(normalized)) this.symbolListeners.set(normalized, new Set());
    this.symbolListeners.get(normalized)!.add(listener);
    return () => { this.symbolListeners.get(normalized)?.delete(listener); };
  }

  public dispatchTick(tick: TickData): void {
    this.channelListeners.get("quotes")?.forEach((listener) => listener(tick));
    this.symbolListeners.get(tick.symbol.toUpperCase())?.forEach((listener) => listener(tick));
  }

  public async syncRealQuotes(): Promise<void> {
    try {
      const response = await fetch("/api/v1/feed/quotes", { credentials: "include" });
      if (!response.ok) this.setState("ERROR");
    } catch {
      this.setState("ERROR");
    }
  }

  public resync(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "resync" }));
    }
  }
}

export const defaultWebSocketClient = new NexaWebSocketClient({ autoConnect: false });
