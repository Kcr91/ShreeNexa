import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AIDraftModal } from "./AIDraftModal";
import { StrategyBuilderState } from "./types";

const mockCurrentState: StrategyBuilderState = {
  strategyName: "Current Workspace Strategy",
  universe: "NIFTY 50",
  timeframe: "15m",
  indicators: [
    { id: "ind-1", name: "current_ema", function: "ema", params: { period: 20 } },
  ],
  rules: [
    {
      id: "rule-1",
      name: "Current Entry",
      type: "ENTRY_LONG",
      combinator: "AND",
      conditions: [
        { id: "c-1", leftOperand: "close", operator: "GREATER_THAN", rightOperand: "current_ema" },
      ],
    },
  ],
  stopLossPct: 1.0,
  takeProfitPct: 2.0,
};

describe("AIDraftModal Component (F5.3)", () => {
  it("renders modal with prompt input and invariant badges", () => {
    render(
      <AIDraftModal
        isOpen={true}
        onClose={vi.fn()}
        currentState={mockCurrentState}
        onApprove={vi.fn()}
      />
    );

    expect(screen.getByTestId("ai-draft-modal")).toBeInTheDocument();
    expect(screen.getByTestId("badge-draft-status")).toHaveTextContent("Status: DRAFT ONLY");
    expect(screen.getByTestId("badge-deployment-state")).toHaveTextContent(
      "Deployment: UNTOUCHED / DISABLED"
    );
    expect(screen.getByTestId("ai-prompt-input")).toBeInTheDocument();
    expect(screen.getByTestId("btn-generate-draft")).toBeInTheDocument();
  });

  it("generates draft, displays diff, explanation, and warnings", async () => {
    render(
      <AIDraftModal
        isOpen={true}
        onClose={vi.fn()}
        currentState={mockCurrentState}
        onApprove={vi.fn()}
      />
    );

    const input = screen.getByTestId("ai-prompt-input");
    fireEvent.change(input, {
      target: { value: "Buy when 9 EMA crosses above 21 EMA on NIFTY 50 15m" },
    });

    const generateBtn = screen.getByTestId("btn-generate-draft");
    fireEvent.click(generateBtn);

    // Wait for draft content
    await waitFor(() => {
      expect(screen.getByTestId("ai-draft-content")).toBeInTheDocument();
    });

    // 1. Verify Diff view
    expect(screen.getByTestId("diff-container")).toBeInTheDocument();
    expect(screen.getByText("Current Workspace Strategy")).toBeInTheDocument();
    expect(screen.getByText(/Proposed AI Draft/i)).toBeInTheDocument();

    // 2. Tab switch to Explanation
    const explanationTab = screen.getByTestId("tab-explanation");
    fireEvent.click(explanationTab);
    expect(screen.getByTestId("explanation-container")).toBeInTheDocument();

    // 3. Tab switch to Warnings
    const warningsTab = screen.getByTestId("tab-warnings");
    fireEvent.click(warningsTab);
    expect(screen.getByTestId("warnings-container")).toBeInTheDocument();
  });

  it("proof: clicking reject discards draft and preserves original state without approval", async () => {
    const handleClose = vi.fn();
    const handleApprove = vi.fn();

    render(
      <AIDraftModal
        isOpen={true}
        onClose={handleClose}
        currentState={mockCurrentState}
        onApprove={handleApprove}
      />
    );

    // Trigger generation
    const input = screen.getByTestId("ai-prompt-input");
    fireEvent.change(input, { target: { value: "Momentum RSI strategy" } });
    fireEvent.click(screen.getByTestId("btn-generate-draft"));

    await waitFor(() => {
      expect(screen.getByTestId("ai-draft-content")).toBeInTheDocument();
    });

    // Click Reject
    const rejectBtn = screen.getByTestId("btn-reject-draft");
    fireEvent.click(rejectBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
    expect(handleApprove).not.toHaveBeenCalled();
  });

  it("proof: clicking approve applies draft to the workspace", async () => {
    const handleClose = vi.fn();
    const handleApprove = vi.fn();

    render(
      <AIDraftModal
        isOpen={true}
        onClose={handleClose}
        currentState={mockCurrentState}
        onApprove={handleApprove}
      />
    );

    const input = screen.getByTestId("ai-prompt-input");
    fireEvent.change(input, { target: { value: "Supertrend strategy" } });
    fireEvent.click(screen.getByTestId("btn-generate-draft"));

    await waitFor(() => {
      expect(screen.getByTestId("btn-approve-draft")).toBeInTheDocument();
    });

    const approveBtn = screen.getByTestId("btn-approve-draft");
    fireEvent.click(approveBtn);

    expect(handleApprove).toHaveBeenCalledTimes(1);
    const appliedState = handleApprove.mock.calls[0][0] as StrategyBuilderState;
    expect(appliedState.universe).toBe("NIFTY 50");
    expect(appliedState.stopLossPct).toBeGreaterThan(0);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("proof: clicking approve & one-click backtest triggers execution with metadata", async () => {
    const handleClose = vi.fn();
    const handleApprove = vi.fn();
    const handleApproveAndBacktest = vi.fn();

    render(
      <AIDraftModal
        isOpen={true}
        onClose={handleClose}
        currentState={mockCurrentState}
        onApprove={handleApprove}
        onApproveAndBacktest={handleApproveAndBacktest}
      />
    );

    const input = screen.getByTestId("ai-prompt-input");
    fireEvent.change(input, { target: { value: "EMA crossover backtest prompt" } });
    fireEvent.click(screen.getByTestId("btn-generate-draft"));

    await waitFor(() => {
      expect(screen.getByTestId("btn-approve-backtest")).toBeInTheDocument();
    });

    const backtestBtn = screen.getByTestId("btn-approve-backtest");
    fireEvent.click(backtestBtn);

    expect(handleApproveAndBacktest).toHaveBeenCalledTimes(1);
    const [draftState, payload] = handleApproveAndBacktest.mock.calls[0];
    expect(draftState.universe).toBe("NIFTY 50");
    expect(payload.strategy_ir.ir_version).toBe(1);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
