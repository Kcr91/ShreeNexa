import {
  WidgetCategory,
  WidgetDefinition,
  ValidationResult,
} from "./types";

export class WidgetRegistry {
  private widgets = new Map<string, WidgetDefinition<any>>();

  public register<T = any>(definition: WidgetDefinition<T>): void {
    this.widgets.set(definition.id, definition as WidgetDefinition<any>);
  }

  public get<T = any>(id: string): WidgetDefinition<T> | undefined {
    return this.widgets.get(id) as WidgetDefinition<T> | undefined;
  }

  public getAll(): WidgetDefinition<any>[] {
    return Array.from(this.widgets.values());
  }

  public getByCategory(category: WidgetCategory): WidgetDefinition<any>[] {
    return this.getAll().filter((w) => w.category === category);
  }

  public validateSettings(widgetId: string, settings: Record<string, unknown>): ValidationResult {
    const widget = this.get(widgetId);
    if (!widget) {
      return {
        isValid: false,
        errors: [`Widget definition '${widgetId}' not found in registry.`],
      };
    }

    const errors: string[] = [];

    for (const field of widget.schema.fields) {
      const val = settings[field.name];

      // Check required
      if (field.required && (val === undefined || val === null || val === "")) {
        errors.push(`Field '${field.label}' is required.`);
        continue;
      }

      if (val === undefined || val === null) {
        continue;
      }

      // Check type and range
      if (field.type === "number") {
        const numVal = Number(val);
        if (isNaN(numVal)) {
          errors.push(`Field '${field.label}' must be a valid number.`);
        } else {
          if (field.min !== undefined && numVal < field.min) {
            errors.push(`Field '${field.label}' cannot be less than ${field.min}.`);
          }
          if (field.max !== undefined && numVal > field.max) {
            errors.push(`Field '${field.label}' cannot be greater than ${field.max}.`);
          }
        }
      } else if (field.type === "boolean") {
        if (typeof val !== "boolean") {
          errors.push(`Field '${field.label}' must be a boolean.`);
        }
      } else if (field.type === "select") {
        if (field.options && field.options.length > 0) {
          const validValues = field.options.map((opt) => opt.value);
          if (!validValues.includes(val as string | number)) {
            errors.push(`Field '${field.label}' has an invalid option '${val}'.`);
          }
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }

  public getDefaultSettings(widgetId: string): Record<string, unknown> {
    const widget = this.get(widgetId);
    if (!widget) return {};

    const defaults: Record<string, unknown> = {};
    for (const field of widget.schema.fields) {
      defaults[field.name] = field.default;
    }
    return defaults;
  }
}

export const widgetRegistry = new WidgetRegistry();
