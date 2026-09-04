import React from "react";

import "./index.css";
import "./widgets/builtin";

import { AuthProvider, UserSession } from "./auth/AuthContext";
import { AuthGuard } from "./auth/AuthGuard";
import { NotificationProvider } from "./notifications/NotificationContext";
import { ToastContainer } from "./notifications/ToastContainer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Shell } from "./components/Shell";

export interface AppProps {
  initialUser?: UserSession;
  autoCheckAuth?: boolean;
}

export const App: React.FC<AppProps> = ({ initialUser, autoCheckAuth = true }) => {
  return (
    <ErrorBoundary fallbackMessage="Critical terminal shell failure. Please refresh the browser.">
      <AuthProvider initialUser={initialUser} autoCheck={autoCheckAuth}>
        <NotificationProvider>
          <AuthGuard>
            <Shell />
            <ToastContainer />
          </AuthGuard>
        </NotificationProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
