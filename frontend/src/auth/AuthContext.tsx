import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { apiClient, ApiError } from "../api/client";

export interface UserSession {
  username: string;
  role: "developer" | "trader" | "admin";
  isAuthenticated: boolean;
  dhanClientId: string;
  csrfToken?: string;
  expiresAt?: string;
}

export interface AuthContextType {
  user: UserSession;
  isLoading: boolean;
  error: string | null;
  setError: (error: string | null) => void;
  initiateLogin: (password: string) => Promise<{
    requiresTotp: boolean;
    challengeToken?: string;
    message: string;
  }>;
  completeTotp: (challengeToken: string, totpCode: string) => Promise<boolean>;
  completeRecovery: (password: string, recoveryCode: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
}

export const unauthenticatedUser: UserSession = {
  username: "",
  role: "trader",
  isAuthenticated: false,
  dhanClientId: "",
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
  children: ReactNode;
  initialUser?: UserSession;
  autoCheck?: boolean;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({
  children,
  initialUser,
  autoCheck = true,
}) => {
  const [user, setUser] = useState<UserSession>(initialUser ?? unauthenticatedUser);
  const [isLoading, setIsLoading] = useState<boolean>(initialUser ? false : autoCheck);
  const [error, setError] = useState<string | null>(null);

  const checkSession = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const me = await apiClient.getCurrentUser();
      if (me.authenticated) {
        setUser({
          username: me.username,
          role: "trader",
          isAuthenticated: true,
          dhanClientId: "",
          csrfToken: me.csrf_token,
          expiresAt: me.expires_at,
        });
        apiClient.setCsrfToken(me.csrf_token);
      } else {
        setUser(unauthenticatedUser);
        apiClient.setCsrfToken(null);
      }
    } catch {
      setUser(unauthenticatedUser);
      apiClient.setCsrfToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!initialUser && autoCheck) {
      void checkSession();
    }
  }, [initialUser, autoCheck, checkSession]);

  const initiateLogin = async (
    password: string,
  ): Promise<{ requiresTotp: boolean; challengeToken?: string; message: string }> => {
    setError(null);
    try {
      const res = await apiClient.login(password);
      return {
        requiresTotp: res.requires_totp,
        challengeToken: res.challenge_token ?? undefined,
        message: res.message,
      };
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  };

  const completeTotp = async (
    challengeToken: string,
    totpCode: string,
  ): Promise<boolean> => {
    setError(null);
    try {
      const res = await apiClient.verifyTotp(challengeToken, totpCode);
      if (res.authenticated) {
        setUser({
          username: res.username,
          role: "trader",
          isAuthenticated: true,
          dhanClientId: "",
          csrfToken: res.csrf_token,
          expiresAt: res.expires_at,
        });
        apiClient.setCsrfToken(res.csrf_token);
        return true;
      }
      return false;
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Verification failed";
      setError(message);
      throw err;
    }
  };

  const completeRecovery = async (
    password: string,
    recoveryCode: string,
  ): Promise<boolean> => {
    setError(null);
    try {
      const res = await apiClient.loginWithRecovery(password, recoveryCode);
      if (res.authenticated) {
        setUser({
          username: res.username,
          role: "trader",
          isAuthenticated: true,
          dhanClientId: "",
          csrfToken: res.csrf_token,
          expiresAt: res.expires_at,
        });
        apiClient.setCsrfToken(res.csrf_token);
        return true;
      }
      return false;
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Recovery login failed";
      setError(message);
      throw err;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient.logout();
    } finally {
      setUser(unauthenticatedUser);
      apiClient.setCsrfToken(null);
      setError(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        error,
        setError,
        initiateLogin,
        completeTotp,
        completeRecovery,
        logout,
        checkSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
