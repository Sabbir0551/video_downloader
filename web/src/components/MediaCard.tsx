"use client";

import React, { useState } from "react";
import { FormatOption, MediaInfoResponse } from "@/types/api";
import { Language, translations } from "@/lib/i18n";
import { Video, Music, Clock, User, Download, CheckCircle2, Sparkles } from "lucide-react";

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
              {media.platform_id && (
                <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-semibold text-emerald-400">
                  {media.platform_id.toUpperCase()}
                </span>
              )}
            </div>
          </div>

          {/* Selected Quality & Download CTA Banner */}
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              <span>{t.selectedQuality}: </span>
              <strong className="text-slate-800 dark:text-slate-200">{selectedLabel}</strong>
            </div>

            <button
              onClick={() => onStartDownload(selectedFormatId, selectedIsAudio, selectedLabel)}
              disabled={isStarting}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-sm shadow-md shadow-blue-500/20 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
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
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
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
                setSelectedFormatId("bestaudio+mp3");
                setSelectedLabel("MP3 (192kbps)");
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer ${
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
                <div className="flex items-center gap-1 font-bold text-sm text-slate-900 dark:text-slate-100">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  {t.bestQuality}
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  Auto • Best Available
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  {t.optimalQuality}
                </div>
              </button>

              {/* Individual video format options */}
              {videoFormats.map((fmt) => {
                const isSelected = selectedFormatId === fmt.format_id && !selectedIsAudio;
                const label = fmt.resolution || fmt.ext.toUpperCase();
                return (
                  <button
                    key={fmt.format_id}
                    type="button"
                    onClick={() => handleSelectFormat(fmt.format_id, false, fmt.format_note || label)}
                    className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                        : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    {isSelected && (
                      <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                    )}
                    <div className="flex items-center gap-1.5 font-bold text-sm text-slate-900 dark:text-slate-100">
                      <span>{label}</span>
                      {fmt.is_hdr && (
                        <span className="px-1 py-0.2 text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded">
                          HDR
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-600 dark:text-slate-400 font-medium mt-0.5 uppercase">
                      {fmt.ext} {fmt.fps && fmt.fps >= 50 ? `• ${Math.round(fmt.fps)}fps` : ""}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      <span>{fmt.filesize_approx ? formatBytes(fmt.filesize_approx) : t.estSizeAuto}</span>
                      <span className="capitalize text-[9px] text-slate-500">
                        {fmt.mode === "compatible_mp4" ? "MP4" : "Original"}
                      </span>
                    </div>
                  </button>
                );
              })}
            </>
          ) : (
            <>
              {/* Primary MP3 Option */}
              <button
                type="button"
                onClick={() => handleSelectFormat("bestaudio+mp3", true, t.mp3Title)}
                className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  selectedFormatId === "bestaudio+mp3" && selectedIsAudio
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {selectedFormatId === "bestaudio+mp3" && selectedIsAudio && (
                  <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  {t.mp3Title}
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  {t.mp3Desc}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  {t.universalCompatible}
                </div>
              </button>

              {/* Primary M4A Option */}
              <button
                type="button"
                onClick={() => handleSelectFormat("bestaudio", true, t.m4aTitle)}
                className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                  selectedFormatId === "bestaudio" && selectedIsAudio
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                    : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                {selectedFormatId === "bestaudio" && selectedIsAudio && (
                  <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  {t.m4aTitle}
                </div>
                <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5">
                  M4A / AAC Original
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  High Fidelity
                </div>
              </button>

              {/* Additional extracted audio streams */}
              {audioFormats.map((afmt) => {
                const isSelected = selectedFormatId === afmt.format_id && selectedIsAudio;
                return (
                  <button
                    key={afmt.format_id}
                    type="button"
                    onClick={() => handleSelectFormat(afmt.format_id, true, afmt.format_note || afmt.ext.toUpperCase())}
                    className={`relative p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500 dark:border-blue-500 ring-2 ring-blue-500/20"
                        : "bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    {isSelected && (
                      <CheckCircle2 className="absolute top-2.5 right-2.5 w-4 h-4 text-blue-600 dark:text-blue-400" />
                    )}
                    <div className="font-bold text-sm text-slate-900 dark:text-slate-100 uppercase">
                      {afmt.ext} {afmt.abr ? `(${Math.round(afmt.abr)}k)` : ""}
                    </div>
                    <div className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-0.5 truncate">
                      {afmt.format_note || "Audio Only"}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      {afmt.filesize_approx ? formatBytes(afmt.filesize_approx) : t.estSizeAuto}
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
