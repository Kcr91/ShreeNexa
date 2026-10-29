import React from "react";
import { StrategyBuilderState } from "../types";
import { decompileCanonicalIRToVisual, CanonicalStrategyIR } from "../canonical";
import {
  extractFromPdf,
  extractFromText,
  ExtractionResult,
  ConfidenceLevel,
} from "../pdfExtractService";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onLoad: (state: StrategyBuilderState) => void;
}

const MAX_PDF_BYTES = 10 * 1024 * 1024;

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  backgroundColor: "rgba(0,0,0,0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: "16px",
};

const modalStyle: React.CSSProperties = {
  width: "min(960px, 100%)",
  maxHeight: "90vh",
  backgroundColor: "var(--bg-surface)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-md, 6px)",
  padding: "var(--spacing-3)",
  display: "flex",
  flexDirection: "column",
  gap: "var(--spacing-2)",
  overflow: "hidden",
};

const btnStyle: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: "0.6875rem",
  cursor: "pointer",
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
};

const primaryBtn: React.CSSProperties = {
  ...btnStyle,
  backgroundColor: "var(--color-primary)",
  color: "var(--text-inverse)",
  border: "none",
  fontWeight: 700,
};

const inputStyle: React.CSSProperties = {
  backgroundColor: "var(--bg-active)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-sm)",
  padding: "6px 8px",
  fontSize: "0.6875rem",
  width: "100%",
};

const CONF_COLOR: Record<ConfidenceLevel, string> = {
  high: "var(--color-up)",
  medium: "#eab308",
  low: "var(--color-down)",
};

const CONF_LABEL: Record<ConfidenceLevel, string> = {
  high: "High ✓",
  medium: "Medium ?",
  low: "Low !",
};

type Stage = "upload" | "processing" | "review" | "error";

export const PDFExtractorPanel: React.FC<Props> = ({ isOpen, onClose, onLoad }) => {
  const [stage, setStage] = React.useState<Stage>("upload");
  const [file, setFile] = React.useState<File | null>(null);
  const [rawText, setRawText] = React.useState<string>("");
  const [strategyName, setStrategyName] = React.useState<string>("Extracted Strategy");
  const [progressMsg, setProgressMsg] = React.useState<string>("");
  const [errorMsg, setErrorMsg] = React.useState<string>("");
  const [result, setResult] = React.useState<ExtractionResult | null>(null);

  React.useEffect(() => {
    if (!isOpen) {
      // Reset on close.
      setStage("upload");
      setFile(null);
      setRawText("");
      setStrategyName("Extracted Strategy");
      setProgressMsg("");
      setErrorMsg("");
      setResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFile = (f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErrorMsg("Only .pdf files are accepted.");
      return;
    }
    if (f.size > MAX_PDF_BYTES) {
      setErrorMsg("PDF exceeds 10 MB.");
      return;
    }
    setErrorMsg("");
    setFile(f);
  };

  const runPdf = async () => {
    if (!file) return;
    setStage("processing");
    setProgressMsg("Uploading PDF…");
    try {
      setProgressMsg("Extracting text and analysing strategy rules…");
      const r = await extractFromPdf(file, strategyName);
      setResult(r);
      setStage("review");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Extraction failed.";
      setErrorMsg(msg);
      setStage("error");
    }
  };

  const runText = async () => {
    if (!rawText.trim()) return;
    setStage("processing");
    setProgressMsg("Analysing strategy rules…");
    try {
      const r = await extractFromText(rawText, strategyName);
      setResult(r);
      setStage("review");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Extraction failed.";
      setErrorMsg(msg);
      setStage("error");
    }
  };

  const loadIntoBuilder = () => {
    if (!result) return;
    const ir = result.strategy_ir as unknown as CanonicalStrategyIR;
    const state = decompileCanonicalIRToVisual(ir);
    onLoad(state);
    onClose();
  };

  return (
    <div style={overlayStyle} data-testid="pdf-extractor-modal" role="dialog" aria-label="Import strategy from PDF">
      <div style={modalStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>Import Strategy from PDF or Text</strong>
          <button type="button" onClick={onClose} style={btnStyle} aria-label="Close">✕</button>
        </div>

        {stage === "upload" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)", overflow: "auto" }}>
            <label style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Strategy name</label>
            <input value={strategyName} onChange={(e) => setStrategyName(e.target.value)} style={inputStyle} aria-label="Strategy name" />

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const f = e.dataTransfer.files?.[0];
                handleFile(f ?? null);
              }}
              style={{
                border: "2px dashed var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: "var(--spacing-3)",
                textAlign: "center",
                color: "var(--text-muted)",
                fontSize: "0.6875rem",
              }}
            >
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                aria-label="PDF file"
                data-testid="pdf-file-input"
              />
              <div style={{ marginTop: "6px" }}>Drag & drop a .pdf file here, or use the picker above. Max 10 MB.</div>
              {file && (
                <div data-testid="selected-file" style={{ marginTop: "6px", color: "var(--text-primary)" }}>
                  Selected: <strong>{file.name}</strong> ({Math.round(file.size / 1024)} KB)
                </div>
              )}
              <button type="button" onClick={runPdf} disabled={!file} style={{ ...primaryBtn, marginTop: "8px" }}>
                Extract from PDF
              </button>
            </div>

            <details>
              <summary style={{ cursor: "pointer", fontSize: "0.75rem" }}>Or paste strategy text directly</summary>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={8}
                placeholder="Paste a strategy description. The parser looks for indicators (EMA/RSI/MACD/...), entry/exit sections, timeframe, and stop-loss / target percentages."
                style={{ ...inputStyle, marginTop: "6px", fontFamily: "var(--font-family-mono)" }}
                aria-label="Strategy text"
                data-testid="pdf-text-input"
              />
              <button type="button" onClick={runText} disabled={!rawText.trim()} style={{ ...primaryBtn, marginTop: "6px" }}>
                Extract from Text
              </button>
            </details>

            {errorMsg && (
              <div style={{ color: "var(--color-down)", fontSize: "0.6875rem" }}>{errorMsg}</div>
            )}
          </div>
        )}

        {stage === "processing" && (
          <div data-testid="pdf-processing" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
            {progressMsg}
          </div>
        )}

        {stage === "error" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
            <div data-testid="pdf-error" style={{ color: "var(--color-down)", fontSize: "0.75rem" }}>
              {errorMsg}
            </div>
            <button type="button" onClick={() => setStage("upload")} style={btnStyle}>Try again</button>
          </div>
        )}

        {stage === "review" && result && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-2)", overflow: "hidden", flex: 1 }}>
            <div style={{ overflow: "auto", fontSize: "0.6875rem", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", padding: "6px" }}>
              <strong>Extracted Text</strong>
              <pre style={{ margin: "4px 0 0", whiteSpace: "pre-wrap", fontFamily: "var(--font-family-mono)" }}>
                {result.extracted_text.slice(0, 8000)}
                {result.extracted_text.length > 8000 ? "\n…(truncated)" : ""}
              </pre>
            </div>
            <div style={{ overflow: "auto", display: "flex", flexDirection: "column", gap: "6px" }} data-testid="pdf-review">
              {result.extraction_report.warnings.length > 0 && (
                <div style={{ fontSize: "0.6875rem", color: "#eab308" }}>
                  {result.extraction_report.warnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}
              <ComponentCards title="Indicators" items={result.extraction_report.components_found.indicators} />
              <ComponentCards title="Entry Conditions" items={result.extraction_report.components_found.entry_conditions} />
              <ComponentCards title="Exit Conditions" items={result.extraction_report.components_found.exit_conditions} />
              {result.extraction_report.components_found.timeframe && (
                <ComponentCards title="Timeframe" items={[result.extraction_report.components_found.timeframe]} />
              )}
              <ComponentCards title="Risk Parameters" items={result.extraction_report.components_found.risk_params} />
              <button type="button" onClick={loadIntoBuilder} style={{ ...primaryBtn, alignSelf: "flex-start" }} data-testid="pdf-load-builder">
                Load into Builder
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ComponentCards: React.FC<{ title: string; items: { description: string; confidence: ConfidenceLevel; source_text: string }[] }> = ({
  title,
  items,
}) => {
  if (!items || items.length === 0) {
    return (
      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
        <strong style={{ color: "var(--text-primary)" }}>{title}:</strong> none detected
      </div>
    );
  }
  return (
    <div>
      <div style={{ fontSize: "0.625rem", color: "var(--text-muted)", textTransform: "uppercase" }}>{title}</div>
      {items.map((it, i) => (
        <div
          key={i}
          style={{
            marginTop: "4px",
            padding: "4px 6px",
            backgroundColor: "var(--bg-active)",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.6875rem",
            borderLeft: `3px solid ${CONF_COLOR[it.confidence]}`,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: "6px" }}>
            <strong>{it.description}</strong>
            <span style={{ color: CONF_COLOR[it.confidence], fontSize: "0.625rem" }}>
              {CONF_LABEL[it.confidence]}
            </span>
          </div>
          {it.source_text && (
            <div style={{ color: "var(--text-muted)", fontSize: "0.625rem", marginTop: "2px" }}>
              “{it.source_text}”
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
