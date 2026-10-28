import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiClient, TokenHealthResponse, ApiError } from "../api/client";

export const SettingsView: React.FC = () => {
  const { user } = useAuth();

  // Active section tab
  const [activeTab, setActiveTab] = useState<"dhan" | "password" | "session">("dhan");

  // --- Dhan Token State ---
  const [tokenHealth, setTokenHealth] = useState<TokenHealthResponse | null>(null);
  const [isTokenLoading, setIsTokenLoading] = useState<boolean>(false);
  const [newToken, setNewToken] = useState<string>("");
  const [newClientId, setNewClientId] = useState<string>("");
  const [showToken, setShowToken] = useState<boolean>(false);
  const [tokenSuccess, setTokenSuccess] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [isSubmittingToken, setIsSubmittingToken] = useState<boolean>(false);

  // --- Password State ---
  const [currentPassword, setCurrentPassword] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showCurrentPw, setShowCurrentPw] = useState<boolean>(false);
  const [showNewPw, setShowNewPw] = useState<boolean>(false);
  const [showConfirmPw, setShowConfirmPw] = useState<boolean>(false);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isSubmittingPassword, setIsSubmittingPassword] = useState<boolean>(false);

  // Load token health on mount
  const fetchTokenHealth = useCallback(async () => {
    setIsTokenLoading(true);
    setTokenError(null);
    try {
      const health = await apiClient.getTokenHealth();
      setTokenHealth(health);
      if (health.client_id_masked && !newClientId) {
        setNewClientId(health.client_id_masked.replace(/\*/g, ""));
      }
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to load Dhan token status";
      setTokenError(msg);
    } finally {
      setIsTokenLoading(false);
    }
  }, [newClientId]);

  useEffect(() => {
    fetchTokenHealth();
  }, [fetchTokenHealth]);

  // Handle Dhan token update
  const handleUpdateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newToken.trim()) {
      setTokenError("Please enter a valid Dhan access token.");
      return;
    }

    setIsSubmittingToken(true);
    setTokenError(null);
    setTokenSuccess(null);

    try {
      const updatedHealth = await apiClient.updateDhanToken(newToken.trim(), newClientId.trim() || undefined);
      setTokenHealth(updatedHealth);
      setTokenSuccess(
        `Dhan access token updated successfully! Valid until ${
          updatedHealth.expires_at ? new Date(updatedHealth.expires_at).toLocaleString() : "end of day"
        }.`
      );
      setNewToken("");
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to update Dhan token.";
      setTokenError(msg);
    } finally {
      setIsSubmittingToken(false);
    }
  };

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      setPasswordError("Please enter your current master password.");
      return;
    }
    if (!newPassword || newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters long.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirm password do not match.");
      return;
    }

    setIsSubmittingPassword(true);
    setPasswordError(null);
    setPasswordSuccess(null);

    try {
      const res = await apiClient.changePassword(currentPassword, newPassword, confirmPassword);
      setPasswordSuccess(res.message || "Master password updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : "Failed to change password.";
      setPasswordError(msg);
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  // Status Badge Helper
  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "valid":
        return { label: "VALID", bg: "var(--color-up-bg)", color: "var(--color-up)", border: "var(--color-up)" };
      case "expiring_soon":
        return { label: "EXPIRING SOON", bg: "var(--color-warning-bg)", color: "var(--color-warning)", border: "var(--color-warning)" };
      case "expired":
        return { label: "EXPIRED", bg: "var(--color-down-bg)", color: "var(--color-down)", border: "var(--color-down)" };
      default:
        return { label: status?.toUpperCase() || "UNKNOWN", bg: "rgba(139, 148, 158, 0.15)", color: "var(--text-muted)", border: "var(--border-default)" };
    }
  };

  const badge = getStatusBadge(tokenHealth?.status);

  return (
    <div
      style={{
        padding: "var(--spacing-6)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--spacing-6)",
        maxWidth: "1000px",
        margin: "0 auto",
        width: "100%",
        overflowY: "auto",
        height: "100%",
      }}
    >
      {/* Header */}
      <div>
        <h2 style={{ fontSize: "var(--font-size-2xl)", fontWeight: 700, color: "var(--text-primary)", marginBottom: "var(--spacing-1)" }}>
          Terminal Settings & Integrations
        </h2>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Manage your Dhan API credentials, change the master terminal password, and review active session parameters.
        </p>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: "var(--spacing-2)",
          borderBottom: "1px solid var(--border-default)",
          paddingBottom: "var(--spacing-2)",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("dhan")}
          style={{
            padding: "var(--spacing-2) var(--spacing-4)",
            borderRadius: "var(--radius-md)",
            border: "none",
            backgroundColor: activeTab === "dhan" ? "var(--color-primary-bg)" : "transparent",
            color: activeTab === "dhan" ? "var(--color-primary)" : "var(--text-muted)",
            fontWeight: 600,
            fontSize: "var(--font-size-sm)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-2)",
            transition: "all 0.15s ease",
          }}
        >
          <span>🔑</span> Dhan Access Token
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("password")}
          style={{
            padding: "var(--spacing-2) var(--spacing-4)",
            borderRadius: "var(--radius-md)",
            border: "none",
            backgroundColor: activeTab === "password" ? "var(--color-primary-bg)" : "transparent",
            color: activeTab === "password" ? "var(--color-primary)" : "var(--text-muted)",
            fontWeight: 600,
            fontSize: "var(--font-size-sm)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-2)",
            transition: "all 0.15s ease",
          }}
        >
          <span>🔒</span> Change Password
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("session")}
          style={{
            padding: "var(--spacing-2) var(--spacing-4)",
            borderRadius: "var(--radius-md)",
            border: "none",
            backgroundColor: activeTab === "session" ? "var(--color-primary-bg)" : "transparent",
            color: activeTab === "session" ? "var(--color-primary)" : "var(--text-muted)",
            fontWeight: 600,
            fontSize: "var(--font-size-sm)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-2)",
            transition: "all 0.15s ease",
          }}
        >
          <span>👤</span> Active Session
        </button>
      </div>

      {/* TAB 1: DHAN ACCESS TOKEN */}
      {activeTab === "dhan" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
          {/* Current Status Card */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: "var(--spacing-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--spacing-4)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, color: "var(--text-primary)" }}>
                Current Dhan Token Status
              </h3>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
                <span
                  style={{
                    fontSize: "var(--font-size-xs)",
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: badge.bg,
                    color: badge.color,
                    border: `1px solid ${badge.border}`,
                    letterSpacing: "0.5px",
                  }}
                >
                  {badge.label}
                </span>
                <button
                  type="button"
                  onClick={fetchTokenHealth}
                  disabled={isTokenLoading}
                  style={{
                    backgroundColor: "transparent",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    padding: "4px 8px",
                    fontSize: "var(--font-size-xs)",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                  }}
                >
                  {isTokenLoading ? "Refreshing..." : "↻ Refresh"}
                </button>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "var(--spacing-4)",
                paddingTop: "var(--spacing-2)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Client ID:</span>
                <span style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, fontFamily: "var(--font-family-mono)" }}>
                  {tokenHealth?.client_id_masked || user.dhanClientId || "Not configured"}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Storage Source:</span>
                <span style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                  {tokenHealth?.source === "dpapi" ? "🔒 Windows DPAPI (Encrypted)" : tokenHealth?.source === "dotenv" ? "📄 .env (Local Config)" : tokenHealth?.source || "Unconfigured"}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Time Remaining:</span>
                <span style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, color: tokenHealth?.is_valid ? "var(--color-up)" : "var(--color-down)" }}>
                  {tokenHealth?.expires_in_seconds && tokenHealth.expires_in_seconds > 0
                    ? `${Math.floor(tokenHealth.expires_in_seconds / 3600)}h ${Math.floor((tokenHealth.expires_in_seconds % 3600) / 60)}m`
                    : tokenHealth?.is_valid ? "Active" : "Expired / Missing"}
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Expires At:</span>
                <span style={{ fontSize: "var(--font-size-sm)" }}>
                  {tokenHealth?.expires_at ? new Date(tokenHealth.expires_at).toLocaleString() : "Unknown"}
                </span>
              </div>
            </div>
          </div>

          {/* Update Token Form Card */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: "var(--spacing-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--spacing-4)",
            }}
          >
            <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, color: "var(--text-primary)" }}>
              Update Dhan 24-Hour Access Token
            </h3>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Paste your new 24-hour access token generated from{" "}
              <a href="https://web.dhan.co" target="_blank" rel="noreferrer" style={{ color: "var(--color-primary)", textDecoration: "underline" }}>
                web.dhan.co
              </a>{" "}
              (Profile → Access Token). Updating here automatically secures it in the terminal's encrypted DPAPI vault and updates your local runtime configuration.
            </p>

            {tokenSuccess && (
              <div
                style={{
                  backgroundColor: "var(--color-up-bg)",
                  border: "1px solid var(--color-up)",
                  color: "var(--color-up)",
                  padding: "var(--spacing-3)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-sm)",
                  fontWeight: 500,
                }}
              >
                ✓ {tokenSuccess}
              </div>
            )}

            {tokenError && (
              <div
                style={{
                  backgroundColor: "var(--color-down-bg)",
                  border: "1px solid var(--color-down)",
                  color: "var(--color-down)",
                  padding: "var(--spacing-3)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-sm)",
                  fontWeight: 500,
                }}
              >
                ✕ {tokenError}
              </div>
            )}

            <form onSubmit={handleUpdateToken} style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-4)" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label htmlFor="dhan-token-input" style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                    New Access Token (JWT):
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    style={{
                      background: "none",
                      border: "none",
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-primary)",
                      cursor: "pointer",
                    }}
                  >
                    {showToken ? "Hide Token" : "Show Token"}
                  </button>
                </div>
                <textarea
                  id="dhan-token-input"
                  rows={3}
                  value={newToken}
                  onChange={(e) => setNewToken(e.target.value)}
                  placeholder="eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9..."
                  style={{
                    width: "100%",
                    padding: "var(--spacing-3)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontFamily: "var(--font-family-mono)",
                    fontSize: "var(--font-size-sm)",
                    resize: "vertical",
                    outline: "none",
                  }}
                  required
                />
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
                <label htmlFor="dhan-clientid-input" style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                  Client ID (Optional - auto-derived from token if left blank):
                </label>
                <input
                  id="dhan-clientid-input"
                  type="text"
                  value={newClientId}
                  onChange={(e) => setNewClientId(e.target.value)}
                  placeholder="e.g. 1100340656"
                  style={{
                    width: "100%",
                    padding: "var(--spacing-3)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontFamily: "var(--font-family-mono)",
                    fontSize: "var(--font-size-sm)",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isSubmittingToken || !newToken.trim()}
                  style={{
                    backgroundColor: isSubmittingToken || !newToken.trim() ? "var(--bg-active)" : "var(--color-primary)",
                    color: isSubmittingToken || !newToken.trim() ? "var(--text-muted)" : "#ffffff",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--spacing-3) var(--spacing-6)",
                    fontSize: "var(--font-size-sm)",
                    fontWeight: 600,
                    cursor: isSubmittingToken || !newToken.trim() ? "not-allowed" : "pointer",
                    transition: "background-color 0.15s ease",
                  }}
                >
                  {isSubmittingToken ? "Encrypting & Updating..." : "Update Token in Terminal"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: CHANGE PASSWORD */}
      {activeTab === "password" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-6)" }}>
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: "var(--spacing-6)",
              display: "flex",
              flexDirection: "column",
              gap: "var(--spacing-4)",
            }}
          >
            <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, color: "var(--text-primary)" }}>
              Change Master Password
            </h3>
            <p style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)", lineHeight: 1.6 }}>
              Update the master login password for the ShreeNexa terminal. Passwords are cryptographically salted and hashed using PBKDF2-SHA256 (600,000 rounds).
            </p>

            {passwordSuccess && (
              <div
                style={{
                  backgroundColor: "var(--color-up-bg)",
                  border: "1px solid var(--color-up)",
                  color: "var(--color-up)",
                  padding: "var(--spacing-3)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-sm)",
                  fontWeight: 500,
                }}
              >
                ✓ {passwordSuccess}
              </div>
            )}

            {passwordError && (
              <div
                style={{
                  backgroundColor: "var(--color-down-bg)",
                  border: "1px solid var(--color-down)",
                  color: "var(--color-down)",
                  padding: "var(--spacing-3)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-sm)",
                  fontWeight: 500,
                }}
              >
                ✕ {passwordError}
              </div>
            )}

            <form onSubmit={handleChangePassword} style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-4)" }}>
              {/* Current Password */}
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label htmlFor="current-pw-input" style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                    Current Master Password:
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowCurrentPw(!showCurrentPw)}
                    style={{
                      background: "none",
                      border: "none",
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-primary)",
                      cursor: "pointer",
                    }}
                  >
                    {showCurrentPw ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  id="current-pw-input"
                  type={showCurrentPw ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  style={{
                    width: "100%",
                    padding: "var(--spacing-3)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: "var(--font-size-sm)",
                    outline: "none",
                  }}
                  required
                />
              </div>

              {/* New Password */}
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label htmlFor="new-pw-input" style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                    New Master Password (min 8 characters):
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowNewPw(!showNewPw)}
                    style={{
                      background: "none",
                      border: "none",
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-primary)",
                      cursor: "pointer",
                    }}
                  >
                    {showNewPw ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  id="new-pw-input"
                  type={showNewPw ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new strong password"
                  style={{
                    width: "100%",
                    padding: "var(--spacing-3)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: "var(--font-size-sm)",
                    outline: "none",
                  }}
                  required
                />
              </div>

              {/* Confirm Password */}
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label htmlFor="confirm-pw-input" style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>
                    Confirm New Password:
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowConfirmPw(!showConfirmPw)}
                    style={{
                      background: "none",
                      border: "none",
                      fontSize: "var(--font-size-xs)",
                      color: "var(--color-primary)",
                      cursor: "pointer",
                    }}
                  >
                    {showConfirmPw ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  id="confirm-pw-input"
                  type={showConfirmPw ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  style={{
                    width: "100%",
                    padding: "var(--spacing-3)",
                    backgroundColor: "var(--bg-secondary)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: "var(--font-size-sm)",
                    outline: "none",
                  }}
                  required
                />
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isSubmittingPassword || !currentPassword || !newPassword || !confirmPassword}
                  style={{
                    backgroundColor:
                      isSubmittingPassword || !currentPassword || !newPassword || !confirmPassword
                        ? "var(--bg-active)"
                        : "var(--color-primary)",
                    color:
                      isSubmittingPassword || !currentPassword || !newPassword || !confirmPassword
                        ? "var(--text-muted)"
                        : "#ffffff",
                    border: "none",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--spacing-3) var(--spacing-6)",
                    fontSize: "var(--font-size-sm)",
                    fontWeight: 600,
                    cursor:
                      isSubmittingPassword || !currentPassword || !newPassword || !confirmPassword
                        ? "not-allowed"
                        : "pointer",
                    transition: "background-color 0.15s ease",
                  }}
                >
                  {isSubmittingPassword ? "Updating Master Password..." : "Update Master Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 3: ACTIVE SESSION */}
      {activeTab === "session" && (
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "var(--spacing-6)",
          }}
        >
          <h3 style={{ fontSize: "var(--font-size-lg)", fontWeight: 600, marginBottom: "var(--spacing-4)" }}>
            Active Session Parameters
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "var(--spacing-3)", fontSize: "var(--font-size-sm)" }}>
            <div style={{ color: "var(--text-muted)" }}>Authenticated User:</div>
            <div style={{ fontWeight: 600 }}>{user.username}</div>

            <div style={{ color: "var(--text-muted)" }}>Role:</div>
            <div>{user.role}</div>

            <div style={{ color: "var(--text-muted)" }}>Dhan Client ID:</div>
            <div style={{ fontFamily: "var(--font-family-mono)" }}>{tokenHealth?.client_id_masked || user.dhanClientId || "Not loaded"}</div>

            <div style={{ color: "var(--text-muted)" }}>Session Expiry:</div>
            <div>{user.expiresAt ? new Date(user.expiresAt).toLocaleString() : "Active (24-hour cookie)"}</div>

            <div style={{ color: "var(--text-muted)" }}>Execution Mode:</div>
            <div>Paper / Research Only (Live execution gated behind Epic 12 approval)</div>
          </div>
        </div>
      )}
    </div>
  );
};
