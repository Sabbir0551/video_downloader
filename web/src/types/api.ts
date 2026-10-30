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
