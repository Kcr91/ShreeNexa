import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App Shell and Layout", () => {
  it("renders terminal header, navigation, and workspace layout tabs", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "ShreeNexa Terminal" })).toBeInTheDocument();
    expect(screen.getByText(/Connected Intelligence. Prosperous Decisions./i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Terminal primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();
    expect(screen.getByText("Market Clock")).toBeInTheDocument();
    expect(screen.getByText("Backtest Performance Summary")).toBeInTheDocument();
    expect(await screen.findByText(/Market Session Clock/i)).toBeInTheDocument();
    expect(screen.queryByText(/Widget not found:/i)).not.toBeInTheDocument();
  });
});
