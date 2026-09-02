import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WidgetPalette } from "./WidgetPalette";
import { widgetRegistry } from "./registry";
import { WidgetDefinition } from "./types";
import "./builtin";

describe("WidgetPalette Component", () => {
  it("renders registered widgets and filters by search query", () => {
    const handleAdd = vi.fn();
    render(<WidgetPalette onAddWidget={handleAdd} />);

    expect(screen.getByRole("dialog", { name: "Widget Palette" })).toBeInTheDocument();
    expect(screen.getByText("Market Watchlist")).toBeInTheDocument();
    expect(screen.getByText("Market Clock")).toBeInTheDocument();

    // Search filter
    const searchInput = screen.getByLabelText("Search widgets");
    fireEvent.change(searchInput, { target: { value: "clock" } });

    expect(screen.getByText("Market Clock")).toBeInTheDocument();
    expect(screen.queryByText("Market Watchlist")).not.toBeInTheDocument();
  });

  it("dynamic runtime fixture widget appears in palette without code modifications", () => {
    const dynamicDef: WidgetDefinition = {
      id: "runtime-custom-widget",
      title: "Runtime Discovered Widget",
      description: "Appears in palette immediately",
      category: "custom",
      icon: "🌟",
      defaultWidth: 250,
      defaultHeight: 200,
      schema: { fields: [] },
      component: () => null,
    };
    widgetRegistry.register(dynamicDef);

    const handleAdd = vi.fn();
    render(<WidgetPalette onAddWidget={handleAdd} />);

    expect(screen.getByText("Runtime Discovered Widget")).toBeInTheDocument();

    const addBtn = screen.getByTestId("palette-item-runtime-custom-widget").querySelector("button");
    expect(addBtn).toBeDefined();
    if (addBtn) {
      fireEvent.click(addBtn);
      expect(handleAdd).toHaveBeenCalledWith("runtime-custom-widget");
    }
  });
});
