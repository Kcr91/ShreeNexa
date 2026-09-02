import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { NexaWebSocketClient, defaultWebSocketClient } from "./client";
import { WebSocketState, FeedChannel, TickData } from "./types";

interface WebSocketContextType {
  client: NexaWebSocketClient;
  state: WebSocketState;
  latency: number;
  lastTicks: Record<string, TickData>;
  subscribedSymbols: string[];
  subscribedChannels: FeedChannel[];
  connect: () => void;
  disconnect: () => void;
  simulateReconnect: () => void;
  subscribeSymbol: (symbol: string) => void;
  unsubscribeSymbol: (symbol: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{
  children: ReactNode;
  client?: NexaWebSocketClient;
}> = ({ children, client = defaultWebSocketClient }) => {
  const [state, setState] = useState<WebSocketState>(client.getState());
  const [latency, setLatency] = useState<number>(client.getLatency());
  const [lastTicks, setLastTicks] = useState<Record<string, TickData>>({});
  const [subscribedSymbols, setSubscribedSymbols] = useState<string[]>(client.getSubscribedSymbols());
  const [subscribedChannels, setSubscribedChannels] = useState<FeedChannel[]>(client.getSubscribedChannels());

  useEffect(() => {
    const unsubState = client.onStateChange((nextState) => {
      setState(nextState);
      setLatency(client.getLatency());
    });

    const unsubQuotes = client.onChannel("quotes", (data) => {
      const tick = data as TickData;
      setLastTicks((prev) => ({
        ...prev,
        [tick.symbol]: tick,
      }));
      setLatency(client.getLatency());
    });

    return () => {
      unsubState();
      unsubQuotes();
    };
  }, [client]);

  const connect = () => client.connect();
  const disconnect = () => client.disconnect();
  const simulateReconnect = () => client.simulateDisconnect();

  const subscribeSymbol = (symbol: string) => {
    client.subscribeChannels(["quotes"], [symbol]);
    setSubscribedSymbols(client.getSubscribedSymbols());
    setSubscribedChannels(client.getSubscribedChannels());
  };

  const unsubscribeSymbol = (symbol: string) => {
    client.unsubscribeChannels([], [symbol]);
    setSubscribedSymbols(client.getSubscribedSymbols());
    setSubscribedChannels(client.getSubscribedChannels());
  };

  return (
    <WebSocketContext.Provider
      value={{
        client,
        state,
        latency,
        lastTicks,
        subscribedSymbols,
        subscribedChannels,
        connect,
        disconnect,
        simulateReconnect,
        subscribeSymbol,
        unsubscribeSymbol,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }
  return context;
};
