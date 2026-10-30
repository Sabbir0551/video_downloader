"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/i18n";
import { Search, Clipboard, X, Loader2, Sparkles } from "lucide-react";

interface UrlInputProps {
  lang: Language;
  onSearch: (url: string) => void;
  isLoading: boolean;
  initialUrl?: string;
}

export function UrlInput({ lang, onSearch, isLoading, initialUrl = "" }: UrlInputProps) {
  const [url, setUrl] = useState(initialUrl);
  const [validationError, setValidationError] = useState<string | null>(null);
  const t = translations[lang];

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
        setValidationError(null);
      }
    } catch {
      // Clipboard permission denied or unsupported
    }
  };

  const handleClear = () => {
    setUrl("");
    setValidationError(null);
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = url.trim();
    if (!clean) {
      setValidationError(t.emptyUrlError);
      return;
    }

    try {
      const parsed = new URL(clean);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        setValidationError(t.invalidUrlError);
        return;
      }
    } catch {
      setValidationError(t.invalidUrlError);
      return;
    }

    setValidationError(null);
    onSearch(clean);
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center shadow-lg shadow-blue-500/5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus-within:border-blue-500 dark:focus-within:border-blue-500 transition-all p-1.5 sm:p-2">
          {/* Input field */}
          <div className="relative flex-1 flex items-center">
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (validationError) setValidationError(null);
              }}
              placeholder={t.urlPlaceholder}
              disabled={isLoading}
              className="w-full bg-transparent px-3 sm:px-4 py-2.5 sm:py-3 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 text-sm sm:text-base outline-none disabled:opacity-50"
              aria-label={t.urlPlaceholder}
            />

            {/* Clear Button */}
            {url && !isLoading && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-full transition-colors mr-1 cursor-pointer"
                title={t.clear}
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Paste Button */}
            {!url && !isLoading && (
              <button
                type="button"
                onClick={handlePaste}
                className="hidden sm:flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 rounded-lg transition-colors mr-2 cursor-pointer"
                title={t.paste}
              >
                <Clipboard className="w-3.5 h-3.5" />
                <span>{t.paste}</span>
              </button>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-5 sm:px-6 py-2.5 sm:py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-sm sm:text-base shadow-md shadow-blue-500/25 transition-all disabled:opacity-60 disabled:cursor-not-allowed shrink-0 cursor-pointer"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="hidden sm:inline">{t.searching}</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>{t.search}</span>
              </>
            )}
          </button>
        </div>

        {/* Validation warning */}
        {validationError && (
          <p className="mt-2 text-xs sm:text-sm text-rose-500 font-medium px-2">
            {validationError}
          </p>
        )}
      </form>

      {/* Helpful hint chips */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-amber-500" />
          {t.supportedPlatforms}
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
          YouTube
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
          Facebook
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
          TikTok
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
          Vimeo
        </span>
        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
          X / Twitter
        </span>
      </div>
    </div>
  );
}
