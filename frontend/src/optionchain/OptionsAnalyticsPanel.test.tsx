import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  OptionsAnalyticsPanel,
  optionsAnalyticsDefinition,
} from "./OptionsAnalyticsPanel";

describe("OptionsAnalyticsPanel Component", () => {
  it("renders top KPIs and default Volatility Skew & Smile tab", () => {
    render(
      <OptionsAnalyticsPanel
        instanceId="opt-analytics-1"
        settings={{ underlying: "NIFTY", defaultTab: "skew" }}
      />
    );

    expect(screen.getByText("ATM IV:")).toBeDefined();
    expect(screen.getByText("PCR (OI):")).toBeDefined();
    expect(screen.getByText("Max Pain:")).toBeDefined();
    expect(screen.getByTestId("tab-skew")).toBeDefined();
    expect(screen.getByText(/25Δ Risk Reversal:/i)).toBeDefined();
    expect(screen.getByText(/25Δ Butterfly:/i)).toBeDefined();
  });

  it("switches to Term Structure tab and displays regime and points", () => {
    render(
      <OptionsAnalyticsPanel
        instanceId="opt-analytics-1"
        settings={{ underlying: "NIFTY" }}
      />
    );

    const termTabBtn = screen.getByText(/Term Structure/i);
    fireEvent.click(termTabBtn);

    expect(screen.getByTestId("tab-term")).toBeDefined();
    expect(screen.getByText("CONTANGO")).toBeDefined();
    expect(screen.getByText("2026-09-10")).toBeDefined();
  });

  it("switches to Max Pain tab and displays loss curve", () => {
    render(
      <OptionsAnalyticsPanel
        instanceId="opt-analytics-1"
        settings={{ underlying: "NIFTY" }}
      />
    );

    const maxPainTabBtn = screen.getByText(/Max Pain & Loss Curve/i);
    fireEvent.click(maxPainTabBtn);

    expect(screen.getByTestId("tab-maxpain")).toBeDefined();
    expect(screen.getByText("Max Pain Theory Expiration Settlement")).toBeDefined();
    expect(screen.getAllByText(/Max Pain/i).length).toBeGreaterThan(0);
  });

  it("switches to IV Rank & Percentile tab", () => {
    render(
      <OptionsAnalyticsPanel
        instanceId="opt-analytics-1"
        settings={{ underlying: "NIFTY" }}
      />
    );

    const ivRankTabBtn = screen.getByText(/IV Rank & Percentile/i);
    fireEvent.click(ivRankTabBtn);

    expect(screen.getByTestId("tab-ivrank")).toBeDefined();
    expect(screen.getByText("IV Rank (52-Week)")).toBeDefined();
    expect(screen.getByText("IV Percentile")).toBeDefined();
    expect(screen.getByText(/Trading Context:/i)).toBeDefined();
  });

  it("has valid widget definition metadata", () => {
    expect(optionsAnalyticsDefinition.id).toBe("options-analytics");
    expect(optionsAnalyticsDefinition.title).toBe("Options Analytics & Volatility");
    expect(optionsAnalyticsDefinition.category).toBe("analytics");
  });
});
