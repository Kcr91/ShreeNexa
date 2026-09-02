import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useWorkspaceHotkeys } from "./hotkeys";

describe("Workspace Keyboard Hotkeys Hook", () => {
  it("switches active tab when Alt+1 or Alt+2 is pressed", () => {
    const onSelectTab = vi.fn();
    const tabIds = ["tab-1", "tab-2", "tab-3"];

    renderHook(() =>
      useWorkspaceHotkeys({
        tabIds,
        onSelectTab,
      })
    );

    // Trigger Alt+1
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "1", altKey: true }));
    expect(onSelectTab).toHaveBeenCalledWith("tab-1");

    // Trigger Alt+2
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "2", altKey: true }));
    expect(onSelectTab).toHaveBeenCalledWith("tab-2");
  });

  it("triggers modal actions on Alt+T, Alt+W, and Alt+E", () => {
    const onSelectTab = vi.fn();
    const onOpenTemplates = vi.fn();
    const onOpenPalette = vi.fn();
    const onOpenExportImport = vi.fn();

    renderHook(() =>
      useWorkspaceHotkeys({
        tabIds: ["tab-1"],
        onSelectTab,
        onOpenTemplates,
        onOpenPalette,
        onOpenExportImport,
      })
    );

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "t", altKey: true }));
    expect(onOpenTemplates).toHaveBeenCalled();

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "w", altKey: true }));
    expect(onOpenPalette).toHaveBeenCalled();

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "e", altKey: true }));
    expect(onOpenExportImport).toHaveBeenCalled();
  });
});
