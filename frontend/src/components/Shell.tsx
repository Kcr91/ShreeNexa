import React, { useState } from "react";
import { Header } from "./Header";
import { Navigation, ActiveRoute } from "./Navigation";
import { StatusFooter } from "./StatusFooter";
import { ErrorBoundary } from "./ErrorBoundary";
import { DashboardView } from "../views/DashboardView";
import { ResearchView } from "../views/ResearchView";
import { ScreenerView } from "../views/ScreenerView";
import { PnLView } from "../views/PnLView";
import { SettingsView } from "../views/SettingsView";

export const Shell: React.FC = () => {
  const [activeRoute, setActiveRoute] = useState<ActiveRoute>("dashboard");

  const renderActiveView = () => {
    switch (activeRoute) {
      case "dashboard":
        return <DashboardView />;
      case "research":
        return <ResearchView />;
      case "screener":
        return <ScreenerView />;
      case "pnl":
        return <PnLView />;
      case "settings":
        return <SettingsView />;
      default:
        return <DashboardView />;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      <Header />
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Navigation activeRoute={activeRoute} onRouteChange={setActiveRoute} />
        <main
          role="main"
          style={{
            flex: 1,
            overflowY: "auto",
            backgroundColor: "var(--bg-primary)",
          }}
        >
          <ErrorBoundary>
            {renderActiveView()}
          </ErrorBoundary>
        </main>
      </div>
      <StatusFooter />
    </div>
  );
};
