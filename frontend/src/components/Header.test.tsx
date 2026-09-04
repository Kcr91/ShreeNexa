import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./Header";
import { apiClient, TokenHealthResponse } from "../api/client";
import { AuthProvider } from "../auth/AuthContext";

describe("Header Component Token Health Badge (QA-07 & QA-08)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const renderWithAuth = () => {
    return render(
      <AuthProvider>
        <Header />
      </AuthProvider>
    );
  };

  it("renders HEALTHY with duration when token status is 'valid'", async () => {
    const mockHealth: TokenHealthResponse = {
      status: "valid",
      is_valid: true,
      expires_in_seconds: 45000, // 12h 30m
      client_id_masked: "1111***478",
      source: "environment",
    };
    vi.spyOn(apiClient, "getTokenHealth").mockResolvedValue(mockHealth);

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: HEALTHY");
    expect(badge).toHaveTextContent("12h 30m");
  });

  it("renders EXPIRING SOON when token status is 'expiring_soon'", async () => {
    const mockHealth: TokenHealthResponse = {
      status: "expiring_soon",
      is_valid: true,
      expires_in_seconds: 1800, // 30m
      client_id_masked: "1111***478",
      source: "environment",
    };
    vi.spyOn(apiClient, "getTokenHealth").mockResolvedValue(mockHealth);

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: EXPIRING SOON");
    expect(badge).toHaveTextContent("30m");
  });

  it("renders EXPIRED when token status is 'expired'", async () => {
    const mockHealth: TokenHealthResponse = {
      status: "expired",
      is_valid: false,
      expires_in_seconds: 0,
      client_id_masked: "1111***478",
      source: "environment",
    };
    vi.spyOn(apiClient, "getTokenHealth").mockResolvedValue(mockHealth);

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: EXPIRED");
  });

  it("renders REVOKED when token status is 'revoked'", async () => {
    const mockHealth: TokenHealthResponse = {
      status: "revoked",
      is_valid: false,
      expires_in_seconds: 0,
      client_id_masked: "1111***478",
      source: "environment",
    };
    vi.spyOn(apiClient, "getTokenHealth").mockResolvedValue(mockHealth);

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: REVOKED");
  });

  it("renders NOT CONFIGURED when token status is 'missing'", async () => {
    const mockHealth: TokenHealthResponse = {
      status: "missing",
      is_valid: false,
      expires_in_seconds: null,
      client_id_masked: "[NONE]",
      source: "none",
    };
    vi.spyOn(apiClient, "getTokenHealth").mockResolvedValue(mockHealth);

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: NOT CONFIGURED");
  });

  it("renders API UNREACHABLE when network call fails", async () => {
    vi.spyOn(apiClient, "getTokenHealth").mockRejectedValue(new Error("Connection refused"));

    renderWithAuth();

    const badge = await screen.findByRole("status");
    expect(badge).toHaveTextContent("Dhan Feed: API UNREACHABLE");
  });
});
