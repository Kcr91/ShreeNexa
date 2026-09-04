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
import { WidgetFrame } from "../widgets/WidgetFrame";
import { widgetRegistry } from "../widgets/registry";

export const Shell: React.FC = () => {
  const [activeRoute, setActiveRoute] = useState<ActiveRoute>("dashboard");

  const renderActiveView = () => {
    switch (activeRoute) {
      case "dashboard":
        return <DashboardView />;
      case "research":
        return (
          <div style={{ overflowY: "auto", flex: 1, height: "100%" }}>
            <ResearchView />
          </div>
        );
      case "screener":
        return (
          <div style={{ overflowY: "auto", flex: 1, height: "100%" }}>
            <ScreenerView />
          </div>
        );
      case "pnl":
        return (
          <div style={{ overflowY: "auto", flex: 1, height: "100%" }}>
            <PnLView />
          </div>
        );
      case "settings":
        return (
          <div style={{ overflowY: "auto", flex: 1, height: "100%" }}>
            <SettingsView />
          </div>
        );
      default: {
        if (widgetRegistry.get(activeRoute)) {
          return (
            <div
              style={{
                height: "100%",
                width: "100%",
                display: "flex",
                flexDirection: "column",
                boxSizing: "border-box",
                padding: "var(--spacing-2)",
              }}
            >
              <WidgetFrame instanceId={`fullscreen-${activeRoute}`} widgetId={activeRoute} />
            </div>
          );
        }
        return <DashboardView />;
      }
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
            height: "100%",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
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
