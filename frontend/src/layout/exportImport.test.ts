import { describe, expect, it } from "vitest";
import { exportLayoutToJson, importLayoutFromJson } from "./exportImport";
import { DEFAULT_LAYOUT } from "./storage";

describe("Layout Export and Import JSON Validation", () => {
  it("exports valid layout to pretty-printed JSON string", () => {
    const jsonStr = exportLayoutToJson(DEFAULT_LAYOUT);
    expect(jsonStr).toContain('"version": 1');
    expect(jsonStr).toContain('"activeTabId":');
    expect(jsonStr).toContain('"tabs":');
  });

  it("successfully imports valid layout JSON string", () => {
    const jsonStr = JSON.stringify(DEFAULT_LAYOUT);
    const result = importLayoutFromJson(jsonStr);

    expect(result.success).toBe(true);
    expect(result.layout).toBeDefined();
    expect(result.layout?.version).toBe(1);
    expect(result.layout?.tabs).toHaveLength(DEFAULT_LAYOUT.tabs.length);
  });

  it("fails when importing empty or malformed JSON syntax", () => {
    const emptyResult = importLayoutFromJson("");
    expect(emptyResult.success).toBe(false);
    expect(emptyResult.error).toContain("cannot be empty");

    const syntaxResult = importLayoutFromJson("{ not a valid json }");
    expect(syntaxResult.success).toBe(false);
    expect(syntaxResult.error).toContain("Invalid JSON syntax");
  });

  it("fails when importing schema-invalid JSON structure", () => {
    const invalidSchema = JSON.stringify({ version: 2, tabs: "not-an-array" });
    const result = importLayoutFromJson(invalidSchema);

    expect(result.success).toBe(false);
    expect(result.error).toContain("schema validation failed");
  });
});
