import React, { createContext, useContext, useState, ReactNode } from "react";

export interface UserSession {
  username: string;
  role: "developer" | "trader" | "admin";
  isAuthenticated: boolean;
  dhanClientId: string;
}

interface AuthContextType {
  user: UserSession;
  login: (username: string) => void;
  logout: () => void;
}

const defaultUser: UserSession = {
  username: "dev_trader",
  role: "developer",
  isAuthenticated: true,
  dhanClientId: "DHAN_LOCAL_DEV",
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession>(defaultUser);

  const login = (username: string) => {
    setUser({
      username,
      role: "developer",
      isAuthenticated: true,
      dhanClientId: "DHAN_LOCAL_DEV",
    });
  };

  const logout = () => {
    setUser({
      username: "anonymous",
      role: "trader",
      isAuthenticated: false,
      dhanClientId: "",
    });
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
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
