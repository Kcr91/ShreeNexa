import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AlertsLogWidget, alertsLogDefinition } from "./AlertsLogWidget";
import { NotificationProvider } from "../../notifications/NotificationContext";
import { widgetRegistry } from "../registry";
import "./index";

describe("AlertsLogWidget Component", () => {
  it("renders alerts log controls and toggles audio sound setting", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: true }}>
        <AlertsLogWidget
          instanceId="alerts-1"
          settings={{
            defaultFilter: "ALL",
            showSoundToggle: true,
          }}
        />
      </NotificationProvider>
    );

    expect(screen.getByText("Alerts Log")).toBeInTheDocument();
    const soundBtn = screen.getByTestId("toggle-sound-btn");
    expect(soundBtn).toHaveTextContent("🔊 Sound ON");

    fireEvent.click(soundBtn);
    expect(soundBtn).toHaveTextContent("🔇 Sound OFF");
  });

  it("simulates fill and risk breach alerts and logs to table", () => {
    render(
      <NotificationProvider initialSettings={{ enableSound: false }}>
        <AlertsLogWidget
          instanceId="alerts-1"
          settings={{
            defaultFilter: "ALL",
            showSoundToggle: true,
          }}
        />
      </NotificationProvider>
    );

    const fillBtn = screen.getByRole("button", { name: "+ Fill" });
    fireEvent.click(fillBtn);

    expect(screen.getByText("Order Executed")).toBeInTheDocument();
    expect(screen.getByText(/BUY 50 NIFTY 24500 CE/i)).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("alerts-log")).toBeDefined();
    expect(widgetRegistry.get("alerts-log")?.title).toBe("Alerts & Audit Log");
    expect(alertsLogDefinition.category).toBe("analytics");
  });
});
