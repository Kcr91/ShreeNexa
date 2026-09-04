import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuthProvider, useAuth, unauthenticatedUser } from "./AuthContext";
import { apiClient } from "../api/client";

describe("AuthContext and Session Hydration (QA-03)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to unauthenticated state with isAuthenticated: false (QA-03)", () => {
    expect(unauthenticatedUser.isAuthenticated).toBe(false);
    expect(unauthenticatedUser.username).toBe("");

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider autoCheck={false}>{children}</AuthProvider>,
    });

    expect(result.current.user.isAuthenticated).toBe(false);
    expect(result.current.user.username).toBe("");
  });

  it("hydrates active session on mount when /api/v1/auth/me succeeds", async () => {
    vi.spyOn(apiClient, "getCurrentUser").mockResolvedValueOnce({
      username: "verified_trader",
      authenticated: true,
      csrf_token: "csrf_hydrate_token_123",
      expires_at: "2026-09-05T18:00:00Z",
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider autoCheck={true}>{children}</AuthProvider>,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.user.isAuthenticated).toBe(true);
      expect(result.current.user.username).toBe("verified_trader");
      expect(result.current.user.csrfToken).toBe("csrf_hydrate_token_123");
      expect(apiClient.getCsrfToken()).toBe("csrf_hydrate_token_123");
    });
  });

  it("gracefully fails to unauthenticated when /api/v1/auth/me returns 401", async () => {
    vi.spyOn(apiClient, "getCurrentUser").mockRejectedValueOnce(
      new Error("HTTP Error 401: Unauthorized")
    );

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider autoCheck={true}>{children}</AuthProvider>,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.user.isAuthenticated).toBe(false);
      expect(result.current.user.username).toBe("");
      expect(apiClient.getCsrfToken()).toBeNull();
    });
  });

  it("logout revokes session and clears authentication and CSRF token", async () => {
    vi.spyOn(apiClient, "logout").mockResolvedValueOnce({
      status: "logged_out",
      message: "Session terminated",
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => (
        <AuthProvider
          initialUser={{
            username: "active_trader",
            role: "trader",
            isAuthenticated: true,
            dhanClientId: "",
            csrfToken: "active_csrf_999",
          }}
          autoCheck={false}
        >
          {children}
        </AuthProvider>
      ),
    });

    expect(result.current.user.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user.isAuthenticated).toBe(false);
    expect(result.current.user.username).toBe("");
    expect(apiClient.getCsrfToken()).toBeNull();
    expect(apiClient.logout).toHaveBeenCalledTimes(1);
  });
});
