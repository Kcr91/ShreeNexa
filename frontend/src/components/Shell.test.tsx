import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import { Shell } from "./Shell";
import "../widgets/builtin";

describe("Shell Navigation and Route Switching", () => {
  it("switches views when clicking navigation tabs", () => {
    render(
      <AuthProvider>
        <Shell />
      </AuthProvider>
    );

    const nav = screen.getByRole("navigation", { name: "Terminal primary navigation" });

    // Initial view is Executive Dashboard with workspace layout
    expect(screen.getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();

    // Click on Strategy Lab nav item
    const labNavBtn = within(nav).getByRole("tab", { name: /Strategy Lab/i });
    fireEvent.click(labNavBtn);
    expect(screen.getByRole("heading", { name: "Strategy Research Lab" })).toBeInTheDocument();

    // Click on Screener nav item
    const screenerNavBtn = within(nav).getByRole("tab", { name: /PIT Screener/i });
    fireEvent.click(screenerNavBtn);
    expect(screen.getByRole("heading", { name: "Point-in-Time Screener" })).toBeInTheDocument();

    // Click on P&L nav item
    const pnlNavBtn = within(nav).getByRole("tab", { name: /Daily P&L \/ TWR/i });
    fireEvent.click(pnlNavBtn);
    expect(screen.getByRole("heading", { name: "Daily P&L & Performance Ledger" })).toBeInTheDocument();

    // Click on Settings nav item
    const settingsNavBtn = within(nav).getByRole("tab", { name: /Settings/i });
    fireEvent.click(settingsNavBtn);
    expect(screen.getByRole("heading", { name: "Terminal Settings & Integrations" })).toBeInTheDocument();
  });
});
