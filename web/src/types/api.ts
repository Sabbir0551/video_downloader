/**
 * AnyStream Video Platform - API Types
 * Strictly synchronized with backend schemas and docs/api/openapi.yaml
 */

export type JobStatus =
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "EXPIRED";

export interface FormatOption {
  format_id: string;
  resolution?: string | null;
  height?: number | null;
  fps?: number | null;
  ext: string;
  format_note: string;
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
  progress?: number | null;
  speed?: string | null;
  eta?: number | null;
  file_size?: number | null;
  download_url?: string | null;
  created_at: string;
  expires_at?: string | null;
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

export type TakedownStatus =
  | "RECEIVED"
  | "BLOCKED_PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED";

export interface TakedownResponse {
  case_id: string;
  status: TakedownStatus;
  message: string;
  created_at: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  ytdlp_version: string;
  database: boolean;
  redis: boolean;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, unknown> | null;
}
