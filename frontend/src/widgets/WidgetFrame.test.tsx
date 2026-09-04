import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WidgetFrame } from "./WidgetFrame";
import "./builtin";

describe("WidgetFrame Component", () => {
  it("renders widget title and lazy-loaded content", async () => {
    render(<WidgetFrame instanceId="inst-1" widgetId="market-clock" />);

    expect(screen.getByText("Market Clock")).toBeInTheDocument();
    expect(await screen.findByText(/Market Session Clock/i)).toBeInTheDocument();
  });

  it("handles settings editor toggle and validation error display", async () => {
    const handleUpdate = vi.fn();
    render(
      <WidgetFrame
        instanceId="inst-1"
        widgetId="watchlist"
        onUpdateSettings={handleUpdate}
      />
    );

    await screen.findByText("NIFTY 50");

    // Open settings editor
    const settingsBtn = screen.getByLabelText("Widget Settings");
    fireEvent.click(settingsBtn);

    expect(screen.getByText("Widget Configuration")).toBeInTheDocument();
    expect(screen.getByLabelText("Refresh Interval (s)")).toBeInTheDocument();

    // Enter invalid refresh interval (e.g. 100 > max 60)
    const input = screen.getByLabelText("Refresh Interval (s)");
    fireEvent.change(input, { target: { value: "120" } });

    // Click Save Settings
    const saveBtn = screen.getByRole("button", { name: "Save Settings" });
    fireEvent.click(saveBtn);

    // Error alert is displayed
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/cannot be greater than 60/i)).toBeInTheDocument();
    expect(handleUpdate).not.toHaveBeenCalled();
  });
});
