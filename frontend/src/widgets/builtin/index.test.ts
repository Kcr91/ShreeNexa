import { describe, expect, it } from "vitest";

import { builtinManifests } from ".";

describe("built-in lazy widget catalog", () => {
  it("keeps synchronous metadata and schemas aligned with lazy modules", async () => {
    for (const manifest of builtinManifests) {
      const { load, ...registeredDefinition } = manifest;
      const { component: _component, ...loadedDefinition } = await load();

      expect(loadedDefinition).toEqual(registeredDefinition);
    }
  });
});
