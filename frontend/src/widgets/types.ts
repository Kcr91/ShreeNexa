import React from "react";

export type WidgetCategory = "chart" | "order" | "analytics" | "watchlist" | "system" | "custom";

export type WidgetSettingsFieldType = "string" | "number" | "boolean" | "select";

export interface SelectOption {
  label: string;
  value: string | number;
}

export interface WidgetSettingsField {
  name: string;
  label: string;
  type: WidgetSettingsFieldType;
  default: unknown;
  description?: string;
  min?: number;
  max?: number;
  options?: SelectOption[];
  required?: boolean;
}

export interface WidgetSettingsSchema {
  fields: WidgetSettingsField[];
}

export interface WidgetComponentProps<TSettings = any> {
  instanceId: string;
  settings: TSettings;
  onUpdateSettings?: (newSettings: Partial<TSettings>) => void;
}

export interface WidgetDefinition<TSettings = any> {
  id: string;
  title: string;
  description: string;
  category: WidgetCategory;
  icon: string;
  defaultWidth: number;
  defaultHeight: number;
  minWidth?: number;
  minHeight?: number;
  schema: WidgetSettingsSchema;
  component: React.ComponentType<WidgetComponentProps<TSettings>> | React.LazyExoticComponent<React.ComponentType<WidgetComponentProps<TSettings>>>;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}
