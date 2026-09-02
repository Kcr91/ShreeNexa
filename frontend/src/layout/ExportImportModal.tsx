import React, { useState, useEffect } from "react";
import { WorkspaceLayout } from "./types";
import { exportLayoutToJson, importLayoutFromJson } from "./exportImport";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  currentLayout: WorkspaceLayout;
  onImportLayout: (layout: WorkspaceLayout) => void;
}

export const ExportImportModal: React.FC<Props> = ({
  isOpen,
  onClose,
  currentLayout,
  onImportLayout,
}) => {
  const [jsonText, setJsonText] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setJsonText(exportLayoutToJson(currentLayout));
      setErrorMsg(null);
      setCopyStatus(false);
    }
  }, [isOpen, currentLayout]);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonText);
      setCopyStatus(true);
      setTimeout(() => setCopyStatus(false), 2000);
    } catch {
      // Fallback
      setCopyStatus(true);
    }
  };

  const handleImport = () => {
    const res = importLayoutFromJson(jsonText);
    if (!res.success || !res.layout) {
      setErrorMsg(res.error || "Failed to validate imported layout.");
      return;
    }

    onImportLayout(res.layout);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-import-modal-title"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          width: "640px",
          maxHeight: "85vh",
          backgroundColor: "var(--bg-panel)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "var(--spacing-3) var(--spacing-4)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
            <span style={{ fontSize: "1.25rem" }}>💾</span>
            <h2 id="export-import-modal-title" style={{ fontSize: "var(--font-size-md)", fontWeight: 600 }}>
              Export / Import Workspace JSON
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close export import modal"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: "var(--font-size-md)",
            }}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)", flex: 1 }}>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", margin: 0 }}>
            Copy the active workspace JSON configuration or paste a new layout schema to import.
          </p>

          {errorMsg && (
            <div
              role="alert"
              style={{
                backgroundColor: "var(--color-down-bg)",
                border: "1px solid var(--color-down)",
                color: "var(--color-down)",
                padding: "var(--spacing-2)",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-size-xs)",
              }}
            >
              {errorMsg}
            </div>
          )}

          <textarea
            aria-label="Layout JSON Configuration"
            value={jsonText}
            onChange={(e) => {
              setJsonText(e.target.value);
              setErrorMsg(null);
            }}
            rows={12}
            style={{
              width: "100%",
              backgroundColor: "var(--bg-active)",
              color: "var(--text-primary)",
              fontFamily: "var(--font-family-mono)",
              fontSize: "0.75rem",
              padding: "var(--spacing-2)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border-default)",
              resize: "vertical",
              boxSizing: "border-box",
            }}
          />

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              type="button"
              onClick={handleCopy}
              style={{
                padding: "var(--spacing-2) var(--spacing-3)",
                backgroundColor: "var(--bg-surface)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-size-xs)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {copyStatus ? "✓ Copied!" : "📋 Copy JSON"}
            </button>

            <button
              type="button"
              onClick={handleImport}
              style={{
                padding: "var(--spacing-2) var(--spacing-3)",
                backgroundColor: "var(--color-primary)",
                color: "var(--text-inverse)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                fontSize: "var(--font-size-xs)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Import & Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
