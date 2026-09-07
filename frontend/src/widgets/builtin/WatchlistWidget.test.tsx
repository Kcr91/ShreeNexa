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

    // Matching index options should appear with INDICES badge
    expect(screen.getAllByText("INDICES").length).toBeGreaterThan(0);
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

  it("handles Zerodha hover actions in suggestion dropdown (Image 1 & 2)", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Create a new watchlist
    const newBtn = screen.getByText("+ New");
    fireEvent.click(newBtn);
    const nameInput = screen.getByPlaceholderText(/Watchlist Name/i);
    fireEvent.change(nameInput, { target: { value: "Zerodha Hover Test" } });
    fireEvent.click(screen.getByText("Create"));

    const symInput = screen.getByPlaceholderText(/Add symbol/i);
    fireEvent.change(symInput, { target: { value: "crude" } });

    // In suggestion dropdown, click the Add to Watchlist (+) button
    const addBtns = screen.getAllByRole("button", { name: /Add to Watchlist/i });
    expect(addBtns.length).toBeGreaterThan(0);
    fireEvent.click(addBtns[0]);

    // CRUDEOIL is added to active watchlist
    expect(screen.getByText("CRUDEOIL")).toBeInTheDocument();
    expect(screen.getByText("MCX")).toBeInTheDocument();

    // Search for an index (e.g. "nifty") -> Image 2: NO Buy/Sell buttons for indices!
    fireEvent.change(symInput, { target: { value: "nifty 50" } });
    const niftyOption = screen.getByText("NIFTY 50 INDEX").closest("li")!;
    fireEvent.mouseEnter(niftyOption);

    // Indices must strictly NOT have Buy or Sell buttons
    expect(screen.queryByRole("button", { name: "Buy" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Sell" })).toBeNull();
    // But must have Market Depth, Chart, and Add to Watchlist buttons
    expect(screen.getByRole("button", { name: "Market Depth" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chart" })).toBeInTheDocument();
  });

  it("handles Zerodha row hover actions, index safety, and Market Depth in watchlist table (Image 3)", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // In default NIFTY 50 watchlist, find RELIANCE row
    const relianceSymbol = screen.getByText("RELIANCE");
    const relianceRow = relianceSymbol.closest("tr")!;
    fireEvent.mouseEnter(relianceRow);

    // Equities row has Buy (B), Sell (S), Market Depth (≡), Chart (📈), Remove (🗑️), and More (•••)
    expect(screen.getByRole("button", { name: "Buy RELIANCE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sell RELIANCE" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Market Depth" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chart" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove Symbol" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "More options" })).toBeInTheDocument();

    // Click Market Depth button on RELIANCE row
    const depthBtn = screen.getByRole("button", { name: "Market Depth" });
    fireEvent.click(depthBtn);

    // Market depth book modal should appear with bids & asks and 20-Level Full Depth capability for NSE
    expect(screen.getByRole("dialog", { name: "Market Depth Modal" })).toBeInTheDocument();
    expect(screen.getByText(/20-Level Full Depth \(NSE\)/i)).toBeInTheDocument();
    expect(screen.getByText("Total Bid")).toBeInTheDocument();
    expect(screen.getByText("Total Ask")).toBeInTheDocument();

    // Close modal
    const closeBtn = screen.getByRole("button", { name: "Close modal" });
    fireEvent.click(closeBtn);
    expect(screen.queryByRole("dialog")).toBeNull();

    // Click Delete / Remove Symbol -> RELIANCE removed from active watchlist
    const removeBtn = screen.getByRole("button", { name: "Remove Symbol" });
    fireEvent.click(removeBtn);
    expect(screen.queryByText("RELIANCE")).toBeNull();
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

  it("sorts watchlist items by % change, name, or current price using the header grade filter", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const sortSelect = screen.getByLabelText("Grade or filter watchlist");
    expect(sortSelect).toBeInTheDocument();

    // Sort by % Change (Low to High - biggest losers first)
    fireEvent.change(sortSelect, { target: { value: "pct_asc" } });
    let rows = screen.getAllByRole("row");
    // Row 0 is header, Row 1 should be MPHASIS (-2.68%)
    expect(rows[1]).toHaveTextContent("MPHASIS");

    // Sort by % Change (High to Low - biggest gainers first)
    fireEvent.change(sortSelect, { target: { value: "pct_desc" } });
    rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("ICICIBANK");

    // Sort by Name (A to Z)
    fireEvent.change(sortSelect, { target: { value: "name_asc" } });
    rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("HDFCBANK");

    // Sort by Current Price (High to Low)
    fireEvent.change(sortSelect, { target: { value: "price_desc" } });
    rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("TCS");
  });

  it("displays 52W High and Low with percentage distance from current price", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    // Open Columns settings
    const colBtn = screen.getByText(/⚙ Columns/i);
    fireEvent.click(colBtn);

    // Enable 52W High and 52W Low columns
    const highCheckbox = screen.getByLabelText("52W High");
    fireEvent.click(highCheckbox);
    const lowCheckbox = screen.getByLabelText("52W Low");
    fireEvent.click(lowCheckbox);

    // Check table headers
    expect(screen.getByText("52W High", { selector: "th" })).toBeInTheDocument();
    expect(screen.getByText("52W Low", { selector: "th" })).toBeInTheDocument();

    // Verify formatted distance percentage rendered for MPHASIS
    // MPHASIS: ltp 2357.10, 52W High 3125.00 (-24.57%), 52W Low 2180.00 (+8.12%)
    expect(screen.getByText(/3,125\.00/i)).toBeInTheDocument();
    expect(screen.getByText(/-24\.57%/i)).toBeInTheDocument();
    expect(screen.getByText(/2,180\.00/i)).toBeInTheDocument();
    expect(screen.getByText(/\+8\.12%/i)).toBeInTheDocument();
  });

  it("places price change (Chg ₹) column immediately before percentage change (Chg %)", () => {
    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);

    const headers = screen.getAllByRole("columnheader");
    const headerTexts = headers.map((h) => h.textContent?.trim() || "");

    const chgAbsIndex = headerTexts.findIndex((t) => t.includes("Chg (₹)"));
    const chgPctIndex = headerTexts.findIndex((t) => t.includes("Chg %"));

    expect(chgAbsIndex).toBeGreaterThan(-1);
    expect(chgPctIndex).toBeGreaterThan(-1);
    expect(chgAbsIndex).toBe(chgPctIndex - 1);
  });

  it("dispatches shreenexa:select-symbol event when a script row is clicked", () => {
    let capturedEvent: any = null;
    const listener = (e: any) => {
      capturedEvent = e.detail;
    };
    window.addEventListener("shreenexa:select-symbol", listener);

    render(<WatchlistWidget instanceId="inst-wl-test" settings={{}} />);
    const mphasisRow = screen.getByText("MPHASIS").closest("tr")!;
    fireEvent.click(mphasisRow);

    expect(capturedEvent).not.toBeNull();
    expect(capturedEvent.symbol).toBe("MPHASIS");
    expect(capturedEvent.item.ltp).toBe(2357.10);

    window.removeEventListener("shreenexa:select-symbol", listener);
  });
});
