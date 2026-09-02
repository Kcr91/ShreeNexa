/**
 * ShreeNexa Terminal Typed API Client Boundary
 */

export interface ApiErrorResponse {
  detail: string | { message?: string };
}

export class ApiError extends Error {
  public status: number;
  public data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface TokenHealthResponse {
  status: "active" | "expiring_soon" | "expired" | "not_configured";
  expires_at?: string;
  days_remaining?: number;
  message?: string;
}

export interface ProcessHealthResponse {
  status: string;
  uptime_seconds: number;
  version: string;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
        let errorData: unknown;
        try {
          errorData = await response.json();
          if (errorData && typeof errorData === "object" && "detail" in errorData) {
            const detail = (errorData as ApiErrorResponse).detail;
            errorMsg = typeof detail === "string" ? detail : (detail.message || errorMsg);
          }
        } catch {
          // Response was not JSON
        }
        throw new ApiError(errorMsg, response.status, errorData);
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        throw err;
      }
      const message = err instanceof Error ? err.message : "Network or connection error";
      throw new ApiError(message, 0);
    }
  }

  public async getHealth(): Promise<ProcessHealthResponse> {
    return this.request<ProcessHealthResponse>("/health");
  }

  public async getTokenHealth(): Promise<TokenHealthResponse> {
    return this.request<TokenHealthResponse>("/api/v1/dhan/token-health");
  }
}

export const apiClient = new ApiClient();
