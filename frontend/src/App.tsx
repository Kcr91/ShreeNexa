import React from "react";
import { AuthProvider } from "./auth/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Shell } from "./components/Shell";

export const App: React.FC = () => {
  return (
    <ErrorBoundary fallbackMessage="Critical terminal shell failure. Please refresh the browser.">
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ErrorBoundary>
  );
};

export default App;
