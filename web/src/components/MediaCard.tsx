"use client";

import React, { useState } from "react";
import { FormatOption, MediaInfoResponse } from "@/types/api";
import { Language, translations } from "@/lib/i18n";
import { Video, Music, Clock, User, Download, CheckCircle2 } from "lucide-react";

interface MediaCardProps {
  media: MediaInfoResponse;
  lang: Language;
  onStartDownload: (formatId: string, isAudioOnly: boolean, label: string) => void;
  isStarting: boolean;
}

export function MediaCard({ media, lang, onStartDownload, isStarting }: MediaCardProps) {
  const t = translations[lang];
  const [activeTab, setActiveTab] = useState<"video" | "audio">("video");
  const [selectedFormatId, setSelectedFormatId] = useState<string>("best");
  const [selectedIsAudio, setSelectedIsAudio] = useState<boolean>(false);
  const [selectedLabel, setSelectedLabel] = useState<string>(t.bestQuality);

  // Format duration into readable string
  const formatDuration = (seconds?: number | null): string => {
    if (!seconds) return "";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins >= 60) {
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      return `${hours}h ${remMins}m ${secs}s`;
    }
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  // Format file size
  const formatBytes = (bytes?: number | null): string => {
    if (!bytes || bytes <= 0) return "--";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Separate video vs audio formats
  const videoFormats = (media.formats || []).filter((f) => !f.is_audio_only);
  const audioFormats = (media.formats || []).filter((f) => f.is_audio_only);

  const handleSelectFormat = (id: string, isAudio: boolean, label: string) => {
    setSelectedFormatId(id);
    setSelectedIsAudio(isAudio);
    setSelectedLabel(label);
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-md shadow-slate-950/5 transition-all">
      {/* Media Details Row */}
      <div className="flex flex-col sm:flex-row gap-5">
        {/* Thumbnail */}
        <div className="relative w-full sm:w-60 aspect-video rounded-xl overflow-hidden bg-slate-950 shrink-0 border border-slate-200 dark:border-slate-800">
          {media.thumbnail_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={media.thumbnail_url}
              alt={media.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-500">
              <Video className="w-10 h-10 opacity-40" />
            </div>
          )}

          {/* Duration overlay badge */}
          {media.duration ? (
            <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/80 backdrop-blur text-white text-xs font-semibold flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDuration(media.duration)}
            </span>
          ) : null}
        </div>

        {/* Video metadata */}
        <div className="flex-1 flex flex-col justify-between py-0.5">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug">
              {media.title}
            </h2>

            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
              {media.uploader && (
                <span className="flex items-center gap-1.5 font-medium">
                  <User className="w-3.5 h-3.5 text-blue-500" />
                  {media.uploader}
                </span>
              )}
              {media.extractor && (
                <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[11px] font-semibold uppercase text-slate-600 dark:text-slate-300">
                  {media.extractor}
                </span>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Selected: <strong className="text-blue-600 dark:text-blue-400 font-semibold">{selectedLabel}</strong>
            </span>

            <button
              onClick={() => onStartDownload(selectedFormatId, selectedIsAudio, selectedLabel)}
              disabled={isStarting}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold text-sm shadow-md shadow-emerald-500/20 transition-all disabled:opacity-60 cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>{isStarting ? t.starting : t.downloadNow}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Format Selector Section */}
      <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {t.qualitySectionTitle}
          </span>

          {/* Quality tabs */}
          <div className="flex rounded-lg bg-slate-100 dark:bg-slate-800/80 p-0.5 border border-slate-200 dark:border-slate-700/60">
            <button
              onClick={() => {
                setActiveTab("video");
                setSelectedIsAudio(false);
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                activeTab === "video"
                  ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <Video className="w-3.5 h-3.5" />
              <span>{t.tabVideo}</span>
            </button>

            <button
              onClick={() => {
                setActiveTab("audio");
                setSelectedIsAudio(true);
                // default to first audio if exists or best audio
                if (audioFormats.length > 0) {
                  setSelectedFormatId(audioFormats[0].format_id);
                  setSelectedLabel(audioFormats[0].resolution || "MP3");
                } else {
                  setSelectedFormatId("bestaudio+mp3");
                  setSelectedLabel("MP3 (192kbps)");
                }
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all ${
                activeTab === "audio"
                  ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <Music className="w-3.5 h-3.5" />
              <span>{t.tabAudio}</span>
            </button>
          </div>
        </div>

        {/* Format Options Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {activeTab === "video" ? (
            <>
              {/* Default Best Quality Tile */}
              <button
                type="button"
                onClick={() => handleSelectFormat("best", false, t.bestQuality)}
                className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  selectedFormatId === "best" && !selectedIsAudio
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {selectedFormatId === "best" && !selectedIsAudio && (
                  <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  {t.bestQuality}
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  MP4 (HD / Auto)
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  Optimal Quality
                </div>
              </button>

              {/* Individual video format options */}
              {videoFormats.slice(0, 7).map((fmt) => {
                const isSelected = selectedFormatId === fmt.format_id && !selectedIsAudio;
                const label = fmt.resolution || fmt.ext.toUpperCase();
                return (
                  <button
                    key={fmt.format_id}
                    type="button"
                    onClick={() => handleSelectFormat(fmt.format_id, false, label)}
                    className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                        : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    {isSelected && (
                      <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                    )}
                    <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                      {label}
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400 font-medium mt-0.5 uppercase">
                      {fmt.ext} {fmt.fps ? `• ${fmt.fps}fps` : ""}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {fmt.filesize ? formatBytes(fmt.filesize) : "Est. Size Auto"}
                    </div>
                  </button>
                );
              })}
            </>
          ) : (
            <>
              {/* Audio MP3 Tile */}
              <button
                type="button"
                onClick={() => handleSelectFormat("bestaudio+mp3", true, "MP3 (192kbps)")}
                className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  selectedFormatId === "bestaudio+mp3"
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {selectedFormatId === "bestaudio+mp3" && (
                  <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  MP3 Audio
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  192 kbps • MP3
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  Universal Compatible
                </div>
              </button>

              {/* Audio M4A / AAC Tile */}
              <button
                type="button"
                onClick={() => handleSelectFormat("bestaudio", true, "M4A (AAC)")}
                className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  selectedFormatId === "bestaudio"
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {selectedFormatId === "bestaudio" && (
                  <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  M4A Audio
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  Direct AAC Stream
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  Fastest Conversion
                </div>
              </button>

              {/* Available direct audio streams */}
              {audioFormats.slice(0, 2).map((fmt) => {
                const isSelected = selectedFormatId === fmt.format_id;
                const label = fmt.resolution || fmt.ext.toUpperCase();
                return (
                  <button
                    key={fmt.format_id}
                    type="button"
                    onClick={() => handleSelectFormat(fmt.format_id, true, label)}
                    className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                        : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    {isSelected && (
                      <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                    )}
                    <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                      {label}
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400 font-medium mt-0.5 uppercase">
                      {fmt.ext}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {fmt.filesize ? formatBytes(fmt.filesize) : "Est. Size Auto"}
                    </div>
                  </button>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

