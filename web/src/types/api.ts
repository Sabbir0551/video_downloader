/**
 * AnyStream Video Platform - API Types
 * Strictly synchronized with backend schemas and docs/api/openapi.yaml
 */

export const JobStatus = {
  QUEUED: "QUEUED",
  PROCESSING: "PROCESSING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  CANCELLED: "CANCELLED",
  EXPIRED: "EXPIRED",
} as const;

export type JobStatus = (typeof JobStatus)[keyof typeof JobStatus];

export interface FormatOption {
  format_id: string;
  resolution?: string | null;
  height?: number | null;
  fps?: number | null;
  ext: string;
  format_note: string;
  filesize?: number | null;
  filesize_approx?: number | null;
  is_audio_only: boolean;
  abr?: number | null;
}

export interface MediaInfoResponse {
  id: string;
  title: string;
  url: string;
  thumbnail_url: string;
  duration: number;
  uploader?: string | null;
  extractor?: string | null;
  is_live?: boolean;
  formats: FormatOption[];
}

export interface UrlExtractRequest {
  url: string;
  captcha_token?: string | null;
}

export interface CreateJobRequest {
  url: string;
  format_id: string;
  audio_only?: boolean;
  quality_label?: string | null;
  captcha_token?: string | null;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  speed?: string | null;
  eta?: number | null;
  file_size?: number | null;
  download_url?: string | null;
  created_at: string;
  expires_at: string;
  job_access_token?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface TakedownRequest {
  requester_name: string;
  requester_email: string;
  copyrighted_work_url: string;
  infringing_url: string;
  statement?: string | null;
  declaration_truth: boolean;
}

export interface TakedownResponse {
  case_id: string;
  status: string;
  message: string;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  project: string;
  version: string;
  environment: string;
  database: string;
  cache: string;
  ytdlp_version: string;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
}


export interface PlatformMetadata {
  id: string;
  name: string;
  domains: string[];
  category: string;
  tier: "supported" | "best_effort" | "unsupported_no_video" | "login_or_paid" | "defunct";
  status: string;
  has_public_video: boolean;
  requires_login: boolean;
  supports_audio_only: boolean;
  max_quality_expected: string;
  per_platform_concurrency: number;
  per_platform_rate_limit: string;
  notes?: string | null;
  extractor_keys: string[];
}

export interface PlatformsListResponse {
  version: string;
  last_verified: string;
  ytdlp_version: string;
  total: number;
  tiers_summary: Record<string, number>;
  platforms: PlatformMetadata[];
}

export interface PlatformDetectResponse {
  detected: boolean;
  platform?: PlatformMetadata | null;
  tier: string;
  allowed: boolean;
  requires_login: boolean;
  has_public_video: boolean;
  message?: string;
}
