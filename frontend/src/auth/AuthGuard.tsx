import React, { ReactNode } from "react";
import { useAuth } from "./AuthContext";
import { LoginView } from "./LoginView";

export interface AuthGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children, fallback }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      fallback ?? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            backgroundColor: "var(--bg-primary, #0a0e14)",
            color: "var(--text-muted, #8b949e)",
            fontFamily: "var(--font-family-mono)",
            fontSize: "var(--font-size-sm, 0.8125rem)",
          }}
          data-testid="auth-loading"
        >
          <span>Authenticating terminal session...</span>
        </div>
      )
    );
  }

  if (!user.isAuthenticated) {
    return <LoginView />;
  }

  return <>{children}</>;
};
