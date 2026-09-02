import {
  ConstituentHeatmapItem,
  MarketBreadth,
  WeightingSource,
} from "./types";

export function calculateMarketBreadth(
  items: { changePct: number; weight?: number }[]
): MarketBreadth {
  const totalCount = items.length;
  if (totalCount === 0) {
    return {
      totalCount: 0,
      advances: 0,
      declines: 0,
      unchanged: 0,
      advanceDeclineRatio: 1.0,
      pctAbovePrevClose: 0.0,
      weightedBreadth: 0.0,
      sentimentPosture: "Neutral",
    };
  }

  const advances = items.filter((i) => i.changePct > 0).length;
  const declines = items.filter((i) => i.changePct < 0).length;
  const unchanged = items.filter((i) => i.changePct === 0).length;

  const adRatio = Number((advances / Math.max(declines, 1)).toFixed(2));
  const pctPositive = Number(((advances / totalCount) * 100).toFixed(1));

  let totalWeight = 0;
  let weightedSum = 0;
  items.forEach((i) => {
    const wt = i.weight ?? (100.0 / totalCount);
    totalWeight += wt;
    weightedSum += wt * i.changePct;
  });

  const weightedBreadth = totalWeight > 0
    ? Number((weightedSum / totalWeight).toFixed(2))
    : 0.0;

  let posture: MarketBreadth["sentimentPosture"] = "Neutral";
  if (pctPositive >= 70.0) {
    posture = "Strong Bullish";
  } else if (pctPositive >= 55.0) {
    posture = "Moderate Bullish";
  } else if (pctPositive >= 45.0) {
    posture = "Neutral";
  } else if (pctPositive >= 30.0) {
    posture = "Moderate Bearish";
  } else {
    posture = "Strong Bearish";
  }

  return {
    totalCount,
    advances,
    declines,
    unchanged,
    advanceDeclineRatio: adRatio,
    pctAbovePrevClose: pctPositive,
    weightedBreadth,
    sentimentPosture: posture,
  };
}

export function handleMissingWeights(
  rawItems: {
    symbol: string;
    sector: string;
    weight?: number | null;
    changePct: number;
    ltp: number;
    volume?: number;
    weightingSource?: WeightingSource;
  }[]
): { cellTotalWeight: number; constituents: ConstituentHeatmapItem[] } {
  if (rawItems.length === 0) {
    return { cellTotalWeight: 0, constituents: [] };
  }

  const knownSum = rawItems.reduce((acc, curr) => {
    return acc + (curr.weight !== undefined && curr.weight !== null && curr.weight > 0 ? curr.weight : 0);
  }, 0);

  const unweightedCount = rawItems.filter(
    (i) => i.weight === undefined || i.weight === null || i.weight <= 0
  ).length;

  const assignedFallbackWeight =
    unweightedCount > 0
      ? Number((Math.max(0, 100 - knownSum) / unweightedCount).toFixed(4))
      : 0;

  const constituents: ConstituentHeatmapItem[] = rawItems.map((item) => {
    const isMissing =
      item.weight === undefined || item.weight === null || item.weight <= 0;
    const finalWeight = isMissing ? assignedFallbackWeight : item.weight!;
    const source: WeightingSource = isMissing
      ? "FALLBACK_EQUAL_WEIGHT"
      : item.weightingSource || "OFFICIAL_NSE";

    return {
      symbol: item.symbol,
      sector: item.sector,
      weight: Number(finalWeight.toFixed(2)),
      isWeightFallback: isMissing,
      weightingSource: source,
      changePct: item.changePct,
      ltp: item.ltp,
      volume: item.volume || 0,
    };
  });

  // Ensure total sum strictly equals 100.0%
  const currentTotal = constituents.reduce((acc, c) => acc + c.weight, 0);
  if (currentTotal > 0 && constituents.length > 0) {
    const diff = Number((100 - currentTotal).toFixed(2));
    constituents[0].weight = Number((constituents[0].weight + diff).toFixed(2));
  }

  const finalCellTotal = Number(
    constituents.reduce((acc, c) => acc + c.weight, 0).toFixed(2)
  );

  return {
    cellTotalWeight: finalCellTotal,
    constituents,
  };
}

export function getHeatmapTileColor(changePct: number): string {
  if (changePct >= 3.0) return "rgba(16, 185, 129, 0.9)"; // Strong green
  if (changePct >= 1.0) return "rgba(16, 185, 129, 0.65)"; // Medium green
  if (changePct >= 0.2) return "rgba(16, 185, 129, 0.35)"; // Mild green
  if (changePct > -0.2) return "rgba(100, 116, 139, 0.25)"; // Neutral slate
  if (changePct > -1.0) return "rgba(239, 68, 68, 0.35)"; // Mild red
  if (changePct > -3.0) return "rgba(239, 68, 68, 0.65)"; // Medium red
  return "rgba(239, 68, 68, 0.9)"; // Strong red
}
