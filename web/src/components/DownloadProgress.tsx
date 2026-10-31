"use client";

import React, { useEffect, useState, useRef } from "react";
import { JobStatusResponse, JobStatus } from "@/types/api";
import { apiClient } from "@/lib/api-client";
import { Language, translations, getErrorMessage } from "@/lib/i18n";
import { saveHistoryItem } from "@/lib/storage";
import {
  Download,
  XCircle,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Clock,
  Gauge,
  HardDrive,
  FileCheck,
} from "lucide-react";

interface DownloadProgressProps {
  jobId: string;
  accessToken?: string | null;
  videoTitle: string;
  thumbnailUrl?: string | null;
  qualityLabel?: string | null;
  lang: Language;
  onCancel: () => void;
  onRetry: () => void;
}

export function DownloadProgress({
  jobId,
  accessToken,
  videoTitle,
  thumbnailUrl,
  qualityLabel,
  lang,
  onCancel,
  onRetry,
}: DownloadProgressProps) {
  const t = translations[lang];
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasSavedToHistoryRef = useRef<boolean>(false);

  // Format file size
  const formatBytes = (bytes?: number | null): string => {
    if (!bytes || bytes <= 0) return "--";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  useEffect(() => {
    let consecutiveErrors = 0;
    let isTerminated = false;
    let eventSource: EventSource | null = null;
    let fallbackInterval: NodeJS.Timeout | null = null;

    const onJobUpdate = (data: JobStatusResponse) => {
      setJob(data);
      consecutiveErrors = 0;

      // If completed, save to local history once
      if (data.status === JobStatus.COMPLETED && data.download_url && !hasSavedToHistoryRef.current) {
        hasSavedToHistoryRef.current = true;
        saveHistoryItem({
          id: data.job_id,
          title: videoTitle,
          url: data.download_url,
          thumbnailUrl: thumbnailUrl,
          qualityLabel: qualityLabel,
          fileSize: data.file_size,
          downloadUrl: data.download_url,
          timestamp: Date.now(),
        });
      }

      // Stop tracking on terminal states
      if (
        data.status === JobStatus.COMPLETED ||
        data.status === JobStatus.FAILED ||
        data.status === JobStatus.CANCELLED ||
        data.status === JobStatus.EXPIRED
      ) {
        isTerminated = true;
        if (eventSource) eventSource.close();
        if (fallbackInterval) clearInterval(fallbackInterval);
        if (data.status === JobStatus.FAILED) {
          setErrorMsg(data.error_message || getErrorMessage(data.error_code, lang));
        }
      }
    };

    const startPollingFallback = () => {
      if (fallbackInterval || isTerminated) return;
      const poll = async () => {
        if (isTerminated) return;
        try {
          const data = accessToken
            ? await apiClient.getJobStatus(jobId, accessToken)
            : await apiClient.getJobStatus(jobId);
          onJobUpdate(data);
        } catch {
          consecutiveErrors++;
          if (consecutiveErrors > 15) {
            if (fallbackInterval) clearInterval(fallbackInterval);
            setErrorMsg(t.errors.DEFAULT);
          }
        }
      };
      poll();
      fallbackInterval = setInterval(poll, 1000);
      pollIntervalRef.current = fallbackInterval;
    };

    // Attempt Server-Sent Events (SSE) streaming with transparent polling fallback
    if (typeof window !== "undefined" && "EventSource" in window) {
      try {
        const streamUrl = `${apiClient.getBaseUrl()}/api/v1/downloads/${jobId}/stream${accessToken ? `?token=${encodeURIComponent(accessToken)}` : ""}`;
        eventSource = new EventSource(streamUrl);

        eventSource.onmessage = (event) => {
          try {
            const data: JobStatusResponse = JSON.parse(event.data);
            onJobUpdate(data);
          } catch {
            // Keepalive or unparseable frame
          }
        };

        eventSource.onerror = () => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          startPollingFallback();
        };
      } catch {
        startPollingFallback();
      }
    } else {
      startPollingFallback();
    }

    return () => {
      isTerminated = true;
      if (eventSource) eventSource.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [jobId, accessToken, videoTitle, thumbnailUrl, qualityLabel, lang, t]);

  const handleCancel = async () => {
    if (isCancelling) return;
    setIsCancelling(true);
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    try {
      if (accessToken) {
        await apiClient.cancelJob(jobId, accessToken);
      } else {
        await apiClient.cancelJob(jobId);
      }
    } catch {
      // Ignore cancellation failure if already terminated
    } finally {
      setIsCancelling(false);
      onCancel();
    }
  };

  const progressPct = Math.min(100, Math.max(0, Math.round(job?.progress || 0)));
  const isCompleted = job?.status === JobStatus.COMPLETED;
  const isFailed = job?.status === JobStatus.FAILED || job?.status === JobStatus.CANCELLED || job?.status === JobStatus.EXPIRED;
  const downloadAbsoluteUrl = job?.download_url
    ? accessToken
      ? apiClient.resolveDownloadUrl(job.download_url, accessToken)
      : apiClient.resolveDownloadUrl(job.download_url)
    : "";

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-md transition-all">
      {/* Header and Status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          {isCompleted ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          ) : isFailed ? (
            <AlertTriangle className="w-5 h-5 text-rose-500" />
          ) : (
            <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
          )}

          <div>
            <h3 className="font-bold text-sm sm:text-base text-slate-900 dark:text-slate-100">
              {isCompleted
                ? t.completed
                : job?.status === JobStatus.PROCESSING
                ? t.processing
                : job?.status === JobStatus.QUEUED
                ? t.queued
                : isFailed
                ? t.failed
                : t.starting}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-1">
              {videoTitle} {qualityLabel ? `(${qualityLabel})` : ""}
            </p>
          </div>
        </div>

        {/* Cancel button during download */}
        {!isCompleted && !isFailed && (
          <button
            onClick={handleCancel}
            disabled={isCancelling}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 transition-colors disabled:opacity-50 cursor-pointer"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>{isCancelling ? t.cancelling : t.cancel}</span>
          </button>
        )}
      </div>

      {/* Progress Bar Container */}
      <div className="space-y-2">
        <div className="w-full h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden relative">
          <div
            className={`h-full transition-all duration-300 rounded-full ${
              isCompleted
                ? "bg-gradient-to-r from-emerald-500 to-teal-500"
                : isFailed
                ? "bg-rose-500"
                : "bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 animate-pulse"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Metrics Row */}
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-medium">
          <span className="font-bold text-slate-700 dark:text-slate-200">{progressPct}%</span>

          <div className="flex items-center gap-4">
            {job?.speed && (
              <span className="flex items-center gap-1">
                <Gauge className="w-3.5 h-3.5 text-blue-500" />
                {t.speed}: {job.speed}
              </span>
            )}

            {job?.eta !== null && job?.eta !== undefined && job.eta > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                {t.eta}: {job.eta}
                {t.seconds}
              </span>
            )}

            {job?.file_size && (
              <span className="hidden sm:flex items-center gap-1">
                <HardDrive className="w-3.5 h-3.5 text-indigo-500" />
                {formatBytes(job.file_size)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Action Area: Completed */}
      {isCompleted && downloadAbsoluteUrl && (
        <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
          <a
            href={downloadAbsoluteUrl}
            download
            className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-base shadow-lg shadow-emerald-500/25 transition-all text-center cursor-pointer"
          >
            <Download className="w-5 h-5" />
            <span>{t.saveFile}</span>
            {job?.file_size ? (
              <span className="text-xs bg-black/20 px-2 py-0.5 rounded-full font-normal">
                {formatBytes(job.file_size)}
              </span>
            ) : null}
          </a>

          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <span className="flex items-center gap-1">
              <FileCheck className="w-3.5 h-3.5 text-emerald-500" />
              {t.secureTokenVerified}
            </span>
            <span>{t.linkExpiresIn30Mins}</span>
          </div>
        </div>
      )}

      {/* Action Area: Failed */}
      {isFailed && (
        <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-rose-500 font-medium">
            {errorMsg || t.failed}
          </p>

          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{t.retry}</span>
          </button>
        </div>
      )}
    </div>
  );
}
