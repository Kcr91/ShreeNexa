import { fireEvent, render, screen, within } from "@testing-library/react";
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

  it("navigates to widget palette options and renders them full-screen", async () => {
    render(
      <AuthProvider>
        <Shell />
      </AuthProvider>
    );

    const nav = screen.getByRole("navigation", { name: "Terminal primary navigation" });
    const main = screen.getByRole("main");

    // 1. Navigate to Technical Chart full screen
    const chartBtn = within(nav).getByRole("tab", { name: /Candlestick Chart/i });
    fireEvent.click(chartBtn);

    expect(await within(main).findByText("Candlestick Chart")).toBeInTheDocument();

    // 2. Navigate to Options Chain full screen
    const optionsBtn = within(nav).getByRole("tab", { name: /Option Chain & Greeks/i });
    fireEvent.click(optionsBtn);

    expect(await within(main).findByText("Option Chain & Greeks")).toBeInTheDocument();

    // 3. Navigate to Positions & Orders Blotter full screen
    const blotterBtn = within(nav).getByRole("tab", { name: /Positions & Orders Blotter/i });
    fireEvent.click(blotterBtn);

    expect(await within(main).findByText("Positions & Orders Blotter")).toBeInTheDocument();

    // 4. Return to Dashboard
    const dashboardBtn = within(nav).getByRole("tab", { name: /Dashboard/i });
    fireEvent.click(dashboardBtn);

    expect(within(main).getByRole("tab", { name: /Main Overview/i })).toBeInTheDocument();
  });

  it("filters navigation items via search box", () => {
    render(
      <AuthProvider>
        <Shell />
      </AuthProvider>
    );

    const nav = screen.getByRole("navigation", { name: "Terminal primary navigation" });
    const searchInput = within(nav).getByPlaceholderText(/Filter views & apps/i);

    fireEvent.change(searchInput, { target: { value: "Blotter" } });

    expect(within(nav).getByRole("tab", { name: /Positions & Orders Blotter/i })).toBeInTheDocument();
    expect(within(nav).queryByRole("tab", { name: /Settings/i })).not.toBeInTheDocument();
  });
});
