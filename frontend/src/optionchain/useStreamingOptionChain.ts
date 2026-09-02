import { useState, useEffect, useRef, useCallback } from "react";
import { OptionChainData, OptionStrikeRow } from "./types";
import { generateOptionChain, calculateBlack76Greeks, solveImpliedVolatilityBlack76 } from "./greeks";

export interface TickUpdate {
  symbol: string;
  ltp: number;
  oi?: number;
  volume?: number;
  bid?: number;
  ask?: number;
  timestamp?: number;
}

export interface UseStreamingOptionChainOptions {
  underlying: string;
  spotPrice: number;
  expiry: string;
  strikeStep: number;
  strikesCount: number;
  riskFreeRate?: number;
  onSubscribe?: (symbols: string[]) => void;
  onUnsubscribe?: (symbols: string[]) => void;
  mockStreaming?: boolean;
}

export interface UseStreamingOptionChainResult {
  chainData: OptionChainData;
  isStale: boolean;
  lastUpdateTime: number | null;
  subscribedSymbols: string[];
  applyTickUpdate: (update: TickUpdate) => void;
  applyBatchTicks: (updates: TickUpdate[]) => void;
}

export function useStreamingOptionChain({
  underlying,
  spotPrice,
  expiry,
  strikeStep,
  strikesCount,
  riskFreeRate = 0.07,
  onSubscribe,
  onUnsubscribe,
  mockStreaming = false,
}: UseStreamingOptionChainOptions): UseStreamingOptionChainResult {
  const [chainData, setChainData] = useState<OptionChainData>(() =>
    generateOptionChain(underlying, spotPrice, expiry, strikeStep, strikesCount)
  );
  const [isStale, setIsStale] = useState<boolean>(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<number | null>(null);

  // References for tick buffer and render throttling
  const tickBufferRef = useRef<Map<string, TickUpdate>>(new Map());
  const rafIdRef = useRef<number | null>(null);
  const lastRenderTimeRef = useRef<number>(Date.now());
  const lastTickReceivedTimeRef = useRef<number>(Date.now());

  // Collect symbols
  const currentSymbols = (chainData?.rows || []).flatMap((s) => [s.call.symbol, s.put.symbol]);

  // Handle underlying / expiry / strike range resubscription
  useEffect(() => {
    const initialData = generateOptionChain(underlying, spotPrice, expiry, strikeStep, strikesCount);
    setChainData(initialData);
    lastTickReceivedTimeRef.current = Date.now();
    setLastUpdateTime(Date.now());
    setIsStale(false);

    const newSymbols = initialData.rows.flatMap((s) => [s.call.symbol, s.put.symbol]);
    if (newSymbols.length > 0 && onSubscribe) {
      onSubscribe(newSymbols);
    }

    return () => {
      if (newSymbols.length > 0 && onUnsubscribe) {
        onUnsubscribe(newSymbols);
      }
    };
  }, [underlying, spotPrice, expiry, strikeStep, strikesCount, onSubscribe, onUnsubscribe]);

  // Staleness monitor
  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Date.now() - lastTickReceivedTimeRef.current;
      setIsStale(elapsed > 5000);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Flush buffered ticks and update Greeks within 16ms render budget
  const flushTicks = useCallback(() => {
    rafIdRef.current = null;
    const now = Date.now();
    const buffer = tickBufferRef.current;
    if (buffer.size === 0) return;

    const updates = Array.from(buffer.values());
    buffer.clear();
    lastRenderTimeRef.current = now;
    lastTickReceivedTimeRef.current = now;
    setLastUpdateTime(now);
    setIsStale(false);

    setChainData((prev) => {
      const updateMap = new Map(updates.map((u) => [u.symbol, u]));

      // Update rows
      const updatedRows: OptionStrikeRow[] = (prev?.rows || []).map((row) => {
        let call = row.call;
        let put = row.put;

        const callUpd = updateMap.get(call.symbol);
        if (callUpd) {
          const newLtp = callUpd.ltp ?? call.ltp;
          const newOi = callUpd.oi ?? call.oi;
          const newVol = callUpd.volume ?? call.volume;
          const newBid = callUpd.bid ?? call.bid;
          const newAsk = callUpd.ask ?? call.ask;

          // Recalculate IV and Greeks locally
          const solved = solveImpliedVolatilityBlack76(
            newLtp,
            prev.underlyingPrice * 1.003,
            row.strike,
            7.0 / 365.0,
            riskFreeRate,
            true
          );
          const activeIv = solved.isReliable ? solved.iv : call.iv / 100.0;
          const newGreeksRes = calculateBlack76Greeks(
            prev.underlyingPrice * 1.003,
            row.strike,
            7.0 / 365.0,
            riskFreeRate,
            activeIv,
            true
          );

          call = {
            ...call,
            ltp: newLtp,
            oi: newOi,
            volume: newVol,
            bid: newBid,
            ask: newAsk,
            iv: Number((activeIv * 100).toFixed(1)),
            greeks: newGreeksRes.greeks,
          };
        }

        const putUpd = updateMap.get(put.symbol);
        if (putUpd) {
          const newLtp = putUpd.ltp ?? put.ltp;
          const newOi = putUpd.oi ?? put.oi;
          const newVol = putUpd.volume ?? put.volume;
          const newBid = putUpd.bid ?? put.bid;
          const newAsk = putUpd.ask ?? put.ask;

          const solved = solveImpliedVolatilityBlack76(
            newLtp,
            prev.underlyingPrice * 1.003,
            row.strike,
            7.0 / 365.0,
            riskFreeRate,
            false
          );
          const activeIv = solved.isReliable ? solved.iv : put.iv / 100.0;
          const newGreeksRes = calculateBlack76Greeks(
            prev.underlyingPrice * 1.003,
            row.strike,
            7.0 / 365.0,
            riskFreeRate,
            activeIv,
            false
          );

          put = {
            ...put,
            ltp: newLtp,
            oi: newOi,
            volume: newVol,
            bid: newBid,
            ask: newAsk,
            iv: Number((activeIv * 100).toFixed(1)),
            greeks: newGreeksRes.greeks,
          };
        }

        return {
          ...row,
          call,
          put,
        };
      });

      // Recalculate totals and PCR
      const totalCallOi = updatedRows.reduce((acc, s) => acc + s.call.oi, 0);
      const totalPutOi = updatedRows.reduce((acc, s) => acc + s.put.oi, 0);
      const pcrRatio = totalCallOi > 0 ? Number((totalPutOi / totalCallOi).toFixed(2)) : 1.0;

      return {
        ...prev,
        rows: updatedRows,
        pcrRatio,
      };
    });
  }, [riskFreeRate]);

  // Apply single tick update into buffer
  const applyTickUpdate = useCallback(
    (update: TickUpdate) => {
      tickBufferRef.current.set(update.symbol, update);
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushTicks);
      }
    },
    [flushTicks]
  );

  // Apply batch of ticks
  const applyBatchTicks = useCallback(
    (updates: TickUpdate[]) => {
      for (const u of updates) {
        tickBufferRef.current.set(u.symbol, u);
      }
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(flushTicks);
      }
    },
    [flushTicks]
  );

  // Mock tick generator for live demonstration when requested
  useEffect(() => {
    if (!mockStreaming) return;

    const interval = setInterval(() => {
      const rows = chainData?.rows || [];
      if (rows.length === 0) return;

      const randomIdx = Math.floor(Math.random() * rows.length);
      const row = rows[randomIdx];
      const isCall = Math.random() > 0.5;
      const target = isCall ? row.call : row.put;

      const deltaPrice = (Math.random() - 0.48) * 2.0;
      const newLtp = Math.max(0.5, Number((target.ltp + deltaPrice).toFixed(2)));
      const newOi = target.oi + Math.floor((Math.random() - 0.5) * 500);

      applyTickUpdate({
        symbol: target.symbol,
        ltp: newLtp,
        oi: Math.max(0, newOi),
        volume: target.volume + Math.floor(Math.random() * 50),
      });
    }, 150);

    return () => clearInterval(interval);
  }, [mockStreaming, chainData?.rows, applyTickUpdate]);

  return {
    chainData,
    isStale,
    lastUpdateTime,
    subscribedSymbols: currentSymbols,
    applyTickUpdate,
    applyBatchTicks,
  };
}
