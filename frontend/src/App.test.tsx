import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { UserSession } from "./auth/AuthContext";

const mockAuthenticatedUser: UserSession = {
  username: "dev_trader",
  role: "developer",
  isAuthenticated: true,
  dhanClientId: "DHAN_LOCAL_DEV",
};

describe("App Shell and Layout", () => {
  it("renders login gateway view when unauthenticated by default (QA-03)", async () => {
    render(<App autoCheckAuth={false} />);

    expect(screen.getByRole("heading", { name: "ShreeNexa Terminal" })).toBeInTheDocument();
    expect(screen.getByText(/2FA Institutional Gateway/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Master Trader Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Continue to 2FA/i })).toBeInTheDocument();
  });

  it("renders terminal header, navigation, and workspace layout tabs when authenticated", async () => {
    render(<App initialUser={mockAuthenticatedUser} />);

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
