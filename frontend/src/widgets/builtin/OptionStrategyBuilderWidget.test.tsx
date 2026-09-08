import { describe, expect, it } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import {
  OptionStrategyBuilderWidget,
  optionStrategyBuilderDefinition,
} from "./OptionStrategyBuilderWidget";
import { defaultWebSocketClient } from "../../websocket/client";

describe("OptionStrategyBuilderWidget Component (Sensibull Grade)", () => {
  it("renders Sensibull scorecard metrics and strategy legs", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE", defaultStrategyTemplate: "BUY_CALL" }}
      />
    );

    // Header and Underlying
    expect(screen.getByText("RELIANCE")).toBeDefined();
    expect(screen.getAllByText(/Feed/i).length).toBeGreaterThan(0);

    // Scorecard metrics
    expect(screen.getByText("Max Profit ⓘ")).toBeDefined();
    expect(screen.getByText("Max Loss ⓘ")).toBeDefined();
    expect(screen.getByText("Breakeven")).toBeDefined();
    expect(screen.getByText("POP ⓘ")).toBeDefined();
    expect(screen.getByText("Time Value ⓘ")).toBeDefined();
    expect(screen.getByText("Intrinsic Value ⓘ")).toBeDefined();
    expect(screen.getByText("Standalone Funds ⓘ")).toBeDefined();
    expect(screen.getByText("Standalone Margin ⓘ")).toBeDefined();

    // Payoff Graph and Controls
    expect(screen.getByText("Payoff Graph")).toBeDefined();
    expect(screen.getByText("P&L Table")).toBeDefined();
    expect(screen.getByText("On Expiry")).toBeDefined();
    expect(screen.getByText("On Target Date")).toBeDefined();
    expect(screen.getByText("🔍 Zoom Out")).toBeDefined();

    // Greek labels
    expect(screen.getByText("Delta ⓘ")).toBeDefined();
    expect(screen.getByText("Theta ⓘ")).toBeDefined();
    expect(screen.getByText("Gamma ⓘ")).toBeDefined();
    expect(screen.getByText("Vega ⓘ")).toBeDefined();

    // Ready-made strategies
    expect(screen.getByText("Ready-made")).toBeDefined();
    expect(screen.getByText("Bullish")).toBeDefined();
    expect(screen.getByText("Bearish")).toBeDefined();
    expect(screen.getByText("Neutral")).toBeDefined();
  });

  it("applies Bull Call Spread template and updates legs", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE" }}
      />
    );

    // Click Bull Call Spread card
    const bcsCard = screen.getByTestId("strategy-card-BULL_CALL_SPREAD");
    fireEvent.click(bcsCard);

    // Bull Call spread has 2 CALL legs
    expect(screen.getAllByText("CALL").length).toBe(2);
    expect(screen.getByText("2 selected - Bull Call Spread")).toBeDefined();
  });

  it("toggles and disables leg dynamically", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE" }}
      />
    );

    const legCheckboxes = screen.getAllByLabelText(/Toggle leg/i);
    expect(legCheckboxes.length).toBeGreaterThan(0);

    const firstLeg = legCheckboxes[0];
    expect(firstLeg).toBeChecked();

    fireEvent.click(firstLeg);
    expect(firstLeg).not.toBeChecked();
  });

  it("adds and deletes option legs", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE" }}
      />
    );

    const addBtn = screen.getByText("+ Add Option Leg");
    fireEvent.click(addBtn);

    // Find delete buttons
    const deleteButtons = screen.getAllByText("✕");
    const countBefore = deleteButtons.length;
    expect(countBefore).toBeGreaterThan(0);

    fireEvent.click(deleteButtons[deleteButtons.length - 1]);
    expect(screen.getAllByText("✕").length).toBe(countBefore - 1);
  });

  it("responds to live feed ticks dynamically", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE" }}
      />
    );

    // Dispatch a live tick for RELIANCE
    act(() => {
      defaultWebSocketClient.dispatchTick({
        symbol: "RELIANCE",
        ltp: 1320.5,
        change: 25.6,
        changePct: 1.98,
        volume: 85000,
        timestamp: Date.now(),
      });
    });

    // Spot price should now reflect 1320.50 and +1.98%
    expect(screen.getByText("1320.50")).toBeDefined();
    expect(screen.getByText("+1.98%")).toBeDefined();
  });

  it("interacts with target price and target date sliders", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "RELIANCE" }}
      />
    );

    const priceSlider = screen.getByLabelText("Target Price Slider");
    fireEvent.change(priceSlider, { target: { value: "1350" } });
    expect(screen.getAllByDisplayValue("1350").length).toBeGreaterThanOrEqual(1);

    const dateSlider = screen.getByLabelText("Target Date Slider");
    fireEvent.change(dateSlider, { target: { value: "10" } });
    expect(screen.getByText(/Day \+10/)).toBeDefined();
  });

  it("has valid widget definition metadata", () => {
    expect(optionStrategyBuilderDefinition.id).toBe("option-strategy-builder");
    expect(optionStrategyBuilderDefinition.title).toBe("Multi-Leg Option Strategy Builder");
    expect(optionStrategyBuilderDefinition.category).toBe("analytics");
  });
});
