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

export type TokenStatus =
  | "valid"
  | "expiring_soon"
  | "expired"
  | "unknown_expiry"
  | "missing"
  | "revoked";

export interface TokenHealthResponse {
  status: TokenStatus;
  is_valid: boolean;
  expires_at?: string | null;
  expires_in_seconds?: number | null;
  client_id_masked: string;
  source: string;
}

export interface ProcessHealthResponse {
  status: string;
  uptime_seconds: number;
  version: string;
}

export interface LoginResponse {
  requires_totp: boolean;
  challenge_token: string | null;
  message: string;
}

export interface AuthSuccessResponse {
  username: string;
  authenticated: boolean;
  csrf_token: string;
  expires_at: string;
  message: string;
}

export interface UserMeResponse {
  username: string;
  authenticated: boolean;
  csrf_token: string;
  expires_at: string;
}

export class ApiClient {
  private baseUrl: string;
  private csrfToken: string | null = null;

  constructor(baseUrl?: string) {
    const envUrl =
      typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE_URL
        ? (import.meta.env.VITE_API_BASE_URL as string)
        : "";
    this.baseUrl = (baseUrl ?? envUrl).replace(/\/$/, "");
  }

  public setCsrfToken(token: string | null): void {
    this.csrfToken = token;
  }

  public getCsrfToken(): string | null {
    return this.csrfToken;
  }

  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const method = (options.method || "GET").toUpperCase();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers as Record<string, string> | undefined),
    };

    if (this.csrfToken && ["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
      if (!headers["x-csrf-token"] && !headers["X-CSRF-Token"]) {
        headers["x-csrf-token"] = this.csrfToken;
      }
    }

    try {
      const response = await fetch(url, {
        credentials: "include",
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

  public async login(password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  }

  public async verifyTotp(challenge_token: string, totp_code: string): Promise<AuthSuccessResponse> {
    return this.request<AuthSuccessResponse>("/api/v1/auth/totp/verify", {
      method: "POST",
      body: JSON.stringify({ challenge_token, totp_code }),
    });
  }

  public async loginWithRecovery(password: string, recovery_code: string): Promise<AuthSuccessResponse> {
    return this.request<AuthSuccessResponse>("/api/v1/auth/recovery", {
      method: "POST",
      body: JSON.stringify({ password, recovery_code }),
    });
  }

  public async getCurrentUser(): Promise<UserMeResponse> {
    return this.request<UserMeResponse>("/api/v1/auth/me");
  }

  public async logout(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>("/api/v1/auth/logout", {
      method: "POST",
    });
  }

  public async getHealth(): Promise<ProcessHealthResponse> {
    return this.request<ProcessHealthResponse>("/health");
  }

  public async getTokenHealth(): Promise<TokenHealthResponse> {
    return this.request<TokenHealthResponse>("/api/v1/dhan/token-health");
  }
}

export const apiClient = new ApiClient();
