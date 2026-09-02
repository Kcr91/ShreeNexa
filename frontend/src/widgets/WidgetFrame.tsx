import React, { Suspense, useState } from "react";
import { widgetRegistry } from "./registry";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { ErrorBoundary } from "../components/ErrorBoundary";

interface Props {
  instanceId: string;
  widgetId: string;
  settings?: Record<string, unknown>;
  onClose?: (instanceId: string) => void;
  onUpdateSettings?: (instanceId: string, newSettings: Record<string, unknown>) => void;
}

export const WidgetFrame: React.FC<Props> = ({
  instanceId,
  widgetId,
  settings: initialSettings,
  onClose,
  onUpdateSettings,
}) => {
  const widgetDef = widgetRegistry.get(widgetId);
  const [currentSettings, setCurrentSettings] = useState<Record<string, unknown>>(
    initialSettings || widgetRegistry.getDefaultSettings(widgetId)
  );
  const [isEditingSettings, setIsEditingSettings] = useState<boolean>(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  if (!widgetDef) {
    return (
      <div
        role="alert"
        style={{
          padding: "var(--spacing-4)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--color-down)",
          borderRadius: "var(--radius-md)",
          color: "var(--color-down)",
          fontSize: "var(--font-size-sm)",
        }}
      >
        Widget not found: <strong>{widgetId}</strong>
      </div>
    );
  }

  const handleSaveSettings = (draft: Record<string, unknown>) => {
    const res = widgetRegistry.validateSettings(widgetId, draft);
    if (!res.isValid) {
      setValidationErrors(res.errors);
      return;
    }
    setValidationErrors([]);
    setCurrentSettings(draft);
    setIsEditingSettings(false);
    if (onUpdateSettings) {
      onUpdateSettings(instanceId, draft);
    }
  };

  const Component = widgetDef.component;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--bg-secondary)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        height: "100%",
        width: "100%",
      }}
    >
      {/* Widget Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "var(--spacing-2) var(--spacing-3)",
          backgroundColor: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-2)" }}>
          <span>{widgetDef.icon}</span>
          <span style={{ fontSize: "var(--font-size-sm)", fontWeight: 600 }}>{widgetDef.title}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-1)" }}>
          <button
            type="button"
            aria-label="Widget Settings"
            onClick={() => setIsEditingSettings(!isEditingSettings)}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              fontSize: "var(--font-size-sm)",
              color: isEditingSettings ? "var(--color-primary)" : "var(--text-muted)",
              padding: "2px 6px",
            }}
          >
            ⚙️
          </button>
          {onClose && (
            <button
              type="button"
              aria-label="Close Widget"
              onClick={() => onClose(instanceId)}
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                fontSize: "var(--font-size-sm)",
                color: "var(--text-muted)",
                padding: "2px 6px",
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Settings Form Overlay or Content View */}
      <div style={{ flex: 1, position: "relative", overflow: "auto" }}>
        {isEditingSettings ? (
          <SettingsEditor
            fields={widgetDef.schema.fields}
            initialValues={currentSettings}
            errors={validationErrors}
            onSave={handleSaveSettings}
            onCancel={() => {
              setIsEditingSettings(false);
              setValidationErrors([]);
            }}
          />
        ) : (
          <ErrorBoundary fallbackMessage="Error rendering widget content.">
            <Suspense fallback={<LoadingSkeleton count={3} />}>
              <Component
                instanceId={instanceId}
                settings={currentSettings}
                onUpdateSettings={(newPartial) => {
                  const updated = { ...currentSettings, ...newPartial };
                  setCurrentSettings(updated);
                  if (onUpdateSettings) onUpdateSettings(instanceId, updated);
                }}
              />
            </Suspense>
          </ErrorBoundary>
        )}
      </div>
    </div>
  );
};

interface SettingsEditorProps {
  fields: { name: string; label: string; type: string; options?: { label: string; value: string | number }[] }[];
  initialValues: Record<string, unknown>;
  errors: string[];
  onSave: (values: Record<string, unknown>) => void;
  onCancel: () => void;
}

const SettingsEditor: React.FC<SettingsEditorProps> = ({
  fields,
  initialValues,
  errors,
  onSave,
  onCancel,
}) => {
  const [draft, setDraft] = useState<Record<string, unknown>>({ ...initialValues });

  const handleChange = (name: string, value: unknown) => {
    setDraft((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div style={{ padding: "var(--spacing-4)", display: "flex", flexDirection: "column", gap: "var(--spacing-3)" }}>
      <div style={{ fontWeight: 600, fontSize: "var(--font-size-sm)" }}>Widget Configuration</div>

      {errors.length > 0 && (
        <div
          role="alert"
          style={{
            padding: "var(--spacing-2)",
            backgroundColor: "var(--color-down-bg)",
            color: "var(--color-down)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--font-size-xs)",
          }}
        >
          {errors.map((e, idx) => (
            <div key={idx}>• {e}</div>
          ))}
        </div>
      )}

      {fields.map((f) => (
        <div key={f.name} style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-1)" }}>
          <label htmlFor={`setting-${f.name}`} style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>{f.label}</label>
          {f.type === "boolean" ? (
            <input
              id={`setting-${f.name}`}
              type="checkbox"
              checked={Boolean(draft[f.name])}
              onChange={(e) => handleChange(f.name, e.target.checked)}
            />
          ) : f.type === "select" && f.options ? (
            <select
              id={`setting-${f.name}`}
              value={String(draft[f.name] || "")}
              onChange={(e) => handleChange(f.name, e.target.value)}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-1)",
                color: "var(--text-primary)",
              }}
            >
              {f.options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ) : (
            <input
              id={`setting-${f.name}`}
              type={f.type === "number" ? "number" : "text"}
              value={String(draft[f.name] ?? "")}
              onChange={(e) => handleChange(f.name, f.type === "number" ? Number(e.target.value) : e.target.value)}
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-1) var(--spacing-2)",
                color: "var(--text-primary)",
              }}
            />
          )}
        </div>
      ))}

      <div style={{ display: "flex", gap: "var(--spacing-2)", marginTop: "var(--spacing-2)" }}>
        <button
          type="button"
          onClick={() => onSave(draft)}
          style={{
            padding: "var(--spacing-1) var(--spacing-3)",
            backgroundColor: "var(--color-primary)",
            color: "var(--text-inverse)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "var(--font-size-xs)",
          }}
        >
          Save Settings
        </button>
        <button
          type="button"
          onClick={onCancel}
          style={{
            padding: "var(--spacing-1) var(--spacing-3)",
            backgroundColor: "transparent",
            color: "var(--text-muted)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            fontSize: "var(--font-size-xs)",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};
