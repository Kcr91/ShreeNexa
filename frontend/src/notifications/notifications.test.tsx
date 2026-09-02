import { renderHook, act } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { NotificationProvider, useNotifications } from "./NotificationContext";

describe("Notification Context and Alert Dispatcher", () => {
  it("dispatches notifications, creates toasts, and tracks unread count", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <NotificationProvider initialSettings={{ enableSound: false }}>
        {children}
      </NotificationProvider>
    );

    const { result } = renderHook(() => useNotifications(), { wrapper });

    expect(result.current.notifications).toHaveLength(0);
    expect(result.current.unreadCount).toBe(0);

    act(() => {
      result.current.sendNotification({
        title: "Order Executed",
        message: "BUY 25 RELIANCE filled",
        severity: "SUCCESS",
        category: "ORDER_FILL",
      });
    });

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.unreadCount).toBe(1);
    expect(result.current.activeToasts).toHaveLength(1);

    // Mark as read
    const notifId = result.current.notifications[0].id;
    act(() => {
      result.current.markAsRead(notifId);
    });

    expect(result.current.unreadCount).toBe(0);
  });

  it("handles RISK_BREACH severity and creates persistent risk banner", () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <NotificationProvider initialSettings={{ enableSound: false }}>
        {children}
      </NotificationProvider>
    );

    const { result } = renderHook(() => useNotifications(), { wrapper });

    act(() => {
      result.current.sendNotification({
        title: "Daily Drawdown Breach",
        message: "Hit maximum account loss limit",
        severity: "RISK_BREACH",
        category: "RISK_BREACH",
      });
    });

    expect(result.current.activeRiskBreaches).toHaveLength(1);

    const breachId = result.current.activeRiskBreaches[0].id;
    act(() => {
      result.current.dismissRiskBreach(breachId);
    });

    expect(result.current.activeRiskBreaches).toHaveLength(0);
  });
});
