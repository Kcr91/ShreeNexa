import { describe, expect, it } from "vitest";
import { PREBUILT_TEMPLATES } from "./templates";
import { validateLayout } from "./storage";

describe("Pre-Built Workspace Templates", () => {
  it("contains valid Day Trader, Options Desk, and Quant Lab templates", () => {
    expect(PREBUILT_TEMPLATES).toHaveLength(3);

    const ids = PREBUILT_TEMPLATES.map((t) => t.id);
    expect(ids).toContain("day-trader");
    expect(ids).toContain("options-desk");
    expect(ids).toContain("quant-lab");
  });

  it("ensures every prebuilt template conforms to WorkspaceLayout schema", () => {
    for (const tmpl of PREBUILT_TEMPLATES) {
      const isValid = validateLayout(tmpl.layout);
      expect(isValid).toBe(true);
      expect(tmpl.layout.tabs.length).toBeGreaterThan(0);
      expect(tmpl.layout.tabs[0].widgets.length).toBeGreaterThan(0);
    }
  });
});
