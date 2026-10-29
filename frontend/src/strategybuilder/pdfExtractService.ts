/**
 * Service wrapping /api/v1/strategy/extract-from-{text,pdf}.
 * The parser is backend-side rule-based and does not reach any LLM.
 */

import { apiClient } from "../api/client";

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ExtractedComponent {
  description: string;
  confidence: ConfidenceLevel;
  source_text: string;
}

export interface ExtractionComponents {
  indicators: ExtractedComponent[];
  entry_conditions: ExtractedComponent[];
  exit_conditions: ExtractedComponent[];
  timeframe?: ExtractedComponent | null;
  risk_params: ExtractedComponent[];
}

export interface ExtractionReport {
  name: string;
  confidence: ConfidenceLevel;
  components_found: ExtractionComponents;
  warnings: string[];
}

export interface ExtractionResult {
  success: boolean;
  extracted_text: string;
  strategy_ir: Record<string, unknown>;
  extraction_report: ExtractionReport;
}

export async function extractFromText(text: string, name = "Extracted Strategy"): Promise<ExtractionResult> {
  return apiClient.request<ExtractionResult>("/api/v1/strategy/extract-from-text", {
    method: "POST",
    body: JSON.stringify({ text, name }),
  });
}

export async function extractFromPdf(file: File, name = "Extracted Strategy"): Promise<ExtractionResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  // Can't go through apiClient.request directly because it sets JSON headers.
  // Build the fetch call manually but reuse the API base URL + CSRF.
  const base =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL
      ? (import.meta.env.VITE_API_BASE_URL as string)
      : "").replace(/\/$/, "");
  const headers: Record<string, string> = { Accept: "application/json" };
  const csrf = apiClient.getCsrfToken();
  if (csrf) {
    headers["x-csrf-token"] = csrf;
    headers["Authorization"] = `Bearer ${csrf}`;
  }
  const url = `${base}/api/v1/strategy/extract-from-pdf`;
  const response = await fetch(url, {
    method: "POST",
    body: form,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const j = await response.json();
      if (j && typeof j.detail === "string") detail = j.detail;
    } catch {
      /* non-JSON */
    }
    throw new Error(detail);
  }
  return (await response.json()) as ExtractionResult;
}
