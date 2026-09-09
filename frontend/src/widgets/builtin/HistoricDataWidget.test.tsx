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
      if (url.includes("/api/v1/historical/coverage")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            symbol: "RELIANCE",
            total_series: 1,
            items: [
              {
                dataset: "intraday",
                symbol: "RELIANCE",
                exchange_segment: "NSE_EQ",
                interval: "1",
                first_date: "2021-09-01",
                last_date: "2026-09-01",
                rows: 469000,
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

  it("shows what the warehouse actually holds for the scrip", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    await waitFor(() => {
      expect(screen.getByTestId("coverage-readout")).toBeInTheDocument();
    });
    // Text spans several JSX nodes, so assert on the rendered container content.
    const readout = screen.getByTestId("coverage-readout").textContent ?? "";
    expect(readout).toContain("intraday/1");
    expect(readout).toContain("2021-09-01 to 2026-09-01");
    // toLocaleString picks the runtime locale, so normalise digit separators.
    expect(readout.replace(/[.,\s]/g, "")).toContain("469000bars");
  });

  it("requests the max available range when the toggle is on", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    const maxBtn = screen.getByRole("button", { name: /Max available/i });
    expect(maxBtn).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(maxBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("range_mode=max")
      );
    });
    expect(maxBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("carries the range mode into the CSV export URL", async () => {
    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    fireEvent.click(screen.getByRole("button", { name: /Max available/i }));

    const createdLinks: HTMLAnchorElement[] = [];
    const originalCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = originalCreate(tag);
      if (tag === "a") {
        createdLinks.push(el as HTMLAnchorElement);
        (el as HTMLAnchorElement).click = vi.fn();
      }
      return el;
    });

    fireEvent.click(screen.getByRole("button", { name: /Download CSV/i }));

    expect(createdLinks.length).toBeGreaterThan(0);
    expect(createdLinks[0].href).toContain("range_mode=max");
  });

  it("says nothing is downloaded rather than implying data exists", async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url.includes("/api/v1/historical/coverage")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ symbol: "GHOST", total_series: 0, items: [] }),
        });
      }
      return Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({ detail: "No warehouse data for GHOST" }),
      });
    });

    render(<HistoricDataWidget instanceId="inst-test-hist" settings={{}} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Nothing has been downloaded for this scrip yet/i)
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/no data is ever simulated/i)).toBeInTheDocument();
  });
});
