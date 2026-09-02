import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { LayoutProvider } from "./LayoutContext";
import { LayoutManager } from "./LayoutManager";
import "../widgets/builtin";

describe("LayoutManager Component and Tab Switching", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders default tabs and active tab widgets", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    expect(screen.getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Strategy Lab/i })).toBeInTheDocument();

    // Default overview widgets
    expect(screen.getByText("Market Clock")).toBeInTheDocument();
    expect(screen.getByText("Market Watchlist")).toBeInTheDocument();
  });

  it("switches tabs when clicking on a tab button", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    const labTab = screen.getByRole("tab", { name: /Strategy Lab/i });
    fireEvent.click(labTab);

    // Active tab is now Strategy Lab with BankNifty Strangle widget
    expect(screen.getByText(/BankNifty Multi-Leg Strangle/i)).toBeInTheDocument();
  });

  it("opens widget palette, adds a widget, and closes modal", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    // Click Add Widget button in tab bar
    const openPaletteBtn = screen.getByRole("button", { name: /Add Widget/i });
    fireEvent.click(openPaletteBtn);

    // Palette modal is open
    expect(screen.getByRole("dialog", { name: "Widget Palette" })).toBeInTheDocument();

    // Add Fixture Dynamic Test Widget
    const addFixtureBtn = screen.getByTestId("palette-item-fixture-test").querySelector("button");
    expect(addFixtureBtn).toBeDefined();
    if (addFixtureBtn) {
      fireEvent.click(addFixtureBtn);
    }

    // Modal closed and widget is rendered on grid
    expect(screen.queryByRole("dialog", { name: "Widget Palette" })).not.toBeInTheDocument();
    expect(screen.getByText("Fixture Dynamic Test Widget")).toBeInTheDocument();
  });

  it("resets workspace layout to defaults when clicking Reset button", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    const resetBtn = screen.getByRole("button", { name: /Reset Workspace Layout/i });
    fireEvent.click(resetBtn);

    expect(screen.getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();
  });
});
