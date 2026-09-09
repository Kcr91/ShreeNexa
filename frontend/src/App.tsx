import React from "react";

import "./index.css";
import "./widgets/builtin";

import { AuthProvider, UserSession } from "./auth/AuthContext";
import { AuthGuard } from "./auth/AuthGuard";
import { NotificationProvider } from "./notifications/NotificationContext";
import { ToastContainer } from "./notifications/ToastContainer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Shell } from "./components/Shell";
import { WebSocketProvider } from "./websocket/WebSocketContext";

export interface AppProps {
  initialUser?: UserSession;
  autoCheckAuth?: boolean;
}

export const App: React.FC<AppProps> = ({ initialUser, autoCheckAuth = true }) => {
  return (
    <ErrorBoundary fallbackMessage="Critical terminal shell failure. Please refresh the browser.">
      <AuthProvider initialUser={initialUser} autoCheck={autoCheckAuth}>
        <NotificationProvider>
          <WebSocketProvider>
            <AuthGuard>
              <Shell />
              <ToastContainer />
            </AuthGuard>
          </WebSocketProvider>
        </NotificationProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
