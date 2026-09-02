import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { LayoutProvider } from "./LayoutContext";
import { LayoutManager } from "./LayoutManager";
import "../widgets/builtin";

describe("Template and JSON Export/Import Layout Integration", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("opens template modal and applies Options Desk template", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    // Open Templates modal
    const templateBtn = screen.getByRole("button", { name: "Workspace Templates" });
    fireEvent.click(templateBtn);

    expect(screen.getByText("Workspace Templates")).toBeInTheDocument();
    expect(screen.getByTestId("template-card-options-desk")).toBeInTheDocument();

    // Apply Options Desk template
    const applyBtn = screen.getByTestId("template-card-options-desk").querySelector("button")!;
    fireEvent.click(applyBtn);

    // Verify template modal closed and Options Desk tab active
    expect(screen.queryByText("Workspace Templates")).not.toBeInTheDocument();
    expect(screen.getByText("Options Desk")).toBeInTheDocument();
  });

  it("opens JSON export/import modal, modifies JSON, and imports new layout", () => {
    render(
      <LayoutProvider>
        <LayoutManager />
      </LayoutProvider>
    );

    // Open JSON modal
    const jsonBtn = screen.getByRole("button", { name: "Export Import Layout" });
    fireEvent.click(jsonBtn);

    expect(screen.getByText("Export / Import Workspace JSON")).toBeInTheDocument();

    const textarea = screen.getByLabelText("Layout JSON Configuration");
    expect(textarea).toHaveValue();

    // Paste invalid JSON and click Import
    fireEvent.change(textarea, { target: { value: "{ invalid json" } });
    const importBtn = screen.getByRole("button", { name: "Import & Apply" });
    fireEvent.click(importBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Invalid JSON syntax");
  });
});
