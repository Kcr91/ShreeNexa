import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiClient, TokenHealthResponse } from "../api/client";

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const [tokenHealth, setTokenHealth] = useState<TokenHealthResponse | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch Token Health
    apiClient
      .getTokenHealth()
      .then((res) => {
        setTokenHealth(res);
        setFetchError(null);
      })
      .catch((err: unknown) => {
        setTokenHealth(null);
        setFetchError(err instanceof Error ? err.message : "API Unreachable");
      });
  }, []);

  const getStatusDisplay = () => {
    if (fetchError) {
      return {
        bg: "var(--color-down-bg, rgba(239, 68, 68, 0.2))",
        text: "var(--color-down, #ef4444)",
        label: "API UNREACHABLE",
        detail: "",
      };
    }
    if (!tokenHealth) {
      return {
        bg: "var(--bg-surface)",
        text: "var(--text-muted)",
        label: "CHECKING...",
        detail: "",
      };
    }

    let detail = "";
    if (tokenHealth.expires_in_seconds != null && tokenHealth.expires_in_seconds > 0) {
      const hrs = Math.floor(tokenHealth.expires_in_seconds / 3600);
      const mins = Math.floor((tokenHealth.expires_in_seconds % 3600) / 60);
      detail = hrs > 0 ? `${hrs}h ${mins}m` : `${mins}m`;
    }

    switch (tokenHealth.status) {
      case "valid":
        return {
          bg: "var(--color-up-bg, rgba(34, 197, 94, 0.2))",
          text: "var(--color-up, #22c55e)",
          label: "HEALTHY",
          detail,
        };
      case "expiring_soon":
        return {
          bg: "var(--color-warning-bg, rgba(234, 179, 8, 0.2))",
          text: "var(--color-warning, #eab308)",
          label: "EXPIRING SOON",
          detail,
        };
      case "expired":
        return {
          bg: "var(--color-down-bg, rgba(239, 68, 68, 0.2))",
          text: "var(--color-down, #ef4444)",
          label: "EXPIRED",
          detail: "Expired",
        };
      case "revoked":
        return {
          bg: "var(--color-down-bg, rgba(239, 68, 68, 0.2))",
          text: "var(--color-down, #ef4444)",
          label: "REVOKED",
          detail: "Revoked",
        };
      case "missing":
        return {
          bg: "var(--color-down-bg, rgba(239, 68, 68, 0.2))",
          text: "var(--color-down, #ef4444)",
          label: "NOT CONFIGURED",
          detail: "No token",
        };
      case "unknown_expiry":
        return {
          bg: "var(--color-warning-bg, rgba(234, 179, 8, 0.2))",
          text: "var(--color-warning, #eab308)",
          label: "UNKNOWN EXPIRY",
          detail,
        };
      default:
        return {
          bg: "var(--bg-surface)",
          text: "var(--text-muted)",
          label: String(tokenHealth.status).replace("_", " ").toUpperCase(),
          detail,
        };
    }
  };

  const statusInfo = getStatusDisplay();

  return (
    <header
      role="banner"
      style={{
        height: "var(--header-height)",
        backgroundColor: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 var(--spacing-4)",
        userSelect: "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-3)" }}>
        <div
          style={{
            width: "12px",
            height: "12px",
            borderRadius: "var(--radius-full)",
            backgroundColor: "var(--color-primary)",
            boxShadow: "0 0 8px var(--color-primary)",
          }}
        />
        <h1
          style={{
            fontSize: "var(--font-size-lg)",
            fontWeight: "bold",
            letterSpacing: "0.5px",
            color: "var(--text-primary)",
          }}
        >
          ShreeNexa Terminal
        </h1>
        <span
          style={{
            fontSize: "var(--font-size-xs)",
            color: "var(--text-muted)",
            borderLeft: "1px solid var(--border-default)",
            paddingLeft: "var(--spacing-3)",
          }}
        >
          Connected Intelligence. Prosperous Decisions.
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-4)" }}>
        {/* Token Health Badge */}
        <div
          role="status"
          aria-label={`Dhan Token Status: ${statusInfo.label}${statusInfo.detail ? ` (${statusInfo.detail})` : ""}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-2)",
            padding: "var(--spacing-1) var(--spacing-3)",
            borderRadius: "var(--radius-full)",
            backgroundColor: statusInfo.bg,
            color: statusInfo.text,
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "var(--radius-full)",
              backgroundColor: statusInfo.text,
            }}
          />
          Dhan Feed: {statusInfo.label}
          {statusInfo.detail && (
            <span style={{ opacity: 0.85, fontWeight: 500 }}>({statusInfo.detail})</span>
          )}
        </div>

        {/* User Pill & Sign Out */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--spacing-2)",
              padding: "var(--spacing-1) var(--spacing-3)",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              fontSize: "var(--font-size-xs)",
              color: "var(--text-primary)",
            }}
          >
            <span style={{ color: "var(--text-muted)" }}>User:</span>
            <strong>{user.username || "anonymous"}</strong>
          </div>

          <button
            type="button"
            onClick={() => void logout()}
            aria-label="Sign out from terminal"
            title="Terminate session"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "var(--spacing-1) var(--spacing-2)",
              borderRadius: "var(--radius-md)",
              backgroundColor: "transparent",
              border: "1px solid var(--border-default)",
              color: "var(--text-muted)",
              fontSize: "var(--font-size-xs)",
              cursor: "pointer",
            }}
          >
            Sign Out
          </button>
        </div>
      </div>
    </header>
  );
};
