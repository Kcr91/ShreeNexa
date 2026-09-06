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

  it("adds Nifty50 index to watchlist without error", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Create a new watchlist "My Indices"
    const newBtn = screen.getByText("+ New");
    fireEvent.click(newBtn);
    const nameInput = screen.getByPlaceholderText(/Watchlist Name/i);
    fireEvent.change(nameInput, { target: { value: "My Indices" } });
    fireEvent.click(screen.getByText("Create"));

    // Add Nifty50 index
    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "Nifty50" } });
    const addBtn = screen.getByText("Add");
    fireEvent.click(addBtn);

    // No error alert
    expect(screen.queryByRole("alert")).toBeNull();
    // NIFTY 50 trading symbol is now in the table
    expect(screen.getByText("NIFTY 50")).toBeInTheDocument();
  });

  it("renders Zerodha-style suggestion dropdown with category pills and index badge on typing", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "ni" } });

    // Suggestion dropdown should be open
    const listbox = screen.getByRole("listbox");
    expect(listbox).toBeInTheDocument();

    // Category pills should be visible
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Indices" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stocks" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "F&O" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ETF" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Commodities" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Forex" })).toBeInTheDocument();

    // Matching index options should appear with INDEX badge
    expect(screen.getAllByText("INDEX").length).toBeGreaterThan(0);
    expect(screen.getByText("NIFTY 50 INDEX")).toBeInTheDocument();
  });

  it("filters suggestions when clicking category pills (ETF, Commodities, Forex)", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "gold" } });

    // Click "ETF" pill -> should show GOLDBEES
    const etfPill = screen.getByRole("button", { name: "ETF" });
    fireEvent.click(etfPill);
    expect(screen.getByText("NIPPON INDIA ETF GOLD BEES")).toBeInTheDocument();
    expect(screen.queryByText("GOLD 1KG MCX FUTURES")).toBeNull();

    // Click "Commodities" pill -> should show MCX GOLD
    const comPill = screen.getByRole("button", { name: "Commodities" });
    fireEvent.click(comPill);
    expect(screen.getByText("GOLD 1KG MCX FUTURES")).toBeInTheDocument();
    expect(screen.queryByText("NIPPON INDIA ETF GOLD BEES")).toBeNull();

    // Search for forex
    fireEvent.change(symInput, { target: { value: "usdinr" } });
    const forexPill = screen.getByRole("button", { name: "Forex" });
    fireEvent.click(forexPill);
    expect(screen.getByText("USDINR CURRENCY FUTURES")).toBeInTheDocument();
  });

  it("handles Option B: hover + Add button directly adds instrument to watchlist", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Create a new watchlist
    const newBtn = screen.getByText("+ New");
    fireEvent.click(newBtn);
    const nameInput = screen.getByPlaceholderText(/Watchlist Name/i);
    fireEvent.change(nameInput, { target: { value: "Option B Test" } });
    fireEvent.click(screen.getByText("Create"));

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "crude" } });

    // Hover + Add button
    const addBtns = screen.getAllByText("+ Add");
    expect(addBtns.length).toBeGreaterThan(0);
    fireEvent.click(addBtns[0]);

    // CRUDEOIL is added to active watchlist
    expect(screen.getByText("CRUDEOIL")).toBeInTheDocument();
    expect(screen.getByText("MCX")).toBeInTheDocument();
  });

  it("handles Option B: clicking row opens mini-action menu and Market Depth", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "reliance" } });

    // Click on the row (not the + Add button)
    const relianceRow = screen.getByText("Reliance Industries Ltd");
    fireEvent.click(relianceRow);

    // Option B Mini-action menu buttons appear
    expect(screen.getByText(/📊 Chart/i)).toBeInTheDocument();
    expect(screen.getByText(/B Buy/i)).toBeInTheDocument();
    expect(screen.getByText(/S Sell/i)).toBeInTheDocument();
    expect(screen.getByText(/\+ Watchlist/i)).toBeInTheDocument();
    expect(screen.getByText(/📋 Market Depth/i)).toBeInTheDocument();

    // Click Market Depth
    const depthBtn = screen.getByText(/📋 Market Depth/i);
    fireEvent.click(depthBtn);

    // Market depth book should appear with bids & asks and 20-Level Full Depth capability for NSE
    expect(screen.getByText(/20-Level Full Depth \(NSE\)/i)).toBeInTheDocument();
    expect(screen.getByText("Total Bid")).toBeInTheDocument();
    expect(screen.getByText("Total Ask")).toBeInTheDocument();
  });

  it("focuses search input when Ctrl+K is pressed", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    expect(document.activeElement).not.toBe(symInput);

    // Trigger Ctrl+K
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });

    // Input should now be focused
    expect(document.activeElement).toBe(symInput);
  });

  it("navigates and selects suggestions via keyboard ArrowDown and Enter", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Create a new watchlist
    const newBtn = screen.getByText("+ New");
    fireEvent.click(newBtn);
    const nameInput = screen.getByPlaceholderText(/Watchlist Name/i);
    fireEvent.change(nameInput, { target: { value: "Keyboard Test" } });
    fireEvent.click(screen.getByText("Create"));

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "fin" } });

    // Press ArrowDown then Enter to select second suggestion
    fireEvent.keyDown(symInput, { key: "ArrowDown" });
    fireEvent.keyDown(symInput, { key: "Enter" });

    // Second match (BAJFINANCE from Bajaj Finance Ltd) should be added
    expect(screen.getByText("BAJFINANCE")).toBeInTheDocument();
  });
});
