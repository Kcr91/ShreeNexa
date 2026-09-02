import { render, screen, act } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LiveFeedStatusWidget, liveFeedStatusDefinition } from "./LiveFeedStatusWidget";
import { defaultWebSocketClient } from "../../websocket/client";
import { widgetRegistry } from "../registry";
import "./index";

describe("LiveFeedStatusWidget Component", () => {
  it("renders live feed status badge and telemetry header", () => {
    render(
      <LiveFeedStatusWidget
        instanceId="feed-status-1"
        settings={{
          showTickStream: true,
          maxStreamHistory: 10,
        }}
      />
    );

    expect(screen.getByTestId("feed-status-badge")).toBeInTheDocument();
    expect(screen.getByTestId("feed-latency-value")).toBeInTheDocument();
    expect(screen.getByText(/Channels:/i)).toBeInTheDocument();
  });

  it("updates live tick stream table when new tick arrives", () => {
    render(
      <LiveFeedStatusWidget
        instanceId="feed-status-1"
        settings={{
          showTickStream: true,
          maxStreamHistory: 10,
        }}
      />
    );

    act(() => {
      defaultWebSocketClient.dispatchTick({
        symbol: "TCS",
        ltp: 4200.0,
        change: 25.0,
        changePct: 0.6,
        volume: 3500,
        timestamp: Date.now(),
      });
    });

    expect(screen.getByTestId("stream-tick-TCS")).toBeInTheDocument();
    expect(screen.getByText("TCS")).toBeInTheDocument();
  });

  it("is registered in widget registry under analytics category", () => {
    expect(widgetRegistry.get("live-feed-status")).toBeDefined();
    expect(widgetRegistry.get("live-feed-status")?.title).toBe("Live Feed & Telemetry");
    expect(liveFeedStatusDefinition.category).toBe("analytics");
  });
});
