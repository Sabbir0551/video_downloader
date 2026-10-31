/**
 * AnyStream Video Platform - Typed HTTP API Client
 */

import {
  CreateJobRequest,
  ErrorResponse,
  HealthResponse,
  JobStatusResponse,
  MediaInfoResponse,
  TakedownRequest,
  TakedownResponse,
  UrlExtractRequest,
} from "@/types/api";

export class ApiClientError extends Error {
  public errorCode: string;
  public status: number;
  public details: Record<string, unknown>;

  constructor(status: number, errorData: ErrorResponse) {
    super(errorData.message || "An unexpected API error occurred.");
    this.name = "ApiClientError";
    this.status = status;
    this.errorCode = errorData.error_code || "UNKNOWN_ERROR";
    this.details = errorData.details || {};
  }
}

export class AnyStreamApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    const raw = baseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    // Strip trailing slashes
    this.baseUrl = raw.replace(/\/+$/, "");
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  /**
   * Resolves relative download paths (e.g. /api/v1/downloads/...) to absolute URLs.
   */
  public resolveDownloadUrl(downloadUrl: string, accessToken?: string | null): string {
    if (!downloadUrl) return "";
    let fullUrl = downloadUrl;
    if (!downloadUrl.startsWith("http://") && !downloadUrl.startsWith("https://")) {
      const cleanPath = downloadUrl.startsWith("/") ? downloadUrl : `/${downloadUrl}`;
      fullUrl = `${this.baseUrl}${cleanPath}`;
    }
    if (accessToken && !fullUrl.includes("token=")) {
      const sep = fullUrl.includes("?") ? "&" : "?";
      fullUrl = `${fullUrl}${sep}token=${encodeURIComponent(accessToken)}`;
    }
    return fullUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const headers = new Headers(options.headers || {});
    
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: ErrorResponse;
      try {
        errorData = await response.json();
      } catch {
        errorData = {
          error_code: `HTTP_${response.status}`,
          message: response.statusText || `Request failed with status ${response.status}`,
          details: {},
        };
      }
      throw new ApiClientError(response.status, errorData);
    }

    return (await response.json()) as T;
  }

  /**
   * System health check
   */
  public async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health", {
      method: "GET",
      cache: "no-store",
    });
  }

  /**
   * Validate URL against SSRF policy and retrieve format details
   */
  public async getMediaInfo(
    url: string,
    captchaToken?: string | null
  ): Promise<MediaInfoResponse> {
    const payload: UrlExtractRequest = {
      url: url.trim(),
      captcha_token: captchaToken || null,
    };

    return this.request<MediaInfoResponse>("/api/v1/info", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  /**
   * Submit background media download job
   */
  public async createJob(payload: CreateJobRequest): Promise<JobStatusResponse> {
    return this.request<JobStatusResponse>("/api/v1/downloads", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  /**
   * Poll download job status by UUID or Video URL
   */
  public async getJobStatus(jobIdOrUrl: string, accessToken?: string | null): Promise<JobStatusResponse> {
    const encoded = encodeURIComponent(jobIdOrUrl.trim());
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["X-Job-Token"] = accessToken;
    }
    const query = accessToken ? `?token=${encodeURIComponent(accessToken)}` : "";
    return this.request<JobStatusResponse>(`/api/v1/downloads/${encoded}${query}`, {
      method: "GET",
      headers,
      cache: "no-store",
    });
  }

  /**
   * Cancel in-flight download job
   */
  public async cancelJob(jobId: string, accessToken?: string | null): Promise<JobStatusResponse> {
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["X-Job-Token"] = accessToken;
    }
    const query = accessToken ? `?token=${encodeURIComponent(accessToken)}` : "";
    return this.request<JobStatusResponse>(`/api/v1/downloads/${jobId}${query}`, {
      method: "DELETE",
      headers,
    });
  }

  /**
   * Submit legal copyright/DMCA takedown notice
   */
  public async submitTakedown(payload: TakedownRequest): Promise<TakedownResponse> {
    return this.request<TakedownResponse>("/api/v1/takedown", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}

// Default singleton client instance
export const apiClient = new AnyStreamApiClient();

