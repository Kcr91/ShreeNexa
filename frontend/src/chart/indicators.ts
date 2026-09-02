import { BarData } from "./types";

export interface LinePoint {
  time: string | number;
  value: number;
}

export interface HistogramPoint {
  time: string | number;
  value: number;
  color?: string;
}

export interface MACDResult {
  macdLine: LinePoint[];
  signalLine: LinePoint[];
  histogram: HistogramPoint[];
}

export function computeSMA(bars: BarData[], period: number): LinePoint[] {
  if (bars.length < period || period <= 0) return [];
  const result: LinePoint[] = [];

  let sum = 0;
  for (let i = 0; i < bars.length; i++) {
    sum += bars[i].close;
    if (i >= period) {
      sum -= bars[i - period].close;
    }
    if (i >= period - 1) {
      result.push({
        time: bars[i].time,
        value: Number((sum / period).toFixed(2)),
      });
    }
  }
  return result;
}

export function computeEMA(bars: BarData[], period: number): LinePoint[] {
  if (bars.length < period || period <= 0) return [];
  const result: LinePoint[] = [];
  const multiplier = 2 / (period + 1);

  // Initial SMA as seed
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += bars[i].close;
  }
  let currentEma = sum / period;
  result.push({ time: bars[period - 1].time, value: Number(currentEma.toFixed(2)) });

  for (let i = period; i < bars.length; i++) {
    currentEma = (bars[i].close - currentEma) * multiplier + currentEma;
    result.push({
      time: bars[i].time,
      value: Number(currentEma.toFixed(2)),
    });
  }
  return result;
}

export function computeRSI(bars: BarData[], period: number = 14): LinePoint[] {
  if (bars.length <= period || period <= 0) return [];
  const result: LinePoint[] = [];

  let gains = 0;
  let losses = 0;

  for (let i = 1; i <= period; i++) {
    const diff = bars[i].close - bars[i - 1].close;
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }

  let avgGain = gains / period;
  let avgLoss = losses / period;

  const firstRs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  const firstRsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + firstRs);
  result.push({ time: bars[period].time, value: Number(firstRsi.toFixed(2)) });

  for (let i = period + 1; i < bars.length; i++) {
    const diff = bars[i].close - bars[i - 1].close;
    const currentGain = diff > 0 ? diff : 0;
    const currentLoss = diff < 0 ? -diff : 0;

    avgGain = (avgGain * (period - 1) + currentGain) / period;
    avgLoss = (avgLoss * (period - 1) + currentLoss) / period;

    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + rs);
    result.push({
      time: bars[i].time,
      value: Number(rsi.toFixed(2)),
    });
  }
  return result;
}

export function computeMACD(
  bars: BarData[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): MACDResult {
  const fastEma = computeEMA(bars, fastPeriod);
  const slowEma = computeEMA(bars, slowPeriod);

  // Map slow EMA times
  const slowMap = new Map<string | number, number>();
  for (const pt of slowEma) {
    slowMap.set(pt.time, pt.value);
  }

  const macdRaw: LinePoint[] = [];
  for (const pt of fastEma) {
    if (slowMap.has(pt.time)) {
      const slowVal = slowMap.get(pt.time)!;
      macdRaw.push({
        time: pt.time,
        value: Number((pt.value - slowVal).toFixed(2)),
      });
    }
  }

  // Signal line is EMA of macdRaw
  const pseudoBars: BarData[] = macdRaw.map((m) => ({
    time: m.time,
    open: m.value,
    high: m.value,
    low: m.value,
    close: m.value,
  }));

  const signalLine = computeEMA(pseudoBars, signalPeriod);
  const signalMap = new Map<string | number, number>();
  for (const s of signalLine) {
    signalMap.set(s.time, s.value);
  }

  const macdLine: LinePoint[] = [];
  const histogram: HistogramPoint[] = [];

  for (const m of macdRaw) {
    if (signalMap.has(m.time)) {
      const sig = signalMap.get(m.time)!;
      const histVal = Number((m.value - sig).toFixed(2));
      macdLine.push(m);
      histogram.push({
        time: m.time,
        value: histVal,
        color: histVal >= 0 ? "rgba(0, 192, 118, 0.6)" : "rgba(255, 77, 79, 0.6)",
      });
    }
  }

  return {
    macdLine,
    signalLine,
    histogram,
  };
}

export function computeVWAP(bars: BarData[]): LinePoint[] {
  if (bars.length === 0) return [];
  const result: LinePoint[] = [];

  let cumulativeTypicalPriceVolume = 0;
  let cumulativeVolume = 0;

  for (const bar of bars) {
    const vol = bar.volume || 1;
    const typicalPrice = (bar.high + bar.low + bar.close) / 3;
    cumulativeTypicalPriceVolume += typicalPrice * vol;
    cumulativeVolume += vol;

    const vwap = cumulativeVolume > 0 ? cumulativeTypicalPriceVolume / cumulativeVolume : bar.close;
    result.push({
      time: bar.time,
      value: Number(vwap.toFixed(2)),
    });
  }

  return result;
}
