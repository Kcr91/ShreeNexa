import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  CatalogInstrument,
  searchCatalogInstruments,
} from "../../watchlist/storage";
import { generateMockDepthBook, resolveSegmentDepthCapability } from "../../depth/engine";
import { MarketDepthBook } from "../../depth/types";

export type SearchCategory =
  | "ALL"
  | "INDICES"
  | "STOCKS"
  | "FNO"
  | "ETF"
  | "COMMODITY"
  | "FOREX";

export interface SymbolSearchDropdownProps {
  value?: string;
  onChange?: (val: string) => void;
  onSelectInstrument: (instrument: CatalogInstrument) => void;
  onOpenChart?: (instrument: CatalogInstrument) => void;
  onBuy?: (instrument: CatalogInstrument) => void;
  onSell?: (instrument: CatalogInstrument) => void;
  onOpenDepth?: (instrument: CatalogInstrument) => void;
  onSubmitText?: (text: string) => void;
  existingSecurityIds?: Set<string>;
  existingSymbols?: Set<string>;
  placeholder?: string;
}

export const SymbolSearchDropdown: React.FC<SymbolSearchDropdownProps> = ({
  value,
  onChange,
  onSelectInstrument,
  onOpenChart,
  onBuy,
  onSell,
  onOpenDepth,
  onSubmitText,
  existingSecurityIds = new Set(),
  existingSymbols = new Set(),
  placeholder = "Add symbol (e.g. NIFTY, TCS, RELIANCE)...",
}) => {
  const [internalQuery, setInternalQuery] = useState("");
  const isControlled = value !== undefined;
  const activeQuery = isControlled ? value : internalQuery;

  const setQueryValue = (val: string) => {
    if (isControlled && onChange) {
      onChange(val);
    } else {
      setInternalQuery(val);
    }
  };

  const [category, setCategory] = useState<SearchCategory>("ALL");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [apiResults, setApiResults] = useState<CatalogInstrument[]>([]);

  // Option B: Active instrument for mini-action menu or market depth view
  const [actionMenuInstrument, setActionMenuInstrument] = useState<CatalogInstrument | null>(null);
  const [showMarketDepth, setShowMarketDepth] = useState(false);

  // Hover state for suggestion rows
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Global hotkey Ctrl+K or / to focus search
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (
        (e.ctrlKey && e.key.toLowerCase() === "k") ||
        (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA")
      ) {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setActionMenuInstrument(null);
        setShowMarketDepth(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced API search when query changes
  useEffect(() => {
    const cleanQ = activeQuery.trim();
    if (!cleanQ || cleanQ.length < 2) {
      setApiResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const timer = setTimeout(async () => {
      try {
        let queryParams = "";
        if (category === "INDICES") queryParams = "&exchange_segment=IDX_I";
        else if (category === "STOCKS") queryParams = "&exchange_segment=NSE_EQ";
        else if (category === "FNO") queryParams = "&exchange_segment=NSE_FNO";
        else if (category === "ETF") queryParams = "&instrument_type=ETF";
        else if (category === "COMMODITY") queryParams = "&exchange_segment=MCX_COMM";
        else if (category === "FOREX") queryParams = "&exchange_segment=NSE_CURRENCY";

        const res = await fetch(
          `/api/v1/instruments/search?query=${encodeURIComponent(cleanQ)}&is_active_only=true${queryParams}&limit=20`
        );
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            const mapped: CatalogInstrument[] = data.map((d: any) => ({
              symbol: d.symbol || d.trading_symbol || cleanQ.toUpperCase(),
              tradingSymbol: d.trading_symbol || d.symbol,
              securityId: String(d.security_id || d.securityId),
              segment: d.exchange_segment || "NSE_EQ",
              instrumentType:
                d.instrument_type === "INDEX"
                  ? "INDEX"
                  : d.instrument_type === "ETF"
                  ? "ETF"
                  : d.exchange_segment?.startsWith("MCX")
                  ? "FUTCOM"
                  : d.exchange_segment?.includes("CURRENCY")
                  ? "FUTCUR"
                  : ["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"].includes(d.instrument_type)
                  ? d.instrument_type
                  : "EQUITY",
              name: d.name || d.trading_symbol || d.symbol,
              ltp: d.ltp ?? (d.instrument_type === "INDEX" ? 24500 : 1000),
              changePct: d.change_pct ?? 0,
              expiry: d.expiry_date,
              strike: d.strike_price,
              optionType: d.option_type,
            }));
            setApiResults(mapped);
          }
        }
      } catch {
        // Offline / dev fallback
        setApiResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [activeQuery, category]);

  // Merge local catalog results and API results, deduplicating by securityId or tradingSymbol
  const results = useMemo(() => {
    const cleanQ = activeQuery.trim();
    if (!cleanQ) return [];

    const localMatches = searchCatalogInstruments(cleanQ, category);
    const seen = new Set<string>();
    const merged: CatalogInstrument[] = [];

    // Prioritize exact or local indexed matches
    for (const item of localMatches) {
      const key = `${item.segment}-${item.securityId}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(item);
      }
    }

    // Add API matches
    for (const item of apiResults) {
      const key = `${item.segment}-${item.securityId}`;
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(item);
      }
    }

    return merged.slice(0, 30);
  }, [activeQuery, category, apiResults]);

  // Reset highlight index when results change
  useEffect(() => {
    setHighlightedIndex(0);
  }, [results]);

  // Scroll highlighted item into view safely
  useEffect(() => {
    if (listRef.current && listRef.current.children[highlightedIndex]) {
      const itemEl = listRef.current.children[highlightedIndex] as HTMLElement;
      if (typeof itemEl.scrollIntoView === "function") {
        itemEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "Enter") {
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % (results.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev - 1 + results.length) % (results.length || 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results.length > 0 && results[highlightedIndex]) {
        // By default Enter adds the highlighted item
        handleSelectAddDirectly(results[highlightedIndex]);
      } else if (onSubmitText && activeQuery.trim()) {
        onSubmitText(activeQuery);
        setIsOpen(false);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (showMarketDepth) {
        setShowMarketDepth(false);
      } else if (actionMenuInstrument) {
        setActionMenuInstrument(null);
      } else {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    }
  };

  // Direct 1-click addition to active watchlist (recommended hover action)
  const handleSelectAddDirectly = (item: CatalogInstrument) => {
    onSelectInstrument(item);
    setQueryValue("");
    setIsOpen(false);
    setActionMenuInstrument(null);
    setShowMarketDepth(false);
  };

  // Clicking row opens Option B Mini-Action Menu
  const handleRowClick = (item: CatalogInstrument) => {
    setActionMenuInstrument(item);
    setShowMarketDepth(false);
  };

  // Segment badges
  const getSegmentBadge = (inst: CatalogInstrument) => {
    if (inst.instrumentType === "INDEX" || inst.segment === "IDX_I") {
      return { label: "INDEX", bg: "rgba(163, 113, 247, 0.2)", color: "#a371f7", border: "rgba(163, 113, 247, 0.4)" };
    }
    if (inst.instrumentType === "ETF") {
      return { label: "ETF", bg: "rgba(46, 160, 67, 0.2)", color: "#3fb950", border: "rgba(46, 160, 67, 0.4)" };
    }
    if (inst.segment?.startsWith("MCX") || inst.instrumentType === "FUTCOM" || inst.instrumentType === "COMMODITY") {
      return { label: "MCX", bg: "rgba(240, 136, 62, 0.2)", color: "#f0883e", border: "rgba(240, 136, 62, 0.4)" };
    }
    if (inst.segment?.includes("CURRENCY") || inst.instrumentType === "FUTCUR" || inst.instrumentType === "FOREX") {
      return { label: "CUR", bg: "rgba(56, 189, 248, 0.2)", color: "#38bdf8", border: "rgba(56, 189, 248, 0.4)" };
    }
    if (["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"].includes(inst.instrumentType) || inst.segment === "NSE_FNO") {
      return { label: "NFO", bg: "rgba(240, 136, 62, 0.2)", color: "#f0883e", border: "rgba(240, 136, 62, 0.4)" };
    }
    if (inst.segment === "BSE_EQ") {
      return { label: "BSE", bg: "rgba(210, 153, 34, 0.2)", color: "#d29922", border: "rgba(210, 153, 34, 0.4)" };
    }
    return { label: "NSE", bg: "rgba(88, 166, 255, 0.2)", color: "#58a6ff", border: "rgba(88, 166, 255, 0.4)" };
  };

  // Generate Market Depth Book for Option B Depth View
  const depthBook: MarketDepthBook | null = useMemo(() => {
    if (!actionMenuInstrument || !showMarketDepth) return null;
    return generateMockDepthBook(
      actionMenuInstrument.symbol,
      actionMenuInstrument.segment,
      "LEVEL_20",
      actionMenuInstrument.ltp || 1000,
      Number(actionMenuInstrument.securityId) || 1333
    );
  }, [actionMenuInstrument, showMarketDepth]);

  const depthCapability = useMemo(() => {
    if (!actionMenuInstrument) return null;
    return resolveSegmentDepthCapability(actionMenuInstrument.segment, "LEVEL_20");
  }, [actionMenuInstrument]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        flex: 1,
        maxWidth: "650px",
      }}
    >
      {/* Search Input Box */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          backgroundColor: "var(--bg-input, #0d1117)",
          border: isOpen ? "1px solid var(--border-active, #58a6ff)" : "1px solid var(--border-subtle, #30363d)",
          borderRadius: "var(--radius-sm, 4px)",
          padding: "4px 8px",
          gap: "6px",
          transition: "border-color 0.15s ease",
        }}
      >
        {/* Search Icon */}
        <span
          style={{
            color: "var(--text-muted, #8b949e)",
            fontSize: "13px",
            lineHeight: 1,
            display: "flex",
            alignItems: "center",
          }}
          aria-hidden="true"
        >
          🔍
        </span>

        {/* Input Field */}
        <input
          ref={inputRef}
          type="text"
          value={activeQuery}
          onChange={(e) => {
            setQueryValue(e.target.value);
            setIsOpen(true);
            setActionMenuInstrument(null);
            setShowMarketDepth(false);
          }}
          onFocus={() => {
            setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Search instruments"
          aria-autocomplete="list"
          aria-expanded={isOpen}
          role="combobox"
          style={{
            flex: 1,
            backgroundColor: "transparent",
            border: "none",
            outline: "none",
            color: "var(--text-primary, #f0f6fc)",
            fontSize: "var(--font-size-xs, 12px)",
            fontFamily: "inherit",
          }}
        />

        {/* Loading Spinner */}
        {isLoading && (
          <span
            style={{
              fontSize: "11px",
              color: "var(--color-brand, #58a6ff)",
              animation: "spin 1s linear infinite",
            }}
            title="Loading suggestions..."
          >
            ⏳
          </span>
        )}

        {/* Clear Button */}
        {activeQuery && (
          <button
            type="button"
            onClick={() => {
              setQueryValue("");
              setApiResults([]);
              setActionMenuInstrument(null);
              setShowMarketDepth(false);
              inputRef.current?.focus();
            }}
            aria-label="Clear search"
            style={{
              background: "none",
              border: "none",
              color: "var(--text-muted, #8b949e)",
              cursor: "pointer",
              fontSize: "12px",
              padding: "0 2px",
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        )}

        {/* Global Ctrl+K Shortcut Hint */}
        <kbd
          style={{
            padding: "1px 5px",
            borderRadius: "3px",
            backgroundColor: "var(--bg-elevated, #21262d)",
            border: "1px solid var(--border-subtle, #30363d)",
            fontSize: "9px",
            color: "var(--text-muted, #8b949e)",
            fontFamily: "inherit",
            cursor: "pointer",
            userSelect: "none",
          }}
          onClick={() => {
            inputRef.current?.focus();
            setIsOpen(true);
          }}
          title="Press Ctrl+K or / to search"
        >
          Ctrl+K
        </kbd>
      </div>

      {/* Autocomplete Dropdown & Option B Action Menus */}
      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            backgroundColor: "var(--bg-surface, #161b22)",
            border: "1px solid var(--border-default, #30363d)",
            borderRadius: "var(--radius-md, 6px)",
            boxShadow: "var(--shadow-lg, 0 10px 25px rgba(0, 0, 0, 0.5))",
            zIndex: 1000,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Zerodha-Style Category Filter Pills (Unified ALL as Default) */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 8px",
              borderBottom: "1px solid var(--border-subtle, #21262d)",
              backgroundColor: "var(--bg-elevated, #11161d)",
              overflowX: "auto",
            }}
          >
            {(
              [
                { id: "ALL", label: "All" },
                { id: "INDICES", label: "Indices" },
                { id: "STOCKS", label: "Stocks" },
                { id: "FNO", label: "F&O" },
                { id: "ETF", label: "ETF" },
                { id: "COMMODITY", label: "Commodities" },
                { id: "FOREX", label: "Forex" },
              ] as const
            ).map((pill) => {
              const isActive = category === pill.id;
              return (
                <button
                  key={pill.id}
                  type="button"
                  onClick={() => setCategory(pill.id)}
                  style={{
                    padding: "2px 8px",
                    borderRadius: "12px",
                    fontSize: "11px",
                    fontWeight: isActive ? 600 : 500,
                    cursor: "pointer",
                    border: isActive
                      ? "1px solid var(--color-brand, #58a6ff)"
                      : "1px solid var(--border-subtle, #30363d)",
                    backgroundColor: isActive
                      ? "var(--color-primary-bg, rgba(88, 166, 255, 0.15))"
                      : "transparent",
                    color: isActive
                      ? "var(--color-brand, #58a6ff)"
                      : "var(--text-muted, #8b949e)",
                    transition: "all 0.1s ease",
                    whiteSpace: "nowrap",
                  }}
                >
                  {pill.label}
                </button>
              );
            })}
            <span
              style={{
                marginLeft: "auto",
                fontSize: "10px",
                color: "var(--text-muted, #8b949e)",
                whiteSpace: "nowrap",
              }}
            >
              {results.length} results
            </span>
          </div>

          {/* Option B: Active Mini-Action Menu & Market Depth Flyout */}
          {actionMenuInstrument && (
            <div
              style={{
                padding: "8px 12px",
                backgroundColor: "var(--bg-elevated, #1c2128)",
                borderBottom: "1px solid var(--border-subtle, #30363d)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              {/* Instrument Details Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontWeight: 700, color: "#fff", fontSize: "13px" }}>
                    {actionMenuInstrument.tradingSymbol}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      padding: "1px 6px",
                      borderRadius: "3px",
                      backgroundColor: getSegmentBadge(actionMenuInstrument).bg,
                      color: getSegmentBadge(actionMenuInstrument).color,
                      border: `1px solid ${getSegmentBadge(actionMenuInstrument).border}`,
                      fontWeight: 700,
                    }}
                  >
                    {getSegmentBadge(actionMenuInstrument).label}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--text-muted, #8b949e)" }}>
                    {actionMenuInstrument.name}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {actionMenuInstrument.ltp > 0 && (
                    <span style={{ fontFamily: "var(--font-family-mono)", fontWeight: 600, fontSize: "12px", color: "#fff" }}>
                      ₹{actionMenuInstrument.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setActionMenuInstrument(null);
                      setShowMarketDepth(false);
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--text-muted, #8b949e)",
                      cursor: "pointer",
                      fontSize: "13px",
                      padding: "0 4px",
                    }}
                    title="Close menu"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Option B Action Buttons */}
              <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                {/* 1. Chart */}
                <button
                  type="button"
                  onClick={() => {
                    onOpenChart?.(actionMenuInstrument);
                    setActionMenuInstrument(null);
                    setIsOpen(false);
                  }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle, #30363d)",
                    backgroundColor: "transparent",
                    color: "var(--text-primary, #f0f6fc)",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  📊 Chart
                </button>

                {/* 2. Buy (B) */}
                <button
                  type="button"
                  onClick={() => {
                    onBuy?.(actionMenuInstrument);
                    setActionMenuInstrument(null);
                    setIsOpen(false);
                  }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    border: "1px solid #238636",
                    backgroundColor: "rgba(35, 134, 54, 0.2)",
                    color: "#3fb950",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  B Buy
                </button>

                {/* 3. Sell (S) */}
                <button
                  type="button"
                  onClick={() => {
                    onSell?.(actionMenuInstrument);
                    setActionMenuInstrument(null);
                    setIsOpen(false);
                  }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    border: "1px solid #da3633",
                    backgroundColor: "rgba(218, 54, 51, 0.2)",
                    color: "#f85149",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  S Sell
                </button>

                {/* 4. Add to Watchlist */}
                <button
                  type="button"
                  onClick={() => {
                    handleSelectAddDirectly(actionMenuInstrument);
                  }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    border: "1px solid var(--color-brand, #58a6ff)",
                    backgroundColor: "rgba(88, 166, 255, 0.15)",
                    color: "var(--color-brand, #58a6ff)",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  + Watchlist
                </button>

                {/* 5. Market Depth (5 or 20) */}
                <button
                  type="button"
                  onClick={() => {
                    onOpenDepth?.(actionMenuInstrument);
                    setShowMarketDepth((prev) => !prev);
                  }}
                  style={{
                    padding: "3px 10px",
                    borderRadius: "4px",
                    border: showMarketDepth
                      ? "1px solid var(--color-brand, #58a6ff)"
                      : "1px solid var(--border-subtle, #30363d)",
                    backgroundColor: showMarketDepth
                      ? "var(--color-primary-bg, rgba(88, 166, 255, 0.2))"
                      : "transparent",
                    color: showMarketDepth ? "var(--color-brand, #58a6ff)" : "var(--text-primary, #f0f6fc)",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  📋 Market Depth ({depthCapability?.actualLevel === "LEVEL_20" ? "20" : "5"})
                </button>
              </div>

              {/* Interactive Market Depth Table (Option B) */}
              {showMarketDepth && depthBook && (
                <div
                  style={{
                    marginTop: "6px",
                    padding: "8px",
                    backgroundColor: "var(--bg-surface, #0d1117)",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle, #30363d)",
                    fontSize: "11px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "6px",
                      color: "var(--text-muted, #8b949e)",
                      fontSize: "10px",
                    }}
                  >
                    <span>
                      Dhan Depth Capability:{" "}
                      <strong style={{ color: "#fff" }}>
                        {depthCapability?.actualLevel === "LEVEL_20"
                          ? "20-Level Full Depth (NSE)"
                          : "5-Level Depth Feed (MCX/Forex/BSE)"}
                      </strong>
                    </span>
                    <span>
                      Spread: ₹{depthBook.spread.toFixed(2)} ({depthBook.spreadPct}%)
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                    {/* Bids Column */}
                    <div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "35px 1fr 1fr",
                          fontWeight: 600,
                          color: "#3fb950",
                          borderBottom: "1px solid rgba(63, 185, 80, 0.3)",
                          paddingBottom: "2px",
                          marginBottom: "2px",
                        }}
                      >
                        <span>Orders</span>
                        <span style={{ textAlign: "right" }}>Qty</span>
                        <span style={{ textAlign: "right" }}>Bid Price</span>
                      </div>
                      {depthBook.bids.slice(0, depthCapability?.actualLevel === "LEVEL_20" ? 20 : 5).map((bid, i) => (
                        <div
                          key={`bid-${i}`}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "35px 1fr 1fr",
                            padding: "1px 0",
                            fontFamily: "var(--font-family-mono)",
                            fontSize: "10px",
                          }}
                        >
                          <span style={{ color: "var(--text-muted, #8b949e)" }}>{bid.orders}</span>
                          <span style={{ textAlign: "right", color: "var(--text-primary, #f0f6fc)" }}>
                            {bid.quantity.toLocaleString("en-IN")}
                          </span>
                          <span style={{ textAlign: "right", color: "#3fb950", fontWeight: 600 }}>
                            {bid.price.toFixed(2)}
                          </span>
                        </div>
                      ))}
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          borderTop: "1px solid var(--border-subtle, #30363d)",
                          marginTop: "4px",
                          paddingTop: "2px",
                          fontWeight: 600,
                        }}
                      >
                        <span>Total Bid</span>
                        <span style={{ fontFamily: "var(--font-family-mono)", color: "#3fb950" }}>
                          {depthBook.totalBidQty.toLocaleString("en-IN")}
                        </span>
                      </div>
                    </div>

                    {/* Asks Column */}
                    <div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 35px",
                          fontWeight: 600,
                          color: "#f85149",
                          borderBottom: "1px solid rgba(248, 81, 73, 0.3)",
                          paddingBottom: "2px",
                          marginBottom: "2px",
                        }}
                      >
                        <span>Ask Price</span>
                        <span style={{ textAlign: "right" }}>Qty</span>
                        <span style={{ textAlign: "right" }}>Orders</span>
                      </div>
                      {depthBook.asks.slice(0, depthCapability?.actualLevel === "LEVEL_20" ? 20 : 5).map((ask, i) => (
                        <div
                          key={`ask-${i}`}
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr 35px",
                            padding: "1px 0",
                            fontFamily: "var(--font-family-mono)",
                            fontSize: "10px",
                          }}
                        >
                          <span style={{ color: "#f85149", fontWeight: 600 }}>{ask.price.toFixed(2)}</span>
                          <span style={{ textAlign: "right", color: "var(--text-primary, #f0f6fc)" }}>
                            {ask.quantity.toLocaleString("en-IN")}
                          </span>
                          <span style={{ textAlign: "right", color: "var(--text-muted, #8b949e)" }}>{ask.orders}</span>
                        </div>
                      ))}
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          borderTop: "1px solid var(--border-subtle, #30363d)",
                          marginTop: "4px",
                          paddingTop: "2px",
                          fontWeight: 600,
                        }}
                      >
                        <span>Total Ask</span>
                        <span style={{ fontFamily: "var(--font-family-mono)", color: "#f85149" }}>
                          {depthBook.totalAskQty.toLocaleString("en-IN")}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Suggestion List */}
          <ul
            ref={listRef}
            role="listbox"
            aria-label="Instrument search suggestions"
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              maxHeight: "320px",
              overflowY: "auto",
            }}
          >
            {results.length === 0 ? (
              <li
                style={{
                  padding: "16px",
                  textAlign: "center",
                  color: "var(--text-muted, #8b949e)",
                  fontSize: "var(--font-size-xs, 12px)",
                }}
              >
                <div>No instruments found for "{activeQuery}".</div>
                <div style={{ fontSize: "11px", marginTop: "4px", opacity: 0.7 }}>
                  Try searching across <strong>Indices</strong>, <strong>Stocks</strong>, <strong>Commodities (MCX)</strong>, <strong>Forex</strong>, or <strong>ETFs</strong>
                </div>
              </li>
            ) : (
              results.map((inst, index) => {
                const isHighlighted = index === highlightedIndex;
                const isHovered = index === hoveredIndex;
                const isAlreadyAdded =
                  existingSecurityIds.has(inst.securityId) ||
                  existingSymbols.has(inst.symbol) ||
                  existingSymbols.has(inst.tradingSymbol);
                const badge = getSegmentBadge(inst);

                return (
                  <li
                    key={`${inst.segment}-${inst.securityId}`}
                    role="option"
                    aria-selected={isHighlighted}
                    onMouseEnter={() => {
                      setHighlightedIndex(index);
                      setHoveredIndex(index);
                    }}
                    onMouseLeave={() => {
                      setHoveredIndex(null);
                    }}
                    onClick={() => handleRowClick(inst)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      cursor: "pointer",
                      borderBottom: "1px solid var(--border-subtle, #1e242c)",
                      backgroundColor:
                        actionMenuInstrument?.securityId === inst.securityId &&
                        actionMenuInstrument?.segment === inst.segment
                          ? "rgba(88, 166, 255, 0.15)"
                          : isHighlighted
                          ? "var(--bg-hover, #21262d)"
                          : "transparent",
                      transition: "background-color 0.1s ease",
                    }}
                  >
                    {/* Left: Symbol, Segment Badge, & Description */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span
                          style={{
                            fontWeight: 600,
                            color: "var(--text-primary, #f0f6fc)",
                            fontSize: "var(--font-size-sm, 13px)",
                          }}
                        >
                          {inst.tradingSymbol}
                        </span>
                        {/* Segment Badge */}
                        <span
                          style={{
                            padding: "1px 5px",
                            borderRadius: "3px",
                            fontSize: "9px",
                            fontWeight: 700,
                            letterSpacing: "0.5px",
                            backgroundColor: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {badge.label}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--text-muted, #8b949e)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          maxWidth: "300px",
                        }}
                      >
                        {inst.name}
                      </span>
                    </div>

                    {/* Right: LTP & Hover Option B + Add Button */}
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {inst.ltp !== undefined && inst.ltp > 0 && (
                        <div style={{ textAlign: "right" }}>
                          <div
                            style={{
                              fontSize: "12px",
                              fontFamily: "var(--font-family-mono)",
                              fontWeight: 500,
                              color: "var(--text-primary, #f0f6fc)",
                            }}
                          >
                            ₹{inst.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </div>
                          {inst.changePct !== undefined && (
                            <div
                              style={{
                                fontSize: "10px",
                                fontFamily: "var(--font-family-mono)",
                                color:
                                  inst.changePct >= 0
                                    ? "var(--color-up, #3fb950)"
                                    : "var(--color-down, #f85149)",
                              }}
                            >
                              {inst.changePct >= 0 ? "+" : ""}
                              {inst.changePct.toFixed(2)}%
                            </div>
                          )}
                        </div>
                      )}

                      {/* Option B: Hover reveals + Add button directly */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectAddDirectly(inst);
                        }}
                        style={{
                          padding: "3px 8px",
                          borderRadius: "var(--radius-sm, 4px)",
                          border: isAlreadyAdded
                            ? "1px solid var(--border-subtle, #30363d)"
                            : "1px solid var(--color-brand, #58a6ff)",
                          backgroundColor: isAlreadyAdded
                            ? "transparent"
                            : "var(--color-primary-bg, rgba(88, 166, 255, 0.15))",
                          color: isAlreadyAdded
                            ? "var(--text-muted, #8b949e)"
                            : "var(--color-brand, #58a6ff)",
                          fontSize: "11px",
                          fontWeight: 600,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "2px",
                          opacity: isHovered || isHighlighted || isAlreadyAdded ? 1 : 0.85,
                          transition: "all 0.15s ease",
                        }}
                        title={isAlreadyAdded ? "Already in Watchlist" : "Add to active Watchlist"}
                      >
                        {isAlreadyAdded ? "✓ Added" : "+ Add"}
                      </button>
                    </div>
                  </li>
                );
              })
            )}
          </ul>

          {/* Keyboard footer hint */}
          <div
            style={{
              padding: "4px 8px",
              backgroundColor: "var(--bg-elevated, #11161d)",
              borderTop: "1px solid var(--border-subtle, #21262d)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "10px",
              color: "var(--text-muted, #8b949e)",
            }}
          >
            <span>
              <kbd style={{ padding: "0 3px", backgroundColor: "#21262d", borderRadius: "2px" }}>↑</kbd>{" "}
              <kbd style={{ padding: "0 3px", backgroundColor: "#21262d", borderRadius: "2px" }}>↓</kbd> navigate
            </span>
            <span>Click row for <strong>Option B Actions / Depth</strong></span>
            <span>
              <kbd style={{ padding: "0 3px", backgroundColor: "#21262d", borderRadius: "2px" }}>Esc</kbd> dismiss
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
