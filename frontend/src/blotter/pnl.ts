import { PositionItem, PortfolioSummary } from "./types";

export function computePositionPnl(pos: PositionItem, currentLtp?: number): PositionItem {
  const ltp = currentLtp !== undefined ? currentLtp : pos.ltp;
  const unrealizedPnl = Number(((ltp - pos.buyAvgPrice) * pos.quantity).toFixed(2));
  const totalPnl = Number((unrealizedPnl + pos.realizedPnl).toFixed(2));
  const dayChange = Number((ltp - pos.buyAvgPrice).toFixed(2));
  const dayChangePct = pos.buyAvgPrice > 0 ? Number(((dayChange / pos.buyAvgPrice) * 100).toFixed(2)) : 0;

  return {
    ...pos,
    ltp,
    dayChange,
    dayChangePct,
    unrealizedPnl,
    totalPnl,
  };
}

export function computePortfolioSummary(
  positions: PositionItem[],
  activeOrdersCount: number = 0
): PortfolioSummary {
  let totalInvested = 0;
  let totalUnrealizedPnl = 0;
  let totalRealizedPnl = 0;
  let openPositionsCount = 0;

  for (const pos of positions) {
    if (pos.quantity !== 0) {
      openPositionsCount += 1;
      totalInvested += Math.abs(pos.quantity) * pos.buyAvgPrice;
    }
    totalUnrealizedPnl += pos.unrealizedPnl;
    totalRealizedPnl += pos.realizedPnl;
  }

  const netPnl = Number((totalUnrealizedPnl + totalRealizedPnl).toFixed(2));

  return {
    totalInvested: Number(totalInvested.toFixed(2)),
    totalUnrealizedPnl: Number(totalUnrealizedPnl.toFixed(2)),
    totalRealizedPnl: Number(totalRealizedPnl.toFixed(2)),
    netPnl,
    openPositionsCount,
    activeOrdersCount,
  };
}
