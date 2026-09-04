import React, { useState, FormEvent } from "react";
import { useAuth } from "./AuthContext";

export const LoginView: React.FC = () => {
  const { initiateLogin, completeTotp, completeRecovery, error, setError } = useAuth();

  const [step, setStep] = useState<"password" | "totp" | "recovery">("password");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [challengeToken, setChallengeToken] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const activeError = localError || error;

  const handlePasswordSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setLocalError("Please enter your master trader password.");
      return;
    }

    setLocalError(null);
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await initiateLogin(password);
      if (res.requiresTotp && res.challengeToken) {
        setChallengeToken(res.challengeToken);
        setStep("totp");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setLocalError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTotpSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!totpCode.trim() || totpCode.trim().length !== 6) {
      setLocalError("Please enter a valid 6-digit TOTP code.");
      return;
    }

    setLocalError(null);
    setError(null);
    setIsSubmitting(true);

    try {
      await completeTotp(challengeToken, totpCode.trim());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "TOTP verification failed";
      setLocalError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRecoverySubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!password.trim() || !recoveryCode.trim()) {
      setLocalError("Please provide both master password and emergency recovery code.");
      return;
    }

    setLocalError(null);
    setError(null);
    setIsSubmitting(true);

    try {
      await completeRecovery(password, recoveryCode.trim());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Recovery login failed";
      setLocalError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        backgroundColor: "var(--bg-primary, #0a0e14)",
        padding: "var(--spacing-4, 1rem)",
        fontFamily: "var(--font-family-sans)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          backgroundColor: "var(--bg-surface, #161b22)",
          border: "1px solid var(--border-default, #30363d)",
          borderRadius: "var(--radius-lg, 8px)",
          boxShadow: "var(--shadow-lg, 0 10px 15px rgba(0, 0, 0, 0.4))",
          padding: "var(--spacing-8, 2rem)",
        }}
      >
        {/* Terminal Header & Branding */}
        <div style={{ textAlign: "center", marginBottom: "var(--spacing-6, 1.5rem)" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--spacing-2, 0.5rem)",
              backgroundColor: "var(--color-primary-bg, rgba(88, 166, 255, 0.15))",
              color: "var(--color-primary, #58a6ff)",
              padding: "2px 8px",
              borderRadius: "var(--radius-full, 9999px)",
              fontSize: "var(--font-size-xs, 0.75rem)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "var(--spacing-3, 0.75rem)",
            }}
          >
            <span>🔒</span> 2FA Institutional Gateway
          </div>
          <h1
            style={{
              fontSize: "var(--font-size-2xl, 1.5rem)",
              fontWeight: 700,
              color: "var(--text-primary, #f0f6fc)",
              margin: 0,
            }}
          >
            ShreeNexa Terminal
          </h1>
          <p
            style={{
              fontSize: "var(--font-size-sm, 0.8125rem)",
              color: "var(--text-muted, #8b949e)",
              marginTop: "var(--spacing-1, 0.25rem)",
            }}
          >
            Connected Intelligence. Prosperous Decisions.
          </p>
        </div>

        {/* Error Alert */}
        {activeError && (
          <div
            role="alert"
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "var(--spacing-2, 0.5rem)",
              backgroundColor: "var(--color-down-bg, rgba(248, 81, 73, 0.15))",
              border: "1px solid var(--color-down, #f85149)",
              color: "var(--color-down, #f85149)",
              padding: "var(--spacing-3, 0.75rem)",
              borderRadius: "var(--radius-md, 6px)",
              fontSize: "var(--font-size-sm, 0.8125rem)",
              marginBottom: "var(--spacing-4, 1rem)",
            }}
          >
            <span style={{ fontSize: "1rem" }}>⚠️</span>
            <div style={{ flex: 1 }}>{activeError}</div>
          </div>
        )}

        {/* STEP 1: Master Password */}
        {step === "password" && (
          <form onSubmit={handlePasswordSubmit} aria-label="Master Password Form">
            <div style={{ marginBottom: "var(--spacing-4, 1rem)" }}>
              <label
                htmlFor="master-password"
                style={{
                  display: "block",
                  fontSize: "var(--font-size-sm, 0.8125rem)",
                  fontWeight: 600,
                  color: "var(--text-secondary, #c9d1d9)",
                  marginBottom: "var(--spacing-1, 0.25rem)",
                }}
              >
                Master Trader Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="master-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter secure master password"
                  autoFocus
                  required
                  style={{
                    width: "100%",
                    padding: "10px 40px 10px 12px",
                    backgroundColor: "var(--bg-secondary, #11161d)",
                    border: "1px solid var(--border-default, #30363d)",
                    borderRadius: "var(--radius-md, 6px)",
                    color: "var(--text-primary, #f0f6fc)",
                    fontSize: "var(--font-size-base, 0.875rem)",
                    outline: "none",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  style={{
                    position: "absolute",
                    right: "10px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--text-muted, #8b949e)",
                    fontSize: "var(--font-size-sm, 0.8125rem)",
                    padding: "4px",
                  }}
                >
                  {showPassword ? "🙈" : "👁️"}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "10px 16px",
                backgroundColor: "var(--color-primary, #58a6ff)",
                color: "var(--text-inverse, #0a0e14)",
                fontWeight: 600,
                fontSize: "var(--font-size-base, 0.875rem)",
                border: "none",
                borderRadius: "var(--radius-md, 6px)",
                cursor: isSubmitting ? "not-allowed" : "pointer",
                opacity: isSubmitting ? 0.7 : 1,
                transition: "opacity 0.2s ease",
              }}
            >
              {isSubmitting ? "Authenticating..." : "Continue to 2FA"}
            </button>

            <div style={{ textAlign: "center", marginTop: "var(--spacing-4, 1rem)" }}>
              <button
                type="button"
                onClick={() => {
                  setLocalError(null);
                  setError(null);
                  setStep("recovery");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--color-primary, #58a6ff)",
                  fontSize: "var(--font-size-xs, 0.75rem)",
                  cursor: "pointer",
                  textDecoration: "none",
                }}
              >
                Lost TOTP Device? Use Emergency Recovery Code
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: TOTP Code */}
        {step === "totp" && (
          <form onSubmit={handleTotpSubmit} aria-label="TOTP Verification Form">
            <div style={{ marginBottom: "var(--spacing-4, 1rem)" }}>
              <label
                htmlFor="totp-code"
                style={{
                  display: "block",
                  fontSize: "var(--font-size-sm, 0.8125rem)",
                  fontWeight: 600,
                  color: "var(--text-secondary, #c9d1d9)",
                  marginBottom: "var(--spacing-1, 0.25rem)",
                }}
              >
                6-Digit TOTP Code
              </label>
              <input
                id="totp-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                autoFocus
                required
                style={{
                  width: "100%",
                  padding: "12px",
                  backgroundColor: "var(--bg-secondary, #11161d)",
                  border: "1px solid var(--border-default, #30363d)",
                  borderRadius: "var(--radius-md, 6px)",
                  color: "var(--text-primary, #f0f6fc)",
                  fontSize: "var(--font-size-xl, 1.25rem)",
                  fontFamily: "var(--font-family-mono)",
                  textAlign: "center",
                  letterSpacing: "0.5em",
                  outline: "none",
                }}
              />
              <span
                style={{
                  display: "block",
                  fontSize: "var(--font-size-xs, 0.75rem)",
                  color: "var(--text-muted, #8b949e)",
                  marginTop: "var(--spacing-1, 0.25rem)",
                  textAlign: "center",
                }}
              >
                Enter code from Google Authenticator or hardware token
              </span>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || totpCode.length !== 6}
              style={{
                width: "100%",
                padding: "10px 16px",
                backgroundColor: "var(--color-primary, #58a6ff)",
                color: "var(--text-inverse, #0a0e14)",
                fontWeight: 600,
                fontSize: "var(--font-size-base, 0.875rem)",
                border: "none",
                borderRadius: "var(--radius-md, 6px)",
                cursor: isSubmitting || totpCode.length !== 6 ? "not-allowed" : "pointer",
                opacity: isSubmitting || totpCode.length !== 6 ? 0.7 : 1,
                transition: "opacity 0.2s ease",
              }}
            >
              {isSubmitting ? "Verifying..." : "Verify & Enter Terminal"}
            </button>

            <div style={{ textAlign: "center", marginTop: "var(--spacing-4, 1rem)" }}>
              <button
                type="button"
                onClick={() => {
                  setLocalError(null);
                  setError(null);
                  setStep("password");
                  setTotpCode("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted, #8b949e)",
                  fontSize: "var(--font-size-xs, 0.75rem)",
                  cursor: "pointer",
                }}
              >
                ← Back to Password
              </button>
            </div>
          </form>
        )}

        {/* STEP 3: Emergency Recovery */}
        {step === "recovery" && (
          <form onSubmit={handleRecoverySubmit} aria-label="Recovery Login Form">
            <div style={{ marginBottom: "var(--spacing-3, 0.75rem)" }}>
              <label
                htmlFor="recovery-password"
                style={{
                  display: "block",
                  fontSize: "var(--font-size-sm, 0.8125rem)",
                  fontWeight: 600,
                  color: "var(--text-secondary, #c9d1d9)",
                  marginBottom: "var(--spacing-1, 0.25rem)",
                }}
              >
                Master Trader Password
              </label>
              <input
                id="recovery-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter master password"
                required
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  backgroundColor: "var(--bg-secondary, #11161d)",
                  border: "1px solid var(--border-default, #30363d)",
                  borderRadius: "var(--radius-md, 6px)",
                  color: "var(--text-primary, #f0f6fc)",
                  fontSize: "var(--font-size-base, 0.875rem)",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ marginBottom: "var(--spacing-4, 1rem)" }}>
              <label
                htmlFor="recovery-code"
                style={{
                  display: "block",
                  fontSize: "var(--font-size-sm, 0.8125rem)",
                  fontWeight: 600,
                  color: "var(--text-secondary, #c9d1d9)",
                  marginBottom: "var(--spacing-1, 0.25rem)",
                }}
              >
                Single-Use Recovery Code
              </label>
              <input
                id="recovery-code"
                type="text"
                value={recoveryCode}
                onChange={(e) => setRecoveryCode(e.target.value)}
                placeholder="e.g. A1B2-C3D4-E5F6-G7H8"
                autoFocus
                required
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  backgroundColor: "var(--bg-secondary, #11161d)",
                  border: "1px solid var(--border-default, #30363d)",
                  borderRadius: "var(--radius-md, 6px)",
                  color: "var(--text-primary, #f0f6fc)",
                  fontSize: "var(--font-size-base, 0.875rem)",
                  fontFamily: "var(--font-family-mono)",
                  outline: "none",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                width: "100%",
                padding: "10px 16px",
                backgroundColor: "var(--color-warning, #d29922)",
                color: "var(--text-inverse, #0a0e14)",
                fontWeight: 600,
                fontSize: "var(--font-size-base, 0.875rem)",
                border: "none",
                borderRadius: "var(--radius-md, 6px)",
                cursor: isSubmitting ? "not-allowed" : "pointer",
                opacity: isSubmitting ? 0.7 : 1,
                transition: "opacity 0.2s ease",
              }}
            >
              {isSubmitting ? "Verifying Recovery..." : "Use Single-Use Code"}
            </button>

            <div style={{ textAlign: "center", marginTop: "var(--spacing-4, 1rem)" }}>
              <button
                type="button"
                onClick={() => {
                  setLocalError(null);
                  setError(null);
                  setStep("password");
                  setRecoveryCode("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted, #8b949e)",
                  fontSize: "var(--font-size-xs, 0.75rem)",
                  cursor: "pointer",
                }}
              >
                ← Return to Normal Login
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
