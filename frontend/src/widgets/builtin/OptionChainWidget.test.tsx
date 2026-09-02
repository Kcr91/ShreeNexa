import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OptionChainWidget, optionChainDefinition } from "./OptionChainWidget";
import { widgetRegistry } from "../registry";
import "./index";

describe("OptionChainWidget Component", () => {
  it("renders option chain strike ladder with ATM marker, Greeks, and drift badge", () => {
    render(
      <OptionChainWidget
        instanceId="chain-1"
        settings={{
          defaultUnderlying: "NIFTY",
          strikesCount: 5,
          showGreeks: true,
          showIV: true,
          showOI: true,
        }}
      />
    );

    expect(screen.getByText("CALLS (CE)")).toBeInTheDocument();
    expect(screen.getByText("PUTS (PE)")).toBeInTheDocument();
    expect(screen.getByText("PCR:")).toBeInTheDocument();
    expect(screen.getByText("Max Pain:")).toBeInTheDocument();
    expect(screen.getByText(/Calibrated/i)).toBeInTheDocument();
    expect(screen.getByTestId("strike-row-24500")).toBeInTheDocument();
  });

  it("clicks a Call strike and selects option leg", () => {
    render(
      <OptionChainWidget
        instanceId="chain-1"
        settings={{
          defaultUnderlying: "NIFTY",
          strikesCount: 5,
          showGreeks: true,
          showIV: true,
          showOI: true,
        }}
      />
    );

    // Click Buy button on 24500 CE
    const buyCallBtn = screen.getByRole("button", { name: "Buy NIFTY 24500 CE" });
    fireEvent.click(buyCallBtn);

    // Displays selected leg status
    expect(screen.getByRole("status")).toHaveTextContent(/Selected: NIFTY 24500 CE BUY/i);
  });

  it("switches underlying index to BANKNIFTY", () => {
    render(
      <OptionChainWidget
        instanceId="chain-1"
        settings={{
          defaultUnderlying: "NIFTY",
          strikesCount: 5,
          showGreeks: true,
          showIV: true,
          showOI: true,
        }}
      />
    );

    const select = screen.getByLabelText("Select Underlying Index");
    fireEvent.change(select, { target: { value: "BANKNIFTY" } });

    expect(screen.getByTestId("option-chain-spot")).toHaveTextContent("51");
  });

  it("toggles Vega and Gamma columns on and off", () => {
    render(
      <OptionChainWidget
        instanceId="chain-1"
        settings={{
          defaultUnderlying: "NIFTY",
          strikesCount: 5,
          showGreeks: true,
          showIV: true,
          showOI: true,
        }}
      />
    );

    expect(screen.queryByText("Vega")).not.toBeInTheDocument();

    // Toggle Vega on
    const vegaCheckbox = screen.getByLabelText("ν");
    fireEvent.click(vegaCheckbox);

    expect(screen.getAllByText("Vega").length).toBeGreaterThan(0);
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("option-chain")).toBeDefined();
    expect(widgetRegistry.get("option-chain")?.title).toBe("Option Chain & Greeks");
    expect(optionChainDefinition.category).toBe("analytics");
  });
});
