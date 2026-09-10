import {
  ConstituentHeatmapItem,
  MarketBreadth,
  WeightingSource,
} from "./types";

export function calculateMarketBreadth(
  items: { changePct?: number; weight?: number }[]
): MarketBreadth {
  const valuedItems = items.filter(
    (item): item is { changePct: number; weight?: number } => typeof item.changePct === "number",
  );
  const totalCount = valuedItems.length;
  if (totalCount === 0) {
    return {
      totalCount: 0,
      advances: 0,
      declines: 0,
      unchanged: 0,
      advanceDeclineRatio: 0.0,
      pctAbovePrevClose: 0.0,
      weightedBreadth: 0.0,
      sentimentPosture: "Unavailable",
    };
  }

  const advances = valuedItems.filter((i) => i.changePct > 0).length;
  const declines = valuedItems.filter((i) => i.changePct < 0).length;
  const unchanged = valuedItems.filter((i) => i.changePct === 0).length;

  const adRatio = Number((advances / Math.max(declines, 1)).toFixed(2));
  const pctPositive = Number(((advances / totalCount) * 100).toFixed(1));

  let totalWeight = 0;
  let weightedSum = 0;
  valuedItems.forEach((i) => {
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
    changePct?: number;
    ltp?: number;
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
      volume: item.volume,
    };
  });

  // Ensure total sum strictly equals 100.0%
  const currentTotal = constituents.reduce((acc, c) => acc + c.weight, 0);
  if (currentTotal > 0 && Math.abs(currentTotal - 100) > 0.01 && constituents.length > 0) {
    const scale = 100.0 / currentTotal;
    constituents.forEach((c) => {
      c.weight = Number((c.weight * scale).toFixed(2));
    });
    const scaledTotal = constituents.reduce((acc, c) => acc + c.weight, 0);
    const residual = Number((100 - scaledTotal).toFixed(2));
    let maxIdx = 0;
    for (let i = 1; i < constituents.length; i++) {
      if (constituents[i].weight > constituents[maxIdx].weight) {
        maxIdx = i;
      }
    }
    constituents[maxIdx].weight = Number((constituents[maxIdx].weight + residual).toFixed(2));
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
  if (changePct > 0) {
    const intensity = Math.min(Math.abs(changePct) / 3.0, 1.0);
    const alpha = 0.35 + intensity * 0.55;
    return `rgba(16, 185, 129, ${alpha.toFixed(2)})`;
  } else if (changePct < 0) {
    const intensity = Math.min(Math.abs(changePct) / 3.0, 1.0);
    const alpha = 0.35 + intensity * 0.55;
    return `rgba(239, 68, 68, ${alpha.toFixed(2)})`;
  }
  return "rgba(100, 116, 139, 0.4)";
}

export function getNseColorBracket(changePct: number): "5" | "3" | "1" | "0" | "-1" | "-3" | "-5" {
  if (changePct >= 5.0) return "5";
  if (changePct >= 3.0) return "3";
  if (changePct > 0.0) return "1";
  if (changePct === 0.0) return "0";
  if (changePct > -3.0) return "-1";
  if (changePct > -5.0) return "-3";
  return "-5";
}

export function getNseColorForPct(changePct: number): string {
  // Official NSE India Heatmap Palette (Images 1 to 4)
  if (changePct >= 5.0) return "#0b7a3e"; // 5: Dark Green
  if (changePct >= 3.0) return "#28a745"; // 3: Medium Green
  if (changePct > 0.0) return "#58ba6d"; // 1: Light Green
  if (changePct === 0.0) return "#8e99a8"; // 0%: Slate Grey
  if (changePct > -3.0) return "#e87070"; // -1: Soft Coral / Light Red
  if (changePct > -5.0) return "#c9302c"; // -3: Medium Red
  return "#8b0000"; // -5: Dark Maroon Red
}
