import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider } from "./AuthContext";
import { LoginView } from "./LoginView";
import { apiClient } from "../api/client";

describe("LoginView Component and 2FA Flow (QA-03)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders master password input and branding initially", () => {
    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    expect(screen.getByRole("heading", { name: "ShreeNexa Terminal" })).toBeInTheDocument();
    expect(screen.getByText(/2FA Institutional Gateway/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Master Trader Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Continue to 2FA/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Lost TOTP Device/i })).toBeInTheDocument();
  });

  it("advances to TOTP verification step upon valid master password", async () => {
    vi.spyOn(apiClient, "login").mockResolvedValueOnce({
      requires_totp: true,
      challenge_token: "mock_challenge_token_xyz",
      message: "TOTP challenge issued",
    });

    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    const passwordInput = screen.getByLabelText(/Master Trader Password/i);
    fireEvent.change(passwordInput, { target: { value: "ShreeNexa2026!SecureTerminal" } });

    const submitBtn = screen.getByRole("button", { name: /Continue to 2FA/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByLabelText(/6-Digit TOTP Code/i)).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText("000000")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Verify & Enter Terminal/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Back to Password/i })).toBeInTheDocument();
  });

  it("displays error message when login fails with invalid password", async () => {
    vi.spyOn(apiClient, "login").mockRejectedValueOnce(
      new Error("Invalid master password. 4 attempts remaining.")
    );

    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    const passwordInput = screen.getByLabelText(/Master Trader Password/i);
    fireEvent.change(passwordInput, { target: { value: "WrongPassword" } });

    const submitBtn = screen.getByRole("button", { name: /Continue to 2FA/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText(/Invalid master password/i)).toBeInTheDocument();
    });
  });

  it("completes TOTP verification and updates auth state", async () => {
    vi.spyOn(apiClient, "login").mockResolvedValueOnce({
      requires_totp: true,
      challenge_token: "mock_challenge_token_xyz",
      message: "TOTP challenge issued",
    });

    vi.spyOn(apiClient, "verifyTotp").mockResolvedValueOnce({
      username: "master_trader",
      authenticated: true,
      csrf_token: "csrf_token_secret_456",
      expires_at: "2026-09-05T12:00:00Z",
      message: "Authenticated successfully",
    });

    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    // Step 1: Submit password
    fireEvent.change(screen.getByLabelText(/Master Trader Password/i), {
      target: { value: "ValidPassword123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Continue to 2FA/i }));

    // Step 2: Submit 6-digit TOTP
    await waitFor(() => {
      expect(screen.getByLabelText(/6-Digit TOTP Code/i)).toBeInTheDocument();
    });

    const totpInput = screen.getByLabelText(/6-Digit TOTP Code/i);
    fireEvent.change(totpInput, { target: { value: "123456" } });

    const verifyBtn = screen.getByRole("button", { name: /Verify & Enter Terminal/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(apiClient.verifyTotp).toHaveBeenCalledWith("mock_challenge_token_xyz", "123456");
      expect(apiClient.getCsrfToken()).toBe("csrf_token_secret_456");
    });
  });

  it("switches to emergency recovery code mode and submits successfully", async () => {
    vi.spyOn(apiClient, "loginWithRecovery").mockResolvedValueOnce({
      username: "master_trader",
      authenticated: true,
      csrf_token: "recovery_csrf_token_789",
      expires_at: "2026-09-05T12:00:00Z",
      message: "Emergency recovery login successful",
    });

    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    // Click to switch to recovery view
    fireEvent.click(screen.getByRole("button", { name: /Lost TOTP Device/i }));

    expect(screen.getByLabelText(/Single-Use Recovery Code/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Use Single-Use Code/i })).toBeInTheDocument();

    // Fill password and recovery code
    fireEvent.change(screen.getByLabelText(/Master Trader Password/i), {
      target: { value: "MasterPassword2026" },
    });
    fireEvent.change(screen.getByLabelText(/Single-Use Recovery Code/i), {
      target: { value: "RECOVERY-1234-5678" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Use Single-Use Code/i }));

    await waitFor(() => {
      expect(apiClient.loginWithRecovery).toHaveBeenCalledWith(
        "MasterPassword2026",
        "RECOVERY-1234-5678"
      );
      expect(apiClient.getCsrfToken()).toBe("recovery_csrf_token_789");
    });
  });

  it("allows returning to normal login from recovery mode and password mode from totp mode", async () => {
    vi.spyOn(apiClient, "login").mockResolvedValueOnce({
      requires_totp: true,
      challenge_token: "challenge_abc",
      message: "TOTP required",
    });

    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    // Enter recovery mode
    fireEvent.click(screen.getByRole("button", { name: /Lost TOTP Device/i }));
    expect(screen.getByLabelText(/Single-Use Recovery Code/i)).toBeInTheDocument();

    // Return to password mode
    fireEvent.click(screen.getByRole("button", { name: /Return to Normal Login/i }));
    expect(screen.getByLabelText(/Master Trader Password/i)).toBeInTheDocument();

    // Advance to TOTP
    fireEvent.change(screen.getByLabelText(/Master Trader Password/i), {
      target: { value: "Password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Continue to 2FA/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/6-Digit TOTP Code/i)).toBeInTheDocument();
    });

    // Go back to password
    fireEvent.click(screen.getByRole("button", { name: /Back to Password/i }));
    expect(screen.getByLabelText(/Master Trader Password/i)).toBeInTheDocument();
  });

  it("renders Launch Dry Run / Demo Mode button and activates demo mode", () => {
    render(
      <AuthProvider autoCheck={false}>
        <LoginView />
      </AuthProvider>
    );

    const demoBtn = screen.getByRole("button", { name: /Launch Dry Run \/ Demo Mode/i });
    expect(demoBtn).toBeInTheDocument();
    fireEvent.click(demoBtn);
  });
});
