import { WorkspaceLayout } from "./types";
import { validateLayout } from "./storage";

export function exportLayoutToJson(layout: WorkspaceLayout): string {
  return JSON.stringify(layout, null, 2);
}

export function importLayoutFromJson(jsonStr: string): {
  success: boolean;
  layout?: WorkspaceLayout;
  error?: string;
} {
  if (!jsonStr || jsonStr.trim() === "") {
    return { success: false, error: "JSON string cannot be empty." };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonStr);
  } catch (err) {
    return { success: false, error: `Invalid JSON syntax: ${(err as Error).message}` };
  }

  if (!validateLayout(parsed)) {
    return {
      success: false,
      error: "Layout schema validation failed. Required: version, activeTabId, and non-empty tabs array.",
    };
  }

  return {
    success: true,
    layout: parsed,
  };
}
