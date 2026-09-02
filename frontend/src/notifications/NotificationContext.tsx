import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { NotificationItem, NotificationSettings, AlertCategory } from "./types";
import { playAlertChime } from "./audio";

interface NotificationContextType {
  notifications: NotificationItem[];
  activeToasts: NotificationItem[];
  activeRiskBreaches: NotificationItem[];
  unreadCount: number;
  settings: NotificationSettings;
  sendNotification: (item: Omit<NotificationItem, "id" | "timestamp" | "isRead">) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  dismissToast: (id: string) => void;
  dismissRiskBreach: (id: string) => void;
  clearAll: () => void;
  toggleSound: () => void;
  testSound: (category: AlertCategory) => void;
}

const DEFAULT_SETTINGS: NotificationSettings = {
  enableSound: true,
  soundVolume: 0.5,
  enableToastStack: true,
  enableRiskBanners: true,
  toastDurationMs: 4000,
};

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider: React.FC<{
  children: ReactNode;
  initialNotifications?: NotificationItem[];
  initialSettings?: Partial<NotificationSettings>;
}> = ({ children, initialNotifications = [], initialSettings = {} }) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>(initialNotifications);
  const [activeToasts, setActiveToasts] = useState<NotificationItem[]>([]);
  const [activeRiskBreaches, setActiveRiskBreaches] = useState<NotificationItem[]>([]);
  const [settings, setSettings] = useState<NotificationSettings>({
    ...DEFAULT_SETTINGS,
    ...initialSettings,
  });

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  const sendNotification = (item: Omit<NotificationItem, "id" | "timestamp" | "isRead">) => {
    const newItem: NotificationItem = {
      ...item,
      id: `notif-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      timestamp: Date.now(),
      isRead: false,
    };

    setNotifications((prev) => [newItem, ...prev]);

    // Show toast if enabled
    if (settings.enableToastStack) {
      setActiveToasts((prev) => [...prev, newItem]);
    }

    // Add risk breach banner if severity is RISK_BREACH
    if (newItem.severity === "RISK_BREACH" && settings.enableRiskBanners) {
      setActiveRiskBreaches((prev) => [...prev, newItem]);
    }

    // Play chime if sound enabled
    if (settings.enableSound) {
      playAlertChime(newItem.category, settings.soundVolume);
    }
  };

  const markAsRead = (id: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, isRead: true } : n)));
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  const dismissToast = (id: string) => {
    setActiveToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const dismissRiskBreach = (id: string) => {
    setActiveRiskBreaches((prev) => prev.filter((b) => b.id !== id));
  };

  const clearAll = () => {
    setNotifications([]);
    setActiveToasts([]);
    setActiveRiskBreaches([]);
  };

  const toggleSound = () => {
    setSettings((prev) => ({ ...prev, enableSound: !prev.enableSound }));
  };

  const testSound = (category: AlertCategory) => {
    playAlertChime(category, settings.soundVolume);
  };

  // Auto-dismiss toast timer
  useEffect(() => {
    if (activeToasts.length === 0) return;

    const timer = setTimeout(() => {
      setActiveToasts((prev) => prev.slice(1));
    }, settings.toastDurationMs);

    return () => clearTimeout(timer);
  }, [activeToasts, settings.toastDurationMs]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        activeToasts,
        activeRiskBreaches,
        unreadCount,
        settings,
        sendNotification,
        markAsRead,
        markAllAsRead,
        dismissToast,
        dismissRiskBreach,
        clearAll,
        toggleSound,
        testSound,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within a NotificationProvider");
  }
  return context;
};
