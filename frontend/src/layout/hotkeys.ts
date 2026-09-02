import { useEffect } from "react";

export interface WorkspaceHotkeysOptions {
  tabIds: string[];
  onSelectTab: (tabId: string) => void;
  onOpenTemplates?: () => void;
  onOpenPalette?: () => void;
  onOpenExportImport?: () => void;
}

export function useWorkspaceHotkeys({
  tabIds,
  onSelectTab,
  onOpenTemplates,
  onOpenPalette,
  onOpenExportImport,
}: WorkspaceHotkeysOptions): void {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Avoid hotkey interference if typing in input/textarea/select
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT")
      ) {
        return;
      }

      if (e.altKey) {
        // Alt + 1..9 -> Switch tab index
        const digit = parseInt(e.key, 10);
        if (!isNaN(digit) && digit >= 1 && digit <= 9) {
          const tabIndex = digit - 1;
          if (tabIndex < tabIds.length) {
            e.preventDefault();
            onSelectTab(tabIds[tabIndex]);
            return;
          }
        }

        // Alt + T -> Templates
        if (e.key === "t" || e.key === "T") {
          e.preventDefault();
          onOpenTemplates?.();
          return;
        }

        // Alt + W -> Widget Palette
        if (e.key === "w" || e.key === "W") {
          e.preventDefault();
          onOpenPalette?.();
          return;
        }

        // Alt + E -> Export/Import
        if (e.key === "e" || e.key === "E") {
          e.preventDefault();
          onOpenExportImport?.();
          return;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [tabIds, onSelectTab, onOpenTemplates, onOpenPalette, onOpenExportImport]);
}
