import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App Shell and Layout", () => {
  it("renders terminal header, navigation, and executive dashboard", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "ShreeNexa Terminal" })).toBeInTheDocument();
    expect(screen.getByText(/Connected Intelligence. Prosperous Decisions./i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Terminal primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeInTheDocument();
  });
});
