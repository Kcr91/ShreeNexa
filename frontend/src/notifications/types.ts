export type AlertSeverity = "INFO" | "SUCCESS" | "WARNING" | "CRITICAL" | "RISK_BREACH";

export type AlertCategory =
  | "ORDER_FILL"
  | "ORDER_REJECT"
  | "MARGIN_CALL"
  | "RISK_BREACH"
  | "PRICE_ALERT"
  | "SYSTEM";

export interface NotificationItem {
  id: string;
  timestamp: number;
  title: string;
  message: string;
  severity: AlertSeverity;
  category: AlertCategory;
  isRead: boolean;
  actionUrl?: string;
}

export interface NotificationSettings {
  enableSound: boolean;
  soundVolume: number; // 0.0 to 1.0
  enableToastStack: boolean;
  enableRiskBanners: boolean;
  toastDurationMs: number;
}

export interface AlertsLogWidgetSettings {
  defaultFilter: "ALL" | "CRITICAL" | "ORDERS" | "RISK";
  showSoundToggle: boolean;
}
