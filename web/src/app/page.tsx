"use client";

import React, { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { UrlInput } from "@/components/UrlInput";
import { MediaSkeleton } from "@/components/MediaSkeleton";
import { MediaCard } from "@/components/MediaCard";
import { DownloadProgress } from "@/components/DownloadProgress";
import { DownloadHistory } from "@/components/DownloadHistory";
import { Footer } from "@/components/Footer";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { MediaInfoResponse } from "@/types/api";
import {
  Language,
  translations,
  getErrorMessage,
} from "@/lib/i18n";
import {
  HistoryItem,
  getStoredHistory,
  clearStoredHistory,
  getStoredLang,
  setStoredLang,
  getStoredTheme,
  setStoredTheme,
} from "@/lib/storage";
import { AlertCircle, ArrowLeft } from "lucide-react";

export default function HomePage() {
  const [lang, setLang] = useState<Language>("bn");
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  // Flow State
  const [activeUrl, setActiveUrl] = useState<string>("");
  const [isInspecting, setIsInspecting] = useState<boolean>(false);
  const [isStartingJob, setIsStartingJob] = useState<boolean>(false);
  const [mediaInfo, setMediaInfo] = useState<MediaInfoResponse | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [selectedQualityLabel, setSelectedQualityLabel] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // History State
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);

  // Initialize preferences on client mount
  useEffect(() => {
    const savedLang = getStoredLang();
    const savedTheme = getStoredTheme();
    setLang(savedLang);
    setTheme(savedTheme);
    setStoredTheme(savedTheme);
    setHistoryItems(getStoredHistory());

    // Health ping
    apiClient
      .getHealth()
      .then((h) => setBackendHealthy(h.status === "healthy"))
      .catch(() => setBackendHealthy(false));
  }, []);

  const handleToggleLang = () => {
    const next = lang === "en" ? "bn" : "en";
    setLang(next);
    setStoredLang(next);
  };

  const handleToggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setStoredTheme(next);
  };

  const handleClearHistory = () => {
    clearStoredHistory();
    setHistoryItems([]);
  };

  // Step 2: Handle URL inspection
  const handleInspectUrl = async (url: string) => {
    setActiveUrl(url);
    setIsInspecting(true);
    setErrorMessage(null);
    setMediaInfo(null);
    setActiveJobId(null);

    try {
      const data = await apiClient.getMediaInfo(url);
      setMediaInfo(data);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(getErrorMessage(err.errorCode, lang));
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(translations[lang].errors.DEFAULT);
      }
    } finally {
      setIsInspecting(false);
    }
  };

  // Step 3: Handle download initiation
  const handleStartDownload = async (
    formatId: string,
    isAudioOnly: boolean,
    label: string
  ) => {
    if (!activeUrl) return;
    setIsStartingJob(true);
    setSelectedQualityLabel(label);
    setErrorMessage(null);

    try {
      const job = await apiClient.createJob({
        url: activeUrl,
        format_id: formatId,
        audio_only: isAudioOnly,
        quality_label: label,
      });
      setActiveJobId(job.job_id);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(getErrorMessage(err.errorCode, lang));
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(translations[lang].errors.DEFAULT);
      }
    } finally {
      setIsStartingJob(false);
    }
  };

  const handleCancelDownload = () => {
    setActiveJobId(null);
  };

  const handleRetryDownload = () => {
    setActiveJobId(null);
  };

  const handleResetToSearch = () => {
    setActiveJobId(null);
    setMediaInfo(null);
    setErrorMessage(null);
  };

  const t = translations[lang];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#080d1a] text-slate-900 dark:text-slate-100 transition-colors">
      {/* Navbar Header */}
      <Header
        lang={lang}
        onToggleLang={handleToggleLang}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        historyCount={historyItems.length}
        onOpenHistory={() => {
          setHistoryItems(getStoredHistory());
          setIsHistoryOpen(true);
        }}
        backendHealthy={backendHealthy}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:py-12 flex flex-col items-center">
        {/* Hero Title and Tagline */}
        <div className="text-center max-w-2xl mx-auto mb-8 sm:mb-10">
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 dark:from-blue-400 dark:via-indigo-300 dark:to-purple-400 bg-clip-text text-transparent">
            {t.appName}
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-600 dark:text-slate-400 font-medium">
            {t.tagline}
          </p>
        </div>

        {/* Input Bar Section */}
        <div className="w-full max-w-2xl mb-6">
          <UrlInput
            lang={lang}
            onSearch={handleInspectUrl}
            isLoading={isInspecting}
            initialUrl={activeUrl}
          />
        </div>

        {/* Friendly Error Message Box */}
        {errorMessage && (
          <div className="w-full max-w-2xl mb-6 p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 flex items-start gap-3 shadow-xs animate-in fade-in">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-semibold">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Dynamic Display State Area */}
        <div className="w-full max-w-2xl">
          {/* 1. Loading Skeleton while inspecting */}
          {isInspecting && <MediaSkeleton />}

          {/* 2. Active Download Progress Tracker */}
          {activeJobId && mediaInfo && (
            <div className="space-y-4">
              <button
                onClick={handleResetToSearch}
                className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>{t.changeQualityOrUrl}</span>
              </button>

              <DownloadProgress
                jobId={activeJobId}
                videoTitle={mediaInfo.title}
                thumbnailUrl={mediaInfo.thumbnail_url}
                qualityLabel={selectedQualityLabel}
                lang={lang}
                onCancel={handleCancelDownload}
                onRetry={handleRetryDownload}
              />
            </div>
          )}

          {/* 3. Media Card with Format Options (when not downloading) */}
          {!activeJobId && mediaInfo && (
            <MediaCard
              media={mediaInfo}
              lang={lang}
              onStartDownload={handleStartDownload}
              isStarting={isStartingJob}
            />
          )}
        </div>
      </main>

      {/* Download History Modal */}
      <DownloadHistory
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        items={historyItems}
        lang={lang}
        onClear={handleClearHistory}
      />

      {/* Footer */}
      <Footer lang={lang} />
    </div>
  );
}
