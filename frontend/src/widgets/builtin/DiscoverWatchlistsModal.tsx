import React, { useState, useEffect, useRef } from "react";
import { Watchlist } from "../../watchlist/types";
import {
  searchStandardWatchlists,
  StandardWatchlistDefinition,
} from "../../watchlist/standardWatchlists";

export interface DiscoverWatchlistsModalProps {
  isOpen: boolean;
  onClose: () => void;
  userWatchlists: Watchlist[];
  activeWatchlistId: string;
  onSelectWatchlist: (id: string) => void;
  onAddStandardWatchlist: (presetId: string) => void;
  onCreateCustomWatchlist: (name: string) => void;
  onDeleteWatchlist: (id: string) => void;
}

export const DiscoverWatchlistsModal: React.FC<DiscoverWatchlistsModalProps> = ({
  isOpen,
  onClose,
  userWatchlists,
  activeWatchlistId,
  onSelectWatchlist,
  onAddStandardWatchlist,
  onCreateCustomWatchlist,
  onDeleteWatchlist,
}) => {
  const [activeTab, setActiveTab] = useState<"discover" | "my-lists" | "new-list">("discover");
  const [searchQuery, setSearchQuery] = useState("");
  const [newListName, setNewListName] = useState("");
  const [hoveredPresetId, setHoveredPresetId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Global Ctrl + Shift + K shortcut to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && (e.key === "K" || e.key === "k")) {
        e.preventDefault();
        setActiveTab("discover");
        setTimeout(() => searchInputRef.current?.focus(), 50);
      } else if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Focus search input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredPresets = searchStandardWatchlists(searchQuery);
  const indicesPresets = filteredPresets.filter((p) => p.category === "INDICES");
  const fnoPresets = filteredPresets.filter((p) => p.category === "F&O STOCKS");

  // Check if a standard watchlist is already added in user's watchlists
  const isAlreadyAdded = (preset: StandardWatchlistDefinition) => {
    const slug = preset.id.replace("std-", "");
    return userWatchlists.some(
      (w) =>
        w.id === preset.id ||
        w.id.startsWith(`wl-std-${slug}`) ||
        w.name === preset.name
    );
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newListName.trim()) return;
    onCreateCustomWatchlist(newListName.trim());
    setNewListName("");
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-label="Discover Watchlists Modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.65)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backdropFilter: "blur(4px)",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        style={{
          width: "440px",
          maxWidth: "92vw",
          maxHeight: "85vh",
          backgroundColor: "#181818",
          color: "#e0e0e0",
          borderRadius: "8px",
          border: "1px solid #2e2e2e",
          boxShadow: "0 16px 40px rgba(0, 0, 0, 0.6)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          fontFamily: "var(--font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
        }}
      >
        {/* 1. Zerodha Search Header */}
        <div
          style={{
            padding: "12px 16px 8px 16px",
            borderBottom: "1px solid #282828",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              backgroundColor: "#202020",
              border: "1px solid #333333",
              borderRadius: "6px",
              padding: "6px 10px",
              gap: "8px",
            }}
          >
            {/* Search Glass Icon */}
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#888" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>

            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search lists"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (activeTab !== "discover") setActiveTab("discover");
              }}
              style={{
                flex: 1,
                backgroundColor: "transparent",
                border: "none",
                outline: "none",
                color: "#f0f0f0",
                fontSize: "13px",
              }}
            />

            {/* Ctrl + Shift + K Badge */}
            <span
              style={{
                fontSize: "10px",
                color: "#777",
                backgroundColor: "#282828",
                border: "1px solid #383838",
                borderRadius: "3px",
                padding: "2px 6px",
                userSelect: "none",
                letterSpacing: "0.5px",
              }}
            >
              Ctrl + Shift + K
            </span>

            {/* Close Button */}
            <button
              onClick={onClose}
              aria-label="Close modal"
              style={{
                background: "transparent",
                border: "none",
                color: "#888",
                cursor: "pointer",
                padding: "2px",
                display: "flex",
                alignItems: "center",
                fontSize: "14px",
              }}
              title="Close (Esc)"
            >
              ✕
            </button>
          </div>

          {/* 2. Zerodha Tabs Row: "My lists" | "Discover" | "+ New list" */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid #222",
              paddingBottom: "2px",
            }}
          >
            <div style={{ display: "flex", gap: "16px" }}>
              <button
                onClick={() => setActiveTab("my-lists")}
                style={{
                  background: "transparent",
                  border: "none",
                  padding: "6px 0",
                  fontSize: "13px",
                  fontWeight: activeTab === "my-lists" ? 600 : 400,
                  color: activeTab === "my-lists" ? "#f0f0f0" : "#888888",
                  cursor: "pointer",
                  borderBottom: activeTab === "my-lists" ? "2px solid #ff5722" : "2px solid transparent",
                }}
              >
                My lists ({userWatchlists.length})
              </button>
              <button
                onClick={() => setActiveTab("discover")}
                style={{
                  background: "transparent",
                  border: "none",
                  padding: "6px 0",
                  fontSize: "13px",
                  fontWeight: activeTab === "discover" ? 600 : 400,
                  color: activeTab === "discover" ? "#f0f0f0" : "#888888",
                  cursor: "pointer",
                  borderBottom: activeTab === "discover" ? "2px solid #ff5722" : "2px solid transparent",
                }}
              >
                Discover
              </button>
            </div>

            <button
              onClick={() => setActiveTab("new-list")}
              style={{
                background: "transparent",
                border: "none",
                padding: "6px 0",
                fontSize: "13px",
                fontWeight: activeTab === "new-list" ? 600 : 400,
                color: activeTab === "new-list" ? "#ff5722" : "#387ed1",
                cursor: "pointer",
              }}
            >
              + New list
            </button>
          </div>
        </div>

        {/* 3. Modal Body based on activeTab */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "8px 0",
          }}
        >
          {/* TAB: DISCOVER */}
          {activeTab === "discover" && (
            <div>
              {/* Option 1: Create New List (Requested: "first option should show create new list and other options are readymade watchlist") */}
              <div
                style={{
                  padding: "10px 14px",
                  margin: "4px 12px 12px 12px",
                  backgroundColor: "#20252b",
                  border: "1px solid #2e4158",
                  borderRadius: "6px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "14px", color: "#387ed1" }}>➕</span>
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "#f0f0f0" }}>
                      Create new list
                    </span>
                  </div>
                  <span style={{ fontSize: "11px", color: "#8fa3b7" }}>
                    Blank custom watchlist
                  </span>
                </div>
                <form
                  onSubmit={handleCreateSubmit}
                  style={{ display: "flex", gap: "8px", alignItems: "center" }}
                >
                  <input
                    type="text"
                    placeholder="Watchlist Name (e.g. IT Sector)"
                    value={newListName}
                    onChange={(e) => setNewListName(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "6px 10px",
                      backgroundColor: "#16191f",
                      border: "1px solid #3d5675",
                      borderRadius: "4px",
                      color: "#f0f0f0",
                      fontSize: "12px",
                      outline: "none",
                    }}
                  />
                  <button
                    type="submit"
                    disabled={!newListName.trim()}
                    style={{
                      padding: "6px 14px",
                      backgroundColor: newListName.trim() ? "#ff5722" : "#333",
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: 500,
                      cursor: newListName.trim() ? "pointer" : "default",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Create
                  </button>
                </form>
              </div>

              {/* INDICES Section */}
              {indicesPresets.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <div
                    style={{
                      padding: "6px 16px",
                      fontSize: "10px",
                      fontWeight: 700,
                      letterSpacing: "0.8px",
                      color: "#777",
                      textTransform: "uppercase",
                    }}
                  >
                    INDICES
                  </div>

                  {indicesPresets.map((preset) => {
                    const added = isAlreadyAdded(preset);
                    const isHovered = hoveredPresetId === preset.id;
                    return (
                      <div
                        key={preset.id}
                        onMouseEnter={() => setHoveredPresetId(preset.id)}
                        onMouseLeave={() => setHoveredPresetId(null)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 16px",
                          cursor: "pointer",
                          backgroundColor: isHovered ? "#242424" : "transparent",
                          transition: "background-color 0.1s ease",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            flex: 1,
                            overflow: "hidden",
                          }}
                          onClick={() => {
                            onAddStandardWatchlist(preset.id);
                          }}
                        >
                          {/* Zerodha Stack / Layers Icon */}
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#777" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12 2 2 7 12 12 22 7 12 2" />
                            <polyline points="2 17 12 22 22 17" />
                            <polyline points="2 12 12 17 22 12" />
                          </svg>

                          <div style={{ overflow: "hidden" }}>
                            <div
                              style={{
                                fontSize: "13px",
                                color: "#f0f0f0",
                                fontWeight: isHovered ? 500 : 400,
                                whiteSpace: "nowrap",
                                textOverflow: "ellipsis",
                                overflow: "hidden",
                              }}
                            >
                              {preset.name}
                            </div>
                          </div>
                        </div>

                        {/* Action: "+ Add to my lists" or "✓ Added" */}
                        <div>
                          {added ? (
                            <span
                              style={{
                                fontSize: "11px",
                                color: "#4caf50",
                                padding: "3px 8px",
                                borderRadius: "3px",
                                backgroundColor: "rgba(76, 175, 80, 0.1)",
                              }}
                            >
                              ✓ Added
                            </span>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onAddStandardWatchlist(preset.id);
                              }}
                              style={{
                                display: isHovered ? "inline-block" : "none",
                                background: "transparent",
                                border: "none",
                                color: "#ff5722",
                                fontSize: "12px",
                                fontWeight: 500,
                                cursor: "pointer",
                                padding: "2px 6px",
                              }}
                            >
                              + Add to my lists
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* F&O STOCKS Section */}
              {fnoPresets.length > 0 && (
                <div>
                  <div
                    style={{
                      padding: "6px 16px",
                      fontSize: "10px",
                      fontWeight: 700,
                      letterSpacing: "0.8px",
                      color: "#777",
                      textTransform: "uppercase",
                    }}
                  >
                    F&O STOCKS
                  </div>

                  {fnoPresets.map((preset) => {
                    const added = isAlreadyAdded(preset);
                    const isHovered = hoveredPresetId === preset.id;
                    return (
                      <div
                        key={preset.id}
                        onMouseEnter={() => setHoveredPresetId(preset.id)}
                        onMouseLeave={() => setHoveredPresetId(null)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 16px",
                          cursor: "pointer",
                          backgroundColor: isHovered ? "#242424" : "transparent",
                          transition: "background-color 0.1s ease",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                            flex: 1,
                            overflow: "hidden",
                          }}
                          onClick={() => {
                            onAddStandardWatchlist(preset.id);
                          }}
                        >
                          {/* Stack / Layers Icon */}
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#777" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="12 2 2 7 12 12 22 7 12 2" />
                            <polyline points="2 17 12 22 22 17" />
                            <polyline points="2 12 12 17 22 12" />
                          </svg>

                          <div>
                            <div
                              style={{
                                fontSize: "13px",
                                color: "#f0f0f0",
                                fontWeight: isHovered ? 500 : 400,
                              }}
                            >
                              {preset.name}
                            </div>
                            <div style={{ fontSize: "11px", color: "#666" }}>
                              {preset.itemCount} scrips
                            </div>
                          </div>
                        </div>

                        {/* Action: "+ Add to my lists" or "✓ Added" */}
                        <div>
                          {added ? (
                            <span
                              style={{
                                fontSize: "11px",
                                color: "#4caf50",
                                padding: "3px 8px",
                                borderRadius: "3px",
                                backgroundColor: "rgba(76, 175, 80, 0.1)",
                              }}
                            >
                              ✓ Added
                            </span>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onAddStandardWatchlist(preset.id);
                              }}
                              style={{
                                display: isHovered ? "inline-block" : "none",
                                background: "transparent",
                                border: "none",
                                color: "#ff5722",
                                fontSize: "12px",
                                fontWeight: 500,
                                cursor: "pointer",
                                padding: "2px 6px",
                              }}
                            >
                              + Add to my lists
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB: MY LISTS */}
          {activeTab === "my-lists" && (
            <div style={{ padding: "8px 16px" }}>
              <div style={{ fontSize: "11px", color: "#888", marginBottom: "8px" }}>
                Switch or manage your active watchlists:
              </div>

              {userWatchlists.map((wl) => {
                const isActive = wl.id === activeWatchlistId;
                return (
                  <div
                    key={wl.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      marginBottom: "6px",
                      borderRadius: "6px",
                      backgroundColor: isActive ? "#262c33" : "#202020",
                      border: isActive ? "1px solid #387ed1" : "1px solid #2a2a2a",
                    }}
                  >
                    <div
                      style={{ cursor: "pointer", flex: 1 }}
                      onClick={() => {
                        onSelectWatchlist(wl.id);
                        onClose();
                      }}
                    >
                      <div style={{ fontSize: "13px", fontWeight: isActive ? 600 : 400, color: isActive ? "#64b5f6" : "#f0f0f0" }}>
                        {wl.name}
                      </div>
                      <div style={{ fontSize: "11px", color: "#888" }}>
                        {wl.items.length} stocks {wl.isGroupedBySector && "• Grouped by sector"}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      {!isActive && (
                        <button
                          onClick={() => {
                            onSelectWatchlist(wl.id);
                            onClose();
                          }}
                          style={{
                            background: "transparent",
                            border: "1px solid #444",
                            color: "#ccc",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            cursor: "pointer",
                          }}
                        >
                          View
                        </button>
                      )}
                      {!wl.isDefault && (
                        <button
                          onClick={() => onDeleteWatchlist(wl.id)}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "#ef5350",
                            fontSize: "12px",
                            cursor: "pointer",
                            padding: "3px 6px",
                          }}
                          title="Delete watchlist"
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TAB: + NEW LIST (Custom Creation Form) */}
          {activeTab === "new-list" && (
            <form onSubmit={handleCreateSubmit} style={{ padding: "16px" }}>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#f0f0f0", marginBottom: "8px" }}>
                Create New Watchlist
              </div>
              <div style={{ fontSize: "11px", color: "#888", marginBottom: "12px" }}>
                Enter a unique name for your custom blank watchlist.
              </div>

              <input
                type="text"
                placeholder="Watchlist Name (e.g. IT Sector)"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                autoFocus
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "8px 10px",
                  borderRadius: "4px",
                  border: "1px solid #444",
                  backgroundColor: "#222",
                  color: "#f0f0f0",
                  fontSize: "13px",
                  marginBottom: "16px",
                  outline: "none",
                }}
              />

              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setActiveTab("discover")}
                  style={{
                    padding: "6px 12px",
                    background: "transparent",
                    border: "1px solid #444",
                    color: "#aaa",
                    borderRadius: "4px",
                    fontSize: "12px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newListName.trim()}
                  style={{
                    padding: "6px 16px",
                    backgroundColor: newListName.trim() ? "#ff5722" : "#555",
                    color: "#fff",
                    border: "none",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: 500,
                    cursor: newListName.trim() ? "pointer" : "not-allowed",
                  }}
                >
                  Create
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
