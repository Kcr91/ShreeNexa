import React from "react";

import "./index.css";
import "./widgets/builtin";

import { AuthProvider } from "./auth/AuthContext";
import { NotificationProvider } from "./notifications/NotificationContext";
import { ToastContainer } from "./notifications/ToastContainer";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Shell } from "./components/Shell";

export const App: React.FC = () => {
  return (
    <ErrorBoundary fallbackMessage="Critical terminal shell failure. Please refresh the browser.">
      <AuthProvider>
        <NotificationProvider>
          <Shell />
          <ToastContainer />
        </NotificationProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
