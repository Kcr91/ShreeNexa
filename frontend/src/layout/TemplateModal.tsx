import React from "react";
import { WorkspaceLayout } from "./types";
import { PREBUILT_TEMPLATES, WorkspaceTemplate } from "./templates";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onApplyTemplate: (layout: WorkspaceLayout) => void;
}

export const TemplateModal: React.FC<Props> = ({ isOpen, onClose, onApplyTemplate }) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="template-modal-title"
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
          width: "580px",
          maxHeight: "80vh",
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
            <span style={{ fontSize: "1.25rem" }}>📋</span>
            <h2 id="template-modal-title" style={{ fontSize: "var(--font-size-md)", fontWeight: 600 }}>
              Workspace Templates
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close template modal"
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

        {/* Template List */}
        <div style={{ padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)", overflowY: "auto" }}>
          {PREBUILT_TEMPLATES.map((tmpl: WorkspaceTemplate) => (
            <div
              key={tmpl.id}
              data-testid={`template-card-${tmpl.id}`}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-3)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "var(--spacing-3)",
              }}
            >
              <div style={{ display: "flex", gap: "var(--spacing-3)", alignItems: "center" }}>
                <span style={{ fontSize: "1.75rem" }}>{tmpl.icon}</span>
                <div>
                  <h3 style={{ fontSize: "var(--font-size-sm)", fontWeight: 600, margin: 0 }}>{tmpl.name}</h3>
                  <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
                    {tmpl.description}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  onApplyTemplate(tmpl.layout);
                  onClose();
                }}
                style={{
                  padding: "var(--spacing-2) var(--spacing-3)",
                  backgroundColor: "var(--color-primary)",
                  color: "var(--text-inverse)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "var(--font-size-xs)",
                  fontWeight: 600,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                Apply Layout
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
