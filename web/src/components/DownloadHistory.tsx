"use client";

import React from "react";
import { HistoryItem, clearStoredHistory } from "@/lib/storage";
import { Language, translations } from "@/lib/i18n";
import { apiClient } from "@/lib/api-client";
import { X, Trash2, Download, Video, Calendar } from "lucide-react";

interface DownloadHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  items: HistoryItem[];
  lang: Language;
  onClear: () => void;
}

export function DownloadHistory({ isOpen, onClose, items, lang, onClear }: DownloadHistoryProps) {
  const t = translations[lang];

  if (!isOpen) return null;

  const formatBytes = (bytes?: number | null): string => {
    if (!bytes || bytes <= 0) return "--";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString(lang === "bn" ? "bn-BD" : "en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-base sm:text-lg text-slate-900 dark:text-slate-100">
              {t.historyTitle}
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 font-semibold">
              {items.length}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {items.length > 0 && (
              <button
                onClick={onClear}
                className="p-1.5 text-slate-400 hover:text-rose-500 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                title={t.clearHistory}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {items.length === 0 ? (
            <div className="py-12 text-center text-slate-400 dark:text-slate-500">
              <Video className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm font-medium">{t.noHistory}</p>
            </div>
          ) : (
            items.map((item) => (
              <div
                key={item.id}
                className="p-3 rounded-xl border border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-800/30 flex items-center gap-3 justify-between hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-12 h-9 rounded-md bg-slate-200 dark:bg-slate-800 shrink-0 overflow-hidden flex items-center justify-center">
                    {item.thumbnailUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={item.thumbnailUrl}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Video className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {item.title}
                    </p>
                    <div className="flex items-center gap-2 text-[10px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {item.qualityLabel && (
                        <span className="font-semibold text-blue-600 dark:text-blue-400">
                          {item.qualityLabel}
                        </span>
                      )}
                      {item.fileSize && <span>• {formatBytes(item.fileSize)}</span>}
                      <span className="hidden sm:inline flex items-center gap-0.5">
                        <Calendar className="w-3 h-3 inline" /> {formatDate(item.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>

                <a
                  href={apiClient.resolveDownloadUrl(item.downloadUrl)}
                  download
                  className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition-colors shrink-0"
                  title={t.saveFile}
                >
                  <Download className="w-4 h-4" />
                </a>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

