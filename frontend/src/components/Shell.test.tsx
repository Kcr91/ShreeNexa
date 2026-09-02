import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import { Shell } from "./Shell";

describe("Shell Navigation and Route Switching", () => {
  it("switches views when clicking navigation tabs", () => {
    render(
      <AuthProvider>
        <Shell />
      </AuthProvider>
    );

    // Initial view is Executive Dashboard
    expect(screen.getByRole("heading", { name: "Executive Dashboard" })).toBeInTheDocument();

    // Click on Strategy Lab
    const labTab = screen.getByRole("tab", { name: /Strategy Lab/i });
    fireEvent.click(labTab);
    expect(screen.getByRole("heading", { name: "Strategy Research Lab" })).toBeInTheDocument();

    // Click on Screener
    const screenerTab = screen.getByRole("tab", { name: /PIT Screener/i });
    fireEvent.click(screenerTab);
    expect(screen.getByRole("heading", { name: "Point-in-Time Screener" })).toBeInTheDocument();

    // Click on P&L
    const pnlTab = screen.getByRole("tab", { name: /Daily P&L \/ TWR/i });
    fireEvent.click(pnlTab);
    expect(screen.getByRole("heading", { name: "Daily P&L & Performance Ledger" })).toBeInTheDocument();

    // Click on Settings
    const settingsTab = screen.getByRole("tab", { name: /Settings/i });
    fireEvent.click(settingsTab);
    expect(screen.getByRole("heading", { name: "Terminal Settings & Integrations" })).toBeInTheDocument();
  });
});
