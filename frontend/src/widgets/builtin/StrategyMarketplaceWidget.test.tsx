import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  StrategyMarketplaceWidget,
  strategyMarketplaceDefinition,
} from "./StrategyMarketplaceWidget";
import { NotificationProvider } from "../../notifications/NotificationContext";
import { widgetRegistry } from "../registry";
import "./index";

describe("StrategyMarketplaceWidget Component", () => {
  it("renders strategy cards and filters by category", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: false }}>
        <StrategyMarketplaceWidget
          instanceId="market-1"
          settings={{
            defaultCategory: "ALL",
            defaultAssetClass: "ALL",
          }}
        />
      </NotificationProvider>
    );

    expect(screen.getByText("NIFTY Weekly Iron Condor")).toBeInTheDocument();
    expect(screen.getByText("BankNifty Supertrend Breakout")).toBeInTheDocument();

    const optionsPill = screen.getByRole("button", { name: "Options Income" });
    fireEvent.click(optionsPill);

    expect(screen.getByText("NIFTY Weekly Iron Condor")).toBeInTheDocument();
    expect(screen.queryByText("BankNifty Supertrend Breakout")).not.toBeInTheDocument();
  });

  it("opens tear sheet modal on preview click and renders performance metrics", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: false }}>
        <StrategyMarketplaceWidget
          instanceId="market-1"
          settings={{
            defaultCategory: "ALL",
            defaultAssetClass: "ALL",
          }}
        />
      </NotificationProvider>
    );

    const previewBtns = screen.getAllByRole("button", { name: "Preview Tear Sheet" });
    fireEvent.click(previewBtns[0]);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Audited Performance Scorecard")).toBeInTheDocument();
    expect(screen.getByTestId("tearsheet-ir-code")).toBeInTheDocument();

    const closeBtn = screen.getByRole("button", { name: "Close modal" });
    fireEvent.click(closeBtn);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("clones strategy and updates button text", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: false }}>
        <StrategyMarketplaceWidget
          instanceId="market-1"
          settings={{
            defaultCategory: "ALL",
            defaultAssetClass: "ALL",
          }}
        />
      </NotificationProvider>
    );

    const cloneBtn = screen.getByTestId("clone-btn-nifty-iron-condor");
    fireEvent.click(cloneBtn);

    expect(cloneBtn).toHaveTextContent("✓ Cloned!");
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("strategy-marketplace")).toBeDefined();
    expect(widgetRegistry.get("strategy-marketplace")?.title).toBe("Strategy Marketplace");
    expect(strategyMarketplaceDefinition.category).toBe("analytics");
  });
});
