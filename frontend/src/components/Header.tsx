import React, { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiClient, TokenHealthResponse } from "../api/client";

export const Header: React.FC = () => {
  const { user } = useAuth();
  const [tokenHealth, setTokenHealth] = useState<TokenHealthResponse | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    // Clock update
    const updateClock = () => {
      const now = new Date();
      const istString = now.toLocaleTimeString("en-IN", {
        timeZone: "Asia/Kolkata",
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      setCurrentTime(`${istString} IST`);
    };

    updateClock();
    const clockTimer = setInterval(updateClock, 1000);

    // Fetch Token Health
    apiClient
      .getTokenHealth()
      .then((res) => setTokenHealth(res))
      .catch(() => {
        setTokenHealth({ status: "not_configured", message: "Offline / Dev Stub" });
      });

    return () => clearInterval(clockTimer);
  }, []);

  const getStatusColor = (status?: string) => {
    switch (status) {
      case "active":
        return { bg: "var(--color-up-bg)", text: "var(--color-up)" };
      case "expiring_soon":
        return { bg: "var(--color-warning-bg)", text: "var(--color-warning)" };
      case "expired":
        return { bg: "var(--color-down-bg)", text: "var(--color-down)" };
      default:
        return { bg: "var(--bg-surface)", text: "var(--text-muted)" };
    }
  };

  const statusStyle = getStatusColor(tokenHealth?.status);

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
          aria-label={`Dhan Token Status: ${tokenHealth?.status || "Checking..."}`}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--spacing-2)",
            padding: "var(--spacing-1) var(--spacing-3)",
            borderRadius: "var(--radius-full)",
            backgroundColor: statusStyle.bg,
            color: statusStyle.text,
            fontSize: "var(--font-size-xs)",
            fontWeight: 600,
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "var(--radius-full)",
              backgroundColor: statusStyle.text,
            }}
          />
          Dhan Feed: {tokenHealth?.status ? tokenHealth.status.replace("_", " ").toUpperCase() : "CHECKING"}
        </div>

        {/* Live Clock */}
        <div
          style={{
            fontFamily: "var(--font-family-mono)",
            fontSize: "var(--font-size-sm)",
            color: "var(--text-secondary)",
          }}
        >
          {currentTime || "--:--:-- IST"}
        </div>

        {/* User Pill */}
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
          <strong>{user.username}</strong>
        </div>
      </div>
    </header>
  );
};
