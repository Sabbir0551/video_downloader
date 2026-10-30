"use client";

import React from "react";
import Link from "next/link";
import { Language, translations } from "@/lib/i18n";
import { ShieldCheck } from "lucide-react";

interface FooterProps {
  lang: Language;
}

export function Footer({ lang }: FooterProps) {
  const t = translations[lang];

  return (
    <footer className="w-full mt-auto border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 backdrop-blur-xs py-8 px-4 transition-colors">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Prominent Legal Trust Notice (Required in Step 5 & prompt guidelines) */}
        <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/60 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">{t.legalNotice}</p>
            <p className="text-[11px] opacity-80">{t.legalDisclaimer}</p>
          </div>
        </div>

        {/* Navigation & Credits */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          <p>© {new Date().getFullYear()} AnyStream Platform • Powered by Next.js & yt-dlp Core</p>

          <div className="flex flex-wrap items-center gap-4 sm:gap-5">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              OpenAPI Swagger
            </a>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <Link
              href="/terms"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {t.terms}
            </Link>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <Link
              href="/privacy"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {t.privacy}
            </Link>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <Link
              href="/dmca"
              className="text-rose-600 dark:text-rose-400 hover:underline font-semibold transition-colors"
            >
              {t.dmca}
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
