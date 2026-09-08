import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { HistoricDataWidget } from "./HistoricDataWidget";

describe("HistoricDataWidget Component", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.restoreAllMocks();

    fetchMock = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/v1/historical/bars")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            symbol: "RELIANCE",
            exchange_segment: "NSE_EQ",
            timeframe: "1d",
            data_source: "warehouse",
            summary: {
              total_bars: 2,
              first_timestamp: "2026-01-05T03:45:00Z",
              last_timestamp: "2026-01-06T03:45:00Z",
              high: 2980.5,
              low: 2940.0,
              total_volume: 1250000,
            },
            bars: [
              {
                timestamp: "2026-01-05T03:45:00Z",
                symbol: "RELIANCE",
                exchange_segment: "NSE_EQ",
                open: 2950.0,
                high: 2980.5,
                low: 2940.0,
                close: 2975.0,
                volume: 600000,
                open_interest: 0,
              },
              {
                timestamp: "2026-01-06T03:45:00Z",
                symbol: "RELIANCE",
                exchange_segment: "NSE_EQ",
                open: 2975.0,
                high: 2985.0,
                low: 2960.0,
                close: 2965.0,
                volume: 650000,
                open_interest: 0,
              },
            ],
          }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Not found" }),
      });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders panel header, scrip search, segment selector, and telemetry badge", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    expect(screen.getByRole("heading", { name: "Historic Data Download" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/DuckDB Parquet: Connected/i)).toBeInTheDocument();
    });

    const symbolInput = screen.getByLabelText(/Script \/ Symbol:/i);
    expect(symbolInput).toBeInTheDocument();
    expect(symbolInput).toHaveValue("RELIANCE");

    const segmentSelect = screen.getByLabelText(/Segment:/i);
    expect(segmentSelect).toBeInTheDocument();
    expect(segmentSelect).toHaveValue("NSE_EQ");
  });

  it("updates symbol when typing or clicking popular chips", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    const symbolInput = screen.getByLabelText(/Script \/ Symbol:/i);

    fireEvent.change(symbolInput, { target: { value: "TCS" } });
    expect(symbolInput).toHaveValue("TCS");

    const chip = screen.getByRole("button", { name: "NIFTY 50" });
    fireEvent.click(chip);
    expect(symbolInput).toHaveValue("NIFTY 50");
  });

  it("switches timeframe when clicking timeframe buttons", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    const m15Btn = screen.getByRole("button", { name: "15 min" });
    fireEvent.click(m15Btn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("timeframe=15m")
      );
    });
  });

  it("fetches and renders bars preview and summary scorecard", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    await waitFor(() => {
      expect(screen.getAllByText("₹2980.50").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("₹2940.00").length).toBeGreaterThanOrEqual(1);
    });

    expect(screen.getByText("Total Bars")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("triggers CSV download on button click", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    const appendChildSpy = vi.spyOn(document.body, "appendChild");
    const removeChildSpy = vi.spyOn(document.body, "removeChild");

    const downloadBtn = screen.getByRole("button", { name: /Download CSV/i });
    fireEvent.click(downloadBtn);

    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
  });
});
