import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import "./widgets/builtin";

describe("App Shell and Layout", () => {
  it("renders terminal header, navigation, and workspace layout tabs", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "ShreeNexa Terminal" })).toBeInTheDocument();
    expect(screen.getByText(/Connected Intelligence. Prosperous Decisions./i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Terminal primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();
    expect(screen.getByText("Market Clock")).toBeInTheDocument();
  });
});
