import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  OptionStrategyBuilderWidget,
  optionStrategyBuilderDefinition,
} from "./OptionStrategyBuilderWidget";

describe("OptionStrategyBuilderWidget Component", () => {
  it("renders default Iron Condor legs and KPI cards", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "NIFTY" }}
      />
    );

    expect(screen.getByText("NET PREMIUM")).toBeDefined();
    expect(screen.getByText("MAX PROFIT")).toBeDefined();
    expect(screen.getByText("MAX LOSS")).toBeDefined();
    expect(screen.getByText("REQUIRED MARGIN")).toBeDefined();
    expect(screen.getByText("BREAKEVENS")).toBeDefined();
    expect(screen.getByText("NET GREEKS")).toBeDefined();
    expect(screen.getByText("+ Add Option Leg")).toBeDefined();
  });

  it("applies Bull Call Spread template", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "NIFTY" }}
      />
    );

    const templateSelect = screen.getByLabelText("Select Strategy Template");
    fireEvent.change(templateSelect, { target: { value: "BULL_CALL_SPREAD" } });

    expect(screen.getAllByText("CALL").length).toBe(2);
    expect(screen.getByText("Debit ₹1500")).toBeDefined();
  });

  it("toggles and disables leg dynamically", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "NIFTY" }}
      />
    );

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBe(4);

    // Toggle off leg 1
    fireEvent.click(checkboxes[0]);
    expect(checkboxes[0]).not.toBeChecked();
  });

  it("adds and deletes option legs", () => {
    render(
      <OptionStrategyBuilderWidget
        instanceId="opt-builder-1"
        settings={{ defaultUnderlying: "NIFTY" }}
      />
    );

    const addBtn = screen.getByText("+ Add Option Leg");
    fireEvent.click(addBtn);

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBe(5);

    const deleteButtons = screen.getAllByText("✕");
    fireEvent.click(deleteButtons[deleteButtons.length - 1]);

    expect(screen.getAllByRole("checkbox").length).toBe(4);
  });

  it("has valid widget definition metadata", () => {
    expect(optionStrategyBuilderDefinition.id).toBe("option-strategy-builder");
    expect(optionStrategyBuilderDefinition.title).toBe("Multi-Leg Option Strategy Builder");
    expect(optionStrategyBuilderDefinition.category).toBe("analytics");
  });
});
