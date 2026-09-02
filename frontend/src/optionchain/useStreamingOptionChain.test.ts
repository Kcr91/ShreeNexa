import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useStreamingOptionChain } from "./useStreamingOptionChain";

describe("useStreamingOptionChain Hook", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("initializes chain and triggers onSubscribe with contract symbols", () => {
    const onSubscribe = vi.fn();
    const onUnsubscribe = vi.fn();

    const { result } = renderHook(() =>
      useStreamingOptionChain({
        underlying: "NIFTY",
        spotPrice: 24520,
        expiry: "2026-01-29",
        strikeStep: 50,
        strikesCount: 5,
        onSubscribe,
        onUnsubscribe,
      })
    );

    expect(result.current.chainData.rows.length).toBe(11);
    expect(result.current.subscribedSymbols.length).toBe(22);
    expect(onSubscribe).toHaveBeenCalledTimes(1);
    expect(onSubscribe).toHaveBeenCalledWith(expect.arrayContaining(["NIFTY 24500 CE"]));
  });

  it("applies tick updates and recalculates Greeks locally", async () => {
    const { result } = renderHook(() =>
      useStreamingOptionChain({
        underlying: "NIFTY",
        spotPrice: 24520,
        expiry: "2026-01-29",
        strikeStep: 50,
        strikesCount: 5,
      })
    );

    const targetCallSymbol = "NIFTY 24500 CE";
    const initialCall = result.current.chainData.rows.find(
      (s) => s.call.symbol === targetCallSymbol
    )?.call;
    expect(initialCall).toBeDefined();

    // Apply tick update
    act(() => {
      result.current.applyTickUpdate({
        symbol: targetCallSymbol,
        ltp: 350.0,
        oi: 500000,
        volume: 300000,
      });
      // Trigger requestAnimationFrame
      vi.advanceTimersByTime(16);
    });

    const updatedCall = result.current.chainData.rows.find(
      (s) => s.call.symbol === targetCallSymbol
    )?.call;

    expect(updatedCall?.ltp).toBe(350.0);
    expect(updatedCall?.oi).toBe(500000);
    expect(updatedCall?.volume).toBe(300000);
    expect(updatedCall?.greeks.delta).toBeGreaterThan(0);
  });

  it("resubscribes safely on underlying change", () => {
    const onSubscribe = vi.fn();
    const onUnsubscribe = vi.fn();

    const { rerender } = renderHook(
      ({ underlying }) =>
        useStreamingOptionChain({
          underlying,
          spotPrice: 24520,
          expiry: "2026-01-29",
          strikeStep: 50,
          strikesCount: 5,
          onSubscribe,
          onUnsubscribe,
        }),
      {
        initialProps: { underlying: "NIFTY" },
      }
    );

    expect(onSubscribe).toHaveBeenCalledTimes(1);

    // Switch underlying to BANKNIFTY
    rerender({ underlying: "BANKNIFTY" });

    expect(onUnsubscribe).toHaveBeenCalledTimes(1);
    expect(onSubscribe).toHaveBeenCalledTimes(2);
    expect(onSubscribe).toHaveBeenLastCalledWith(expect.arrayContaining(["BANKNIFTY 24500 CE"]));
  });

  it("detects staleness when ticks are delayed", () => {
    const { result } = renderHook(() =>
      useStreamingOptionChain({
        underlying: "NIFTY",
        spotPrice: 24520,
        expiry: "2026-01-29",
        strikeStep: 50,
        strikesCount: 5,
      })
    );

    expect(result.current.isStale).toBe(false);

    // Advance time by 6 seconds without ticks
    act(() => {
      vi.advanceTimersByTime(6000);
    });

    expect(result.current.isStale).toBe(true);
  });
});
