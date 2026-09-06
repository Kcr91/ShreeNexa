import React, { useState, useEffect, useRef, useMemo } from "react";
import { apiClient } from "../../api/client";
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

  // Market Depth modal instrument
  const [depthModalInstrument, setDepthModalInstrument] = useState<CatalogInstrument | null>(null);

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
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced API search when query changes
  useEffect(() => {
    const cleanQ = activeQuery.trim();
    if (!cleanQ || cleanQ.length < 1) {
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

        const token = apiClient.getCsrfToken() || "demo-csrf-token";
        const res = await fetch(
          `/api/v1/instruments/search?query=${encodeURIComponent(cleanQ)}&is_active_only=true${queryParams}&limit=100`,
          {
            credentials: "include",
            headers: {
              Accept: "application/json",
              Authorization: `Bearer ${token}`,
              "x-csrf-token": token,
            },
          }
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

    return merged.slice(0, 100);
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
      if (depthModalInstrument) {
        setDepthModalInstrument(null);
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
  };

  // Segment badges
  const getSegmentBadge = (inst: CatalogInstrument) => {
    if (inst.instrumentType === "INDEX" || inst.segment === "IDX_I") {
      return { label: "INDICES", bg: "rgba(163, 113, 247, 0.2)", color: "#a371f7", border: "rgba(163, 113, 247, 0.4)" };
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
    if (inst.segment === "BSE_EQ" || inst.segment === "BSE") {
      return { label: "BSE", bg: "rgba(210, 153, 34, 0.2)", color: "#d29922", border: "rgba(210, 153, 34, 0.4)" };
    }
    return { label: "NSE", bg: "rgba(88, 166, 255, 0.2)", color: "#58a6ff", border: "rgba(88, 166, 255, 0.4)" };
  };

  // Generate Market Depth Book for Depth Modal
  const depthBook: MarketDepthBook | null = useMemo(() => {
    if (!depthModalInstrument) return null;
    return generateMockDepthBook(
      depthModalInstrument.symbol,
      depthModalInstrument.segment,
      "LEVEL_20",
      depthModalInstrument.ltp || 1000,
      Number(depthModalInstrument.securityId) || 1333
    );
  }, [depthModalInstrument]);

  const depthCapability = useMemo(() => {
    if (!depthModalInstrument) return null;
    return resolveSegmentDepthCapability(depthModalInstrument.segment, "LEVEL_20");
  }, [depthModalInstrument]);

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

          {/* Market Depth Floating Modal */}
          {depthModalInstrument && depthBook && (
            <div
              role="dialog"
              aria-label="Market Depth Modal"
              style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0, 0, 0, 0.75)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 3000,
              }}
              onClick={() => setDepthModalInstrument(null)}
            >
              <div
                style={{
                  width: "500px",
                  maxWidth: "95vw",
                  backgroundColor: "var(--bg-surface, #161b22)",
                  borderRadius: "8px",
                  border: "1px solid var(--border-default, #30363d)",
                  padding: "16px",
                  boxShadow: "0 12px 36px rgba(0, 0, 0, 0.8)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontWeight: 700, color: "#fff", fontSize: "15px" }}>
                      {depthModalInstrument.tradingSymbol}
                    </span>
                    <span
                      style={{
                        fontSize: "10px",
                        padding: "1px 6px",
                        borderRadius: "3px",
                        backgroundColor: getSegmentBadge(depthModalInstrument).bg,
                        color: getSegmentBadge(depthModalInstrument).color,
                        border: `1px solid ${getSegmentBadge(depthModalInstrument).border}`,
                        fontWeight: 700,
                      }}
                    >
                      {getSegmentBadge(depthModalInstrument).label}
                    </span>
                    <span style={{ fontSize: "12px", color: "var(--text-muted, #8b949e)" }}>
                      {depthModalInstrument.name}
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {depthModalInstrument.ltp > 0 && (
                      <span style={{ fontFamily: "var(--font-family-mono)", fontWeight: 700, fontSize: "14px", color: "#fff" }}>
                        ₹{depthModalInstrument.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => setDepthModalInstrument(null)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--text-muted, #8b949e)",
                        cursor: "pointer",
                        fontSize: "16px",
                        padding: "2px 6px",
                      }}
                      title="Close modal"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {/* Capability & Spread Info */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "10px",
                    color: "var(--text-muted, #8b949e)",
                    fontSize: "11px",
                    backgroundColor: "var(--bg-elevated, #0d1117)",
                    padding: "6px 10px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle, #30363d)",
                  }}
                >
                  <span>
                    Capability:{" "}
                    <strong style={{ color: "#58a6ff" }}>
                      {depthCapability?.actualLevel === "LEVEL_20"
                        ? "20-Level Full Depth (NSE)"
                        : "5-Level Depth Feed (MCX/Forex/BSE)"}
                    </strong>
                  </span>
                  <span>
                    Spread: ₹{depthBook.spread.toFixed(2)} ({depthBook.spreadPct}%)
                  </span>
                </div>

                {/* Bids & Asks Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  {/* Bids */}
                  <div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "40px 1fr 1fr",
                        fontWeight: 600,
                        color: "#3fb950",
                        borderBottom: "1px solid rgba(63, 185, 80, 0.3)",
                        paddingBottom: "4px",
                        marginBottom: "4px",
                        fontSize: "11px",
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
                          gridTemplateColumns: "40px 1fr 1fr",
                          padding: "2px 0",
                          fontFamily: "var(--font-family-mono)",
                          fontSize: "11px",
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
                        marginTop: "6px",
                        paddingTop: "4px",
                        fontWeight: 600,
                        fontSize: "11px",
                      }}
                    >
                      <span>Total Bid</span>
                      <span style={{ fontFamily: "var(--font-family-mono)", color: "#3fb950" }}>
                        {depthBook.totalBidQty.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>

                  {/* Asks */}
                  <div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr 40px",
                        fontWeight: 600,
                        color: "#f85149",
                        borderBottom: "1px solid rgba(248, 81, 73, 0.3)",
                        paddingBottom: "4px",
                        marginBottom: "4px",
                        fontSize: "11px",
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
                          gridTemplateColumns: "1fr 1fr 40px",
                          padding: "2px 0",
                          fontFamily: "var(--font-family-mono)",
                          fontSize: "11px",
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
                        marginTop: "6px",
                        paddingTop: "4px",
                        fontWeight: 600,
                        fontSize: "11px",
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
              maxHeight: "360px",
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
                const isIndex = inst.instrumentType === "INDEX" || inst.segment === "IDX_I";

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
                    onClick={() => handleSelectAddDirectly(inst)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      cursor: "pointer",
                      borderBottom: "1px solid var(--border-subtle, #1e242c)",
                      backgroundColor:
                        isHovered || isHighlighted
                          ? "var(--bg-hover, #21262d)"
                          : "transparent",
                      transition: "background-color 0.1s ease",
                      minHeight: "42px",
                    }}
                  >
                    {/* Left: Symbol & Segment Badge & Description */}
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0, flex: 1 }}>
                      <span
                        style={{
                          fontWeight: 600,
                          color: "var(--text-primary, #f0f6fc)",
                          fontSize: "var(--font-size-sm, 13px)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {inst.tradingSymbol}
                      </span>

                      {/* Description */}
                      {inst.name && (
                        <span
                          style={{
                            fontSize: "11px",
                            color: "var(--text-muted, #8b949e)",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            maxWidth: isHovered || isHighlighted ? "140px" : "240px",
                          }}
                        >
                          {inst.name}
                        </span>
                      )}

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
                          marginLeft: (!isHovered && !isHighlighted) ? "auto" : undefined,
                        }}
                      >
                        {badge.label}
                      </span>
                    </div>

                    {/* Right: Zerodha Kite Hover Action Buttons (Images 1 & 2) */}
                    {isHovered || isHighlighted ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          marginLeft: "8px",
                        }}
                      >
                        {/* Buy & Sell Buttons: Only for non-indices (Image 1) */}
                        {!isIndex && (
                          <>
                            <button
                              type="button"
                              aria-label="Buy"
                              title="Buy (B)"
                              onClick={(e) => {
                                e.stopPropagation();
                                onBuy?.(inst);
                              }}
                              style={{
                                width: "26px",
                                height: "24px",
                                borderRadius: "3px",
                                border: "none",
                                backgroundColor: "#1976d2",
                                color: "#ffffff",
                                fontSize: "12px",
                                fontWeight: 700,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                padding: 0,
                                transition: "transform 0.1s ease",
                              }}
                            >
                              B
                            </button>
                            <button
                              type="button"
                              aria-label="Sell"
                              title="Sell (S)"
                              onClick={(e) => {
                                e.stopPropagation();
                                onSell?.(inst);
                              }}
                              style={{
                                width: "26px",
                                height: "24px",
                                borderRadius: "3px",
                                border: "none",
                                backgroundColor: "#ff5722",
                                color: "#ffffff",
                                fontSize: "12px",
                                fontWeight: 700,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                padding: 0,
                                transition: "transform 0.1s ease",
                              }}
                            >
                              S
                            </button>
                          </>
                        )}

                        {/* Market Depth Button (≡) */}
                        <button
                          type="button"
                          aria-label="Market Depth"
                          title="Market Depth"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenDepth?.(inst);
                            setDepthModalInstrument(inst);
                          }}
                          style={{
                            width: "26px",
                            height: "24px",
                            borderRadius: "3px",
                            border: "1px solid var(--border-subtle, #30363d)",
                            backgroundColor: "var(--bg-elevated, #21262d)",
                            color: "var(--text-primary, #f0f6fc)",
                            fontSize: "13px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: 0,
                          }}
                        >
                          ≡
                        </button>

                        {/* Chart Button (📈) */}
                        <button
                          type="button"
                          aria-label="Chart"
                          title="Chart"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenChart?.(inst);
                          }}
                          style={{
                            width: "26px",
                            height: "24px",
                            borderRadius: "3px",
                            border: "1px solid var(--border-subtle, #30363d)",
                            backgroundColor: "var(--bg-elevated, #21262d)",
                            color: "var(--text-primary, #f0f6fc)",
                            fontSize: "12px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: 0,
                          }}
                        >
                          📈
                        </button>

                        {/* Add to Watchlist Button (+) */}
                        <button
                          type="button"
                          aria-label={isAlreadyAdded ? "Already in Watchlist" : "Add to Watchlist"}
                          title={isAlreadyAdded ? "Already in Watchlist" : "Add to Watchlist"}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectAddDirectly(inst);
                          }}
                          style={{
                            width: "28px",
                            height: "24px",
                            borderRadius: "3px",
                            border: "none",
                            backgroundColor: isAlreadyAdded ? "rgba(46, 160, 67, 0.2)" : "#2e7d32",
                            color: isAlreadyAdded ? "#3fb950" : "#ffffff",
                            fontSize: "14px",
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: 0,
                          }}
                        >
                          {isAlreadyAdded ? "✓" : "+"}
                        </button>
                      </div>
                    ) : (
                      /* Not Hovered: LTP & Change */
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
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
                      </div>
                    )}
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
            <span>Hover row for <strong>Buy, Sell, Depth & Chart</strong></span>
            <span>
              <kbd style={{ padding: "0 3px", backgroundColor: "#21262d", borderRadius: "2px" }}>Esc</kbd> dismiss
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
