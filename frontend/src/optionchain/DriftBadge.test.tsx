import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DriftBadge, CalibrationReportData } from "./DriftBadge";

describe("DriftBadge Component", () => {
  const mockCalibratedReport: CalibrationReportData = {
    underlying: "NIFTY",
    expiryDate: "2026-09-17",
    status: "CALIBRATED",
    forwardSourceFitted: "SYNTHETIC_PCP",
    forwardPriceUsed: 25080.0,
    thetaRmse: 0.04,
    thetaMae: 0.03,
    deltaMae: 0.01,
    ivMae: 0.005,
    maxThetaDriftPct: 2.1,
    reconciledStrikesCount: 26,
    totalStrikesEvaluated: 30,
    excludedStrikesCount: 4,
    driftBadgeText: "🟢 Calibrated (Theta Error 0.04)",
    bestConvention: {
      dayCount: "ACT_365",
      timeMode: "CALENDAR_HOURS_TO_CLOSE",
      riskFreeRate: 0.07,
      annualizationFactor: 365,
    },
    exclusionSummary: {
      ZERO_LIQUIDITY: 2,
      WIDE_SPREAD: 1,
      DEEP_OTM_ITM: 1,
    },
  };

  it("renders calibrated badge status and opens inspection popover", () => {
    render(<DriftBadge underlying="NIFTY" report={mockCalibratedReport} />);

    expect(screen.getByText(/Calibrated/i)).toBeDefined();

    // Click button to open details popover
    const badgeButton = screen.getByRole("button");
    fireEvent.click(badgeButton);

    expect(screen.getByText("Black-76 Calibration Status")).toBeDefined();
    expect(screen.getByText(/SYNTHETIC_PCP/i)).toBeDefined();
    expect(screen.getByText(/26 \/ 30 strikes/i)).toBeDefined();
    expect(screen.getByText(/ZERO_LIQUIDITY: 2/i)).toBeDefined();
  });

  it("renders warning and drift detected status badges", () => {
    const warningReport: CalibrationReportData = {
      ...mockCalibratedReport,
      status: "WARNING",
      thetaMae: 0.45,
      maxThetaDriftPct: 12.4,
    };

    const { rerender } = render(<DriftBadge underlying="NIFTY" report={warningReport} />);
    expect(screen.getByText(/Minor Drift/i)).toBeDefined();

    const driftReport: CalibrationReportData = {
      ...mockCalibratedReport,
      status: "DRIFT_DETECTED",
      thetaMae: 1.25,
      maxThetaDriftPct: 22.0,
    };

    rerender(<DriftBadge underlying="NIFTY" report={driftReport} />);
    expect(screen.getByText(/Drift Detected/i)).toBeDefined();
  });

  it("triggers onRecalibrate callback when clicking recalibrate button", () => {
    const onRecalibrate = vi.fn();
    render(
      <DriftBadge
        underlying="NIFTY"
        report={mockCalibratedReport}
        onRecalibrate={onRecalibrate}
      />
    );

    // Open popover
    const badgeButton = screen.getByRole("button");
    fireEvent.click(badgeButton);

    // Click Recalibrate
    const recalibrateBtn = screen.getByText(/Recalibrate Dhan Chain Now/i);
    fireEvent.click(recalibrateBtn);

    expect(onRecalibrate).toHaveBeenCalledTimes(1);
  });
});
