import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WatchlistWidget } from "./WatchlistWidget";

describe("WatchlistWidget Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders default watchlist tabs and symbols", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Check tabs
    expect(screen.getByText("NIFTY 50")).toBeInTheDocument();
    expect(screen.getByText("BANK NIFTY F&O")).toBeInTheDocument();
    expect(screen.getByText("Breakout Stocks")).toBeInTheDocument();

    // Default is NIFTY 50 -> check symbols
    expect(screen.getByText("RELIANCE")).toBeInTheDocument();
    expect(screen.getByText("TCS")).toBeInTheDocument();
  });

  it("switches tabs between equity and F&O watchlists", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Click on BANK NIFTY F&O
    const fnoTab = screen.getByText("BANK NIFTY F&O");
    fireEvent.click(fnoTab);

    // Should display F&O contracts
    expect(screen.getByText("BANKNIFTY-FUT")).toBeInTheDocument();
    expect(screen.getByText("BANKNIFTY-52000-CE")).toBeInTheDocument();
    expect(screen.getAllByText("F&O").length).toBeGreaterThan(0);
  });

  it("creates a new custom watchlist and adds a symbol", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Click + New
    const newBtn = screen.getByText("+ New");
    fireEvent.click(newBtn);

    const input = screen.getByPlaceholderText(/Watchlist Name/i);
    fireEvent.change(input, { target: { value: "Crypto Proxy" } });

    const createBtn = screen.getByText("Create");
    fireEvent.click(createBtn);

    // Active tab is now "Crypto Proxy"
    expect(screen.getByText("Crypto Proxy")).toBeInTheDocument();
    expect(screen.getByText(/No symbols in this watchlist/i)).toBeInTheDocument();

    // Add a symbol
    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "COIN" } });
    const addBtn = screen.getByText("Add");
    fireEvent.click(addBtn);

    expect(screen.getByText("COIN")).toBeInTheDocument();
  });

  it("shows error alert and prevents adding unknown instrument", async () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "UNKNOWNXYZ" } });
    const addBtn = screen.getByText("Add");
    fireEvent.click(addBtn);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Unknown instrument 'UNKNOWNXYZ'");
  });

  it("toggles column visibility in column configuration panel", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Click Columns button
    const colBtn = screen.getByText(/⚙ Columns/i);
    fireEvent.click(colBtn);

    // Check that column options are displayed
    expect(screen.getByLabelText("Bid / Ask")).toBeInTheDocument();
    const bidAskCheckbox = screen.getByLabelText("Bid / Ask");

    // Toggle Bid / Ask on
    fireEvent.click(bidAskCheckbox);

    // Table now contains Bid / Ask header
    expect(screen.getByText("Bid / Ask", { selector: "th" })).toBeInTheDocument();
  });
});
