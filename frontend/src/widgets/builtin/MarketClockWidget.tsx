import React, { useEffect, useState } from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface MarketClockSettings {
  showSeconds: boolean;
  timeZone: "Asia/Kolkata" | "UTC";
}

export const MarketClockWidget: React.FC<WidgetComponentProps<MarketClockSettings>> = ({
  settings,
}) => {
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const timeZone = settings.timeZone || "Asia/Kolkata";
      const formatted = now.toLocaleTimeString("en-IN", {
        timeZone,
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: settings.showSeconds !== false ? "2-digit" : undefined,
      });
      setTimeStr(`${formatted} (${timeZone === "Asia/Kolkata" ? "IST" : "UTC"})`);
    };

    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [settings.showSeconds, settings.timeZone]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        padding: "var(--spacing-4)",
      }}
    >
      <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)", textTransform: "uppercase" }}>
        Market Session Clock
      </div>
      <div
        style={{
          fontFamily: "var(--font-family-mono)",
          fontSize: "var(--font-size-2xl)",
          fontWeight: "bold",
          color: "var(--text-primary)",
          marginTop: "var(--spacing-2)",
        }}
      >
        {timeStr || "--:--:--"}
      </div>
    </div>
  );
};

export const marketClockDefinition: WidgetDefinition<MarketClockSettings> = {
  id: "market-clock",
  title: "Market Clock",
  description: "Live session clock with timezone selection.",
  category: "system",
  icon: "⏰",
  defaultWidth: 300,
  defaultHeight: 180,
  schema: {
    fields: [
      {
        name: "showSeconds",
        label: "Show Seconds",
        type: "boolean",
        default: true,
      },
      {
        name: "timeZone",
        label: "Time Zone",
        type: "select",
        default: "Asia/Kolkata",
        options: [
          { label: "India Standard Time (IST)", value: "Asia/Kolkata" },
          { label: "Coordinated Universal Time (UTC)", value: "UTC" },
        ],
      },
    ],
  },
  component: MarketClockWidget,
};
