import React from "react";
import { WidgetComponentProps, WidgetDefinition } from "../types";

export interface FixtureTestSettings {
  customMessage: string;
  samplingRate: number;
}

export const FixtureTestWidget: React.FC<WidgetComponentProps<FixtureTestSettings>> = ({
  settings,
}) => {
  return (
    <div style={{ height: "100%", padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
      <div style={{ color: "var(--color-primary)", fontWeight: "bold", fontSize: "var(--font-size-sm)" }}>
        Fixture Test Widget
      </div>
      <div style={{ fontSize: "var(--font-size-sm)", color: "var(--text-secondary)" }}>
        Message: {settings.customMessage || "Default Test Message"}
      </div>
      <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", fontFamily: "var(--font-family-mono)" }}>
        Sampling Rate: {settings.samplingRate} Hz
      </div>
    </div>
  );
};

export const fixtureTestDefinition: WidgetDefinition<FixtureTestSettings> = {
  id: "fixture-test",
  title: "Fixture Dynamic Test Widget",
  description: "Test fixture verifying dynamic palette registration.",
  category: "custom",
  icon: "🧩",
  defaultWidth: 280,
  defaultHeight: 160,
  schema: {
    fields: [
      {
        name: "customMessage",
        label: "Custom Message",
        type: "string",
        default: "Hello ShreeNexa",
        required: true,
      },
      {
        name: "samplingRate",
        label: "Sampling Rate",
        type: "number",
        default: 10,
        min: 1,
        max: 100,
      },
    ],
  },
  component: FixtureTestWidget,
};
