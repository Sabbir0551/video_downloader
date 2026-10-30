"use client";

import React from "react";
import Link from "next/link";
import { Language, translations } from "@/lib/i18n";
import { Moon, Sun, Globe, History } from "lucide-react";

interface HeaderProps {
  lang: Language;
  onToggleLang: () => void;
  theme: "dark" | "light";
  onToggleTheme: () => void;
  historyCount: number;
  onOpenHistory: () => void;
  backendHealthy: boolean | null;
}

export function Header({
  lang,
  onToggleLang,
  theme,
  onToggleTheme,
  historyCount,
  onOpenHistory,
  backendHealthy,
}: HeaderProps) {
  const t = translations[lang];

  return (
    <header className="w-full border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur sticky top-0 z-40 transition-colors">
      <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo and Brand */}
        <Link href="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xl shadow-md shadow-blue-500/20">
            A
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 dark:from-blue-400 dark:via-indigo-300 dark:to-purple-400 bg-clip-text text-transparent">
                AnyStream
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                v1.0
              </span>
            </div>
          </div>
        </Link>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Health indicator */}
          <div
            className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
              backendHealthy === true
                ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800/60"
                : backendHealthy === false
                ? "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800/60"
                : "bg-slate-100 dark:bg-slate-800 text-slate-500 border-slate-200 dark:border-slate-700"
            }`}
            title={backendHealthy ? t.apiOnline : t.apiConnecting}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendHealthy === true
                  ? "bg-emerald-500 animate-pulse"
                  : backendHealthy === false
                  ? "bg-rose-500"
                  : "bg-amber-400 animate-ping"
              }`}
            />
            <span className="text-[11px] font-semibold">
              {backendHealthy === true ? t.apiOnline : backendHealthy === false ? t.apiOffline : t.apiConnecting}
            </span>
          </div>

          {/* Download History Button */}
          <button
            onClick={onOpenHistory}
            className="relative p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title={t.historyTitle}
            aria-label={t.historyTitle}
          >
            <History className="w-5 h-5" />
            {historyCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-blue-600 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                {historyCount > 9 ? "9+" : historyCount}
              </span>
            )}
          </button>

          {/* Language Switcher */}
          <button
            onClick={onToggleLang}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors"
            title="Switch Language / ভাষা পরিবর্তন করুন"
          >
            <Globe className="w-4 h-4 text-blue-500" />
            <span>{lang === "en" ? "বাং" : "EN"}</span>
          </button>

          {/* Theme Switcher */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title={theme === "dark" ? t.themeLight : t.themeDark}
            aria-label="Toggle Theme"
          >
            {theme === "dark" ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-slate-600" />}
          </button>
        </div>
      </div>
    </header>
  );
}
