import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PaperTradingWidget, paperTradingDefinition } from "./PaperTradingWidget";

describe("PaperTradingWidget", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders widget header metrics and reconciled indicator", () => {
    render(
      <PaperTradingWidget
        instanceId="test-paper"
        settings={{ accountId: "test-acc", defaultTab: "POSITIONS" }}
      />
    );

    expect(screen.getByText("Account Equity")).toBeInTheDocument();
    expect(screen.getByText("Cash Available")).toBeInTheDocument();
    expect(screen.getAllByText("Realized P&L")[0]).toBeInTheDocument();
    expect(screen.getByText("Live MTM Unrealized")).toBeInTheDocument();
    expect(screen.getByText("Statutory Costs")).toBeInTheDocument();
    expect(screen.getByText("🟢 Reconciled")).toBeInTheDocument();
  });

  it("displays open positions and live MTM on POSITIONS tab", () => {
    render(
      <PaperTradingWidget
        instanceId="test-paper"
        settings={{ accountId: "test-acc", defaultTab: "POSITIONS" }}
      />
    );

    expect(screen.getByText("TCS")).toBeInTheDocument();
    expect(screen.getByText("INFY")).toBeInTheDocument();
    expect(screen.getByText("+30")).toBeInTheDocument();
    expect(screen.getByText("+100")).toBeInTheDocument();
  });

  it("switches to ORDER_BOOK and displays rejection reason and cancel button", () => {
    render(
      <PaperTradingWidget
        instanceId="test-paper"
        settings={{ accountId: "test-acc", defaultTab: "POSITIONS" }}
      />
    );

    const orderBookTab = screen.getByRole("button", { name: /Order Book/i });
    fireEvent.click(orderBookTab);

    // Verify order statuses
    expect(screen.getAllByText("FILLED").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("REJECTED")).toBeInTheDocument();

    // Verify rejection reason display
    expect(screen.getByText(/Insufficient funds/i)).toBeInTheDocument();

    // Verify cancel action button for working orders
    const cancelBtn = screen.getByRole("button", { name: "Cancel" });
    expect(cancelBtn).toBeInTheDocument();
    fireEvent.click(cancelBtn);
  });

  it("switches to TRADE_BOOK and displays executed fills and statutory costs", () => {
    render(
      <PaperTradingWidget
        instanceId="test-paper"
        settings={{ accountId: "test-acc", defaultTab: "POSITIONS" }}
      />
    );

    const tradeBookTab = screen.getByRole("button", { name: /Trade Book/i });
    fireEvent.click(tradeBookTab);

    expect(screen.getByText("Fill ID")).toBeInTheDocument();
    expect(screen.getByText("Turnover")).toBeInTheDocument();
    expect(screen.getByText("Statutory Cost")).toBeInTheDocument();
    expect(screen.getByText("fill-1")).toBeInTheDocument();
  });

  it("switches to RECONCILIATION tab and displays mathematical invariants", () => {
    render(
      <PaperTradingWidget
        instanceId="test-paper"
        settings={{ accountId: "test-acc", defaultTab: "RECONCILIATION" }}
      />
    );

    expect(screen.getByText("Mathematical Accounting Invariants")).toBeInTheDocument();
    expect(screen.getByText("✓ Exact Parity (0.00 Discrepancy)")).toBeInTheDocument();
    expect(screen.getByText(/Rejected Orders & Pre-Trade Risk Violations/i)).toBeInTheDocument();
  });

  it("exports valid widget definition conforming to registry", () => {
    expect(paperTradingDefinition.id).toBe("paper_trading");
    expect(paperTradingDefinition.title).toBe("Paper Trading Blotter");
    expect(paperTradingDefinition.category).toBe("order");
    expect(paperTradingDefinition.schema.fields.length).toBeGreaterThanOrEqual(2);
  });
});
