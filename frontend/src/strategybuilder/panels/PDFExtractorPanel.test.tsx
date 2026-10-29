import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PDFExtractorPanel } from "./PDFExtractorPanel";
import * as svc from "../pdfExtractService";
import { StrategyBuilderState } from "../types";

const sampleResult: svc.ExtractionResult = {
  success: true,
  extracted_text: "Buy when 9 EMA crosses above 21 EMA. Stop loss 1.5%.",
  strategy_ir: {
    ir_version: 1,
    name: "Test",
    kind: "stock",
    horizon: "intraday",
    strategy_type: "trend_following",
    universe: { type: "index", index_name: "NIFTY 50" },
    timeframe: "15m",
    indicators: { ema_9: { fn: "EMA", params: { period: 9 } } },
    entries: [],
    exits: [{ id: "exit-sl", type: "stop", pct: 1.5 }, { id: "exit-tp", type: "target", pct: 2 }],
    sizing: { type: "fixed_value", value: 50000 },
    risk: { max_positions: 5, no_trade_windows: [] },
  },
  extraction_report: {
    name: "Test",
    confidence: "high",
    components_found: {
      indicators: [{ description: "EMA(9)", confidence: "high", source_text: "9-period exponential" }],
      entry_conditions: [],
      exit_conditions: [],
      timeframe: { description: "15m", confidence: "medium", source_text: "15-minute" },
      risk_params: [{ description: "Stop loss 1.5%", confidence: "high", source_text: "stop loss 1.5%" }],
    },
    warnings: ["No entry conditions detected."],
  },
};

describe("PDFExtractorPanel", () => {
  it("renders upload UI when open", () => {
    render(<PDFExtractorPanel isOpen={true} onClose={() => {}} onLoad={() => {}} />);
    expect(screen.getByTestId("pdf-extractor-modal")).toBeInTheDocument();
    expect(screen.getByTestId("pdf-file-input")).toBeInTheDocument();
    expect(screen.getByTestId("pdf-text-input")).toBeInTheDocument();
  });

  it("extracts from pasted text and shows review with components", async () => {
    const spy = vi.spyOn(svc, "extractFromText").mockResolvedValue(sampleResult);
    render(<PDFExtractorPanel isOpen={true} onClose={() => {}} onLoad={() => {}} />);

    const textarea = screen.getByTestId("pdf-text-input");
    fireEvent.change(textarea, { target: { value: "Some strategy text" } });
    fireEvent.click(screen.getByRole("button", { name: /Extract from Text/i }));

    await waitFor(() => expect(spy).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId("pdf-review")).toBeInTheDocument());
    expect(screen.getByText("EMA(9)")).toBeInTheDocument();
    expect(screen.getByText(/No entry conditions detected/)).toBeInTheDocument();
    spy.mockRestore();
  });

  it("loads decompiled state into the builder on 'Load into Builder'", async () => {
    const spy = vi.spyOn(svc, "extractFromText").mockResolvedValue(sampleResult);
    let received: StrategyBuilderState | null = null;
    render(
      <PDFExtractorPanel
        isOpen={true}
        onClose={() => {}}
        onLoad={(s) => {
          received = s;
        }}
      />
    );
    fireEvent.change(screen.getByTestId("pdf-text-input"), { target: { value: "Some strategy text" } });
    fireEvent.click(screen.getByRole("button", { name: /Extract from Text/i }));
    await waitFor(() => expect(screen.getByTestId("pdf-load-builder")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("pdf-load-builder"));

    expect(received).not.toBeNull();
    expect(received!.strategyName).toBe("Test");
    expect(received!.timeframe).toBe("15m");
    expect(received!.indicators.length).toBeGreaterThanOrEqual(1);
    spy.mockRestore();
  });

  it("shows error state when extraction service rejects", async () => {
    const spy = vi.spyOn(svc, "extractFromText").mockRejectedValue(new Error("Something broke"));
    render(<PDFExtractorPanel isOpen={true} onClose={() => {}} onLoad={() => {}} />);
    fireEvent.change(screen.getByTestId("pdf-text-input"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /Extract from Text/i }));
    await waitFor(() => expect(screen.getByTestId("pdf-error")).toBeInTheDocument());
    expect(screen.getByTestId("pdf-error")).toHaveTextContent(/Something broke/);
    spy.mockRestore();
  });

  it("rejects non-pdf files", () => {
    render(<PDFExtractorPanel isOpen={true} onClose={() => {}} onLoad={() => {}} />);
    const input = screen.getByTestId("pdf-file-input") as HTMLInputElement;
    const nonPdf = new File(["x"], "readme.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", { value: [nonPdf] });
    fireEvent.change(input);
    expect(screen.getByText(/Only \.pdf files are accepted/i)).toBeInTheDocument();
  });
});
