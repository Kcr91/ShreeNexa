import React, { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  createSeriesMarkers,
  IChartApi,
  ColorType,
  Time,
} from "lightweight-charts";
import { BarData, ChartIndicatorConfig } from "./types";
import { computeSMA, computeEMA, computeRSI, computeMACD, computeVWAP } from "./indicators";
import { detectSessionBreaks } from "./sessionBreaks";

interface Props {
  bars: BarData[];
  indicators?: ChartIndicatorConfig[];
  showSessionBreaks?: boolean;
  showVolume?: boolean;
}

export const ChartContainer: React.FC<Props> = ({
  bars,
  indicators = [],
  showSessionBreaks = true,
  showVolume = true,
}) => {
  const mainChartRef = useRef<HTMLDivElement>(null);
  const subChartRef = useRef<HTMLDivElement>(null);

  const mainChartApi = useRef<IChartApi | null>(null);
  const subChartApi = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!mainChartRef.current || bars.length === 0) return;

    // Destroy existing charts
    if (mainChartApi.current) {
      mainChartApi.current.remove();
      mainChartApi.current = null;
    }
    if (subChartApi.current) {
      subChartApi.current.remove();
      subChartApi.current = null;
    }

    const subPaneIndicators = indicators.filter((ind) => ind.pane === "subpane");
    const hasSubPane = subPaneIndicators.length > 0;

    // 1. Create Main Price Chart
    const mainChart = createChart(mainChartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#a0a5b5",
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.05)" },
        horzLines: { color: "rgba(255, 255, 255, 0.05)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0, 210, 255, 0.4)", width: 1, style: 3 },
        horzLine: { color: "rgba(0, 210, 255, 0.4)", width: 1, style: 3 },
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
      autoSize: true,
    });
    mainChartApi.current = mainChart;

    // Main Candlestick Series
    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor: "#00c076",
      downColor: "#ff4d4f",
      borderVisible: false,
      wickUpColor: "#00c076",
      wickDownColor: "#ff4d4f",
    });

    const candleData = bars.map((b) => ({
      time: b.time as Time,
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));
    candleSeries.setData(candleData);

    // Session break markers
    if (showSessionBreaks) {
      const breaks = detectSessionBreaks(bars);
      const markers = breaks.map((sb) => ({
        time: sb.time as Time,
        position: "aboveBar" as const,
        color: "#00d2ff",
        shape: "arrowDown" as const,
        text: `Open: ${sb.date}`,
      }));
      if (markers.length > 0) {
        try {
          createSeriesMarkers(candleSeries, markers);
        } catch {
          // Fallback if plugin cannot attach in test env
        }
      }
    }

    // Volume Series
    if (showVolume) {
      const volumeSeries = mainChart.addSeries(HistogramSeries, {
        color: "rgba(255, 255, 255, 0.15)",
        priceFormat: { type: "volume" },
        priceScaleId: "", // overlay
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      const volData = bars.map((b) => ({
        time: b.time as Time,
        value: b.volume || 0,
        color: b.close >= b.open ? "rgba(0, 192, 118, 0.3)" : "rgba(255, 77, 79, 0.3)",
      }));
      volumeSeries.setData(volData);
    }

    // Overlay Indicators (SMA, EMA, VWAP)
    const overlayIndicators = indicators.filter((ind) => ind.pane === "overlay");
    for (const ind of overlayIndicators) {
      const lineSeries = mainChart.addSeries(LineSeries, {
        color: ind.color || "#ffaa00",
        lineWidth: 2,
        title: `${ind.name}`,
      });

      let pts: { time: string | number; value: number }[] = [];
      if (ind.type === "SMA") {
        pts = computeSMA(bars, Number(ind.params.period || 20));
      } else if (ind.type === "EMA") {
        pts = computeEMA(bars, Number(ind.params.period || 20));
      } else if (ind.type === "VWAP") {
        pts = computeVWAP(bars);
      }
      lineSeries.setData(pts.map((p) => ({ time: p.time as Time, value: p.value })));
    }

    // 2. Create Sub-Pane Chart if RSI or MACD requested
    if (hasSubPane && subChartRef.current) {
      const subChart = createChart(subChartRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#a0a5b5",
        },
        grid: {
          vertLines: { color: "rgba(255, 255, 255, 0.05)" },
          horzLines: { color: "rgba(255, 255, 255, 0.05)" },
        },
        timeScale: {
          borderColor: "rgba(255, 255, 255, 0.1)",
          timeVisible: true,
          secondsVisible: false,
        },
        autoSize: true,
      });
      subChartApi.current = subChart;

      for (const ind of subPaneIndicators) {
        if (ind.type === "RSI") {
          const rsiSeries = subChart.addSeries(LineSeries, {
            color: ind.color || "#a855f7",
            lineWidth: 2,
            title: `RSI (${ind.params.period || 14})`,
          });
          const rsiPts = computeRSI(bars, Number(ind.params.period || 14));
          rsiSeries.setData(rsiPts.map((p) => ({ time: p.time as Time, value: p.value })));
        } else if (ind.type === "MACD") {
          const macdRes = computeMACD(bars);
          const macdLine = subChart.addSeries(LineSeries, {
            color: "#00d2ff",
            lineWidth: 1,
            title: "MACD",
          });
          const signalLine = subChart.addSeries(LineSeries, {
            color: "#ff7700",
            lineWidth: 1,
            title: "Signal",
          });
          const histSeries = subChart.addSeries(HistogramSeries, {
            title: "Histogram",
          });

          macdLine.setData(macdRes.macdLine.map((p) => ({ time: p.time as Time, value: p.value })));
          signalLine.setData(macdRes.signalLine.map((p) => ({ time: p.time as Time, value: p.value })));
          histSeries.setData(
            macdRes.histogram.map((p) => ({
              time: p.time as Time,
              value: p.value,
              color: p.color,
            }))
          );
        }
      }

      // Synchronize time scales
      mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range && subChartApi.current) {
          subChartApi.current.timeScale().setVisibleLogicalRange(range);
        }
      });
      subChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range && mainChartApi.current) {
          mainChartApi.current.timeScale().setVisibleLogicalRange(range);
        }
      });
    }

    return () => {
      if (mainChartApi.current) {
        mainChartApi.current.remove();
        mainChartApi.current = null;
      }
      if (subChartApi.current) {
        subChartApi.current.remove();
        subChartApi.current = null;
      }
    };
  }, [bars, indicators, showSessionBreaks, showVolume]);

  const hasSubPane = indicators.some((ind) => ind.pane === "subpane");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", position: "relative" }}>
      <div
        ref={mainChartRef}
        data-testid="main-chart-container"
        style={{ flex: hasSubPane ? 2 : 1, width: "100%", minHeight: "200px" }}
      />
      {hasSubPane && (
        <div
          ref={subChartRef}
          data-testid="sub-chart-container"
          style={{
            flex: 1,
            width: "100%",
            borderTop: "1px solid var(--border-subtle)",
            minHeight: "120px",
          }}
        />
      )}
    </div>
  );
};
