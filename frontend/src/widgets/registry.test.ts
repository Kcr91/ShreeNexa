import { describe, expect, it } from "vitest";
import { WidgetRegistry } from "./registry";
import { WidgetDefinition } from "./types";

describe("WidgetRegistry and Settings Schema Validation", () => {
  it("registers and retrieves widget definitions dynamically", () => {
    const registry = new WidgetRegistry();

    const testDef: WidgetDefinition = {
      id: "dynamic-test",
      title: "Dynamic Test Widget",
      description: "Dynamically added widget",
      category: "custom",
      icon: "🧪",
      defaultWidth: 200,
      defaultHeight: 150,
      schema: {
        fields: [
          {
            name: "paramA",
            label: "Parameter A",
            type: "number",
            default: 10,
            min: 5,
            max: 50,
            required: true,
          },
          {
            name: "mode",
            label: "Mode",
            type: "select",
            default: "fast",
            options: [
              { label: "Fast", value: "fast" },
              { label: "Slow", value: "slow" },
            ],
          },
        ],
      },
      component: () => null,
    };

    registry.register(testDef);

    expect(registry.get("dynamic-test")).toBeDefined();
    expect(registry.get("dynamic-test")?.title).toBe("Dynamic Test Widget");
    expect(registry.getByCategory("custom")).toHaveLength(1);
    expect(registry.getAll()).toHaveLength(1);
  });

  it("validates valid settings against schema", () => {
    const registry = new WidgetRegistry();
    const testDef: WidgetDefinition = {
      id: "test-valid",
      title: "Test",
      description: "Test",
      category: "custom",
      icon: "🔧",
      defaultWidth: 100,
      defaultHeight: 100,
      schema: {
        fields: [
          { name: "count", label: "Count", type: "number", default: 5, min: 1, max: 10 },
          { name: "tag", label: "Tag", type: "string", default: "alpha", required: true },
        ],
      },
      component: () => null,
    };
    registry.register(testDef);

    const validRes = registry.validateSettings("test-valid", { count: 8, tag: "beta" });
    expect(validRes.isValid).toBe(true);
    expect(validRes.errors).toHaveLength(0);
  });

  it("rejects invalid settings with explicit error messages", () => {
    const registry = new WidgetRegistry();
    const testDef: WidgetDefinition = {
      id: "test-invalid",
      title: "Test",
      description: "Test",
      category: "custom",
      icon: "🔧",
      defaultWidth: 100,
      defaultHeight: 100,
      schema: {
        fields: [
          { name: "score", label: "Score", type: "number", default: 50, min: 0, max: 100 },
          { name: "requiredName", label: "Required Name", type: "string", default: "", required: true },
          {
            name: "choice",
            label: "Choice",
            type: "select",
            default: "opt1",
            options: [{ label: "Opt 1", value: "opt1" }, { label: "Opt 2", value: "opt2" }],
          },
        ],
      },
      component: () => null,
    };
    registry.register(testDef);

    // 1. Missing required field, out of range number, invalid select option
    const res = registry.validateSettings("test-invalid", {
      score: 150, // exceeds max 100
      requiredName: "", // missing required
      choice: "invalid_opt", // not in options
    });

    expect(res.isValid).toBe(false);
    expect(res.errors).toHaveLength(3);
    expect(res.errors[0]).toContain("cannot be greater than 100");
    expect(res.errors[1]).toContain("is required");
    expect(res.errors[2]).toContain("has an invalid option");
  });
});
