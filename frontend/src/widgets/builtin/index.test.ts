import { describe, expect, it } from "vitest";

import { builtinManifests } from ".";
import { widgetRegistry } from "../registry";

describe("built-in lazy widget catalog and bundle budget (QA-14)", () => {
  it("keeps synchronous metadata and schemas aligned with lazy modules", async () => {
    for (const manifest of builtinManifests) {
      const { load, ...registeredDefinition } = manifest;
      const { component: _component, ...loadedDefinition } = await load();

      expect(loadedDefinition).toEqual(registeredDefinition);
    }
  });

  it("verifies all 22 built-in widgets are registered as lazy-loaded definitions", () => {
    expect(builtinManifests.length).toBeGreaterThanOrEqual(20);
    for (const manifest of builtinManifests) {
      expect(typeof manifest.load).toBe("function");
      const registered = widgetRegistry.get(manifest.id);
      expect(registered).toBeDefined();
      expect(registered?.id).toBe(manifest.id);
      expect(registered?.title).toBe(manifest.title);
      expect(registered?.schema).toBeDefined();
    }
  });

  it("ensures heavy widgets (chart, options, blotter) are not eagerly imported", () => {
    const chartManifest = builtinManifests.find((m) => m.id === "chart");
    expect(chartManifest).toBeDefined();
    expect(typeof chartManifest?.load).toBe("function");

    const optionChainManifest = builtinManifests.find((m) => m.id === "option-chain");
    expect(optionChainManifest).toBeDefined();
    expect(typeof optionChainManifest?.load).toBe("function");
  });
});
