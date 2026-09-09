import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { HistoricDataReportWidget } from "./HistoricDataReportWidget";

const REPORT = {
  generated_at: "2026-09-09T12:00:00+05:30",
  totals: {
    windows: 8,
    bars: 87479,
    done: 6,
    empty: 0,
    pending: 2,
    failed: 0,
    suspect: 6,
    settled: 6,
    percent_complete: 75.0,
  },
  series_returned: 1,
  series: [
    {
      symbol: "NIFTY",
      label: "NIFTY [1]",
      dataset: "intraday",
      exchange_segment: "IDX_I",
      interval: "1",
      tier: 1,
      downloaded_months: 6,
      pending_months: 2,
      failed_months: 0,
      suspect_months: 1,
      total_rows: 87479,
      first_month: "2021-09",
      last_month: "2022-04",
      months: [
        {
          month: "2021-10",
          state: "done",
          rows: 14987,
          suspect: true,
          reasons: ["only 50% of bars inside regular market hours"],
          in_hours: 7500,
          out_of_hours: 7487,
          distinct_days: 21,
          unexpected_dates: ["2021-10-16"],
          attempts: 1,
          last_error: null,
        },
        {
          month: "2021-11",
          state: "done",
          rows: 15023,
          suspect: false,
          reasons: [],
          in_hours: 15023,
          out_of_hours: 0,
          distinct_days: 21,
          unexpected_dates: [],
          attempts: 1,
          last_error: null,
        },
        {
          month: "2022-04",
          state: "pending",
          rows: 0,
          suspect: false,
          reasons: [],
          in_hours: 0,
          out_of_hours: 0,
          distinct_days: 0,
          unexpected_dates: [],
          attempts: 0,
          last_error: null,
        },
      ],
    },
  ],
};

describe("HistoricDataReportWidget", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.restoreAllMocks();
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => REPORT,
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows overall download progress", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    await waitFor(() => {
      expect(screen.getByTestId("report-totals")).toBeInTheDocument();
    });
    const totals = screen.getByTestId("report-totals").textContent ?? "";
    expect(totals).toContain("75");
    expect(totals.replace(/[.,\s]/g, "")).toContain("87479");
  });

  it("renders one cell per month of the series", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/NIFTY \[1\] 2021-10 done/)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/NIFTY \[1\] 2021-11 done/)).toBeInTheDocument();
    expect(screen.getByLabelText(/NIFTY \[1\] 2022-04 pending/)).toBeInTheDocument();
  });

  it("distinguishes a flagged month from a clean one", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/2021-10 done needs review/)).toBeInTheDocument();
    });
    // The clean month must not be labelled as needing review.
    expect(screen.queryByLabelText(/2021-11 done needs review/)).toBeNull();
  });

  it("explains why a month was flagged when selected", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    const cell = await screen.findByLabelText(/2021-10 done needs review/);
    fireEvent.click(cell);

    const detail = screen.getByTestId("month-detail");
    expect(detail.textContent).toContain("only 50% of bars inside regular market hours");
    expect(detail.textContent).toContain("2021-10-16");
  });

  it("filters to flagged months only when asked", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    fireEvent.click(screen.getByRole("button", { name: /Needs review only/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("suspect_only=true")
      );
    });
  });

  it("passes a symbol filter to the API", async () => {
    render(<HistoricDataReportWidget settings={{}} />);

    fireEvent.change(screen.getByLabelText(/Symbol filter/i), {
      target: { value: "banknifty" },
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("symbol=BANKNIFTY"));
    });
  });

  it("says nothing has been queued rather than showing an empty grid", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ...REPORT, series: [], series_returned: 0 }),
    });

    render(<HistoricDataReportWidget settings={{}} />);

    await waitFor(() => {
      expect(screen.getByText(/No backfill jobs have been queued yet/i)).toBeInTheDocument();
    });
  });

  it("surfaces a ledger outage instead of implying nothing was downloaded", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Backfill ledger unavailable: connection refused" }),
    });

    render(<HistoricDataReportWidget settings={{}} />);

    await waitFor(() => {
      expect(screen.getByText(/ledger unavailable/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/No backfill jobs have been queued yet/i)).toBeNull();
  });
});
