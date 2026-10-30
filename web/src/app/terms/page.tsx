"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Language, translations } from "@/lib/i18n";
import {
  getStoredLang,
  setStoredLang,
  getStoredTheme,
  setStoredTheme,
  getStoredHistory,
} from "@/lib/storage";
import { ShieldCheck, ArrowLeft, CheckCircle2, AlertTriangle, FileText } from "lucide-react";

export default function TermsPage() {
  const [lang, setLang] = useState<Language>("bn");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setLang(getStoredLang());
    const t = getStoredTheme();
    setTheme(t);
    setStoredTheme(t);
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

  const isEn = lang === "en";

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#080d1a] text-slate-900 dark:text-slate-100 transition-colors">
      <Header
        lang={lang}
        onToggleLang={handleToggleLang}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        historyCount={getStoredHistory().length}
        onOpenHistory={() => {}}
        backendHealthy={true}
      />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold text-blue-600 dark:text-blue-400 hover:underline mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{isEn ? "Back to Downloader" : "ডাউনলোডারে ফিরে যান"}</span>
        </Link>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-10 shadow-sm space-y-8">
          {/* Header */}
          <div className="border-b border-slate-200 dark:border-slate-800 pb-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
                  {isEn ? "Terms of Service" : "ব্যবহারের নিয়মাবলী ও শর্তসমূহ"}
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {isEn ? "Last updated: October 2026 • Effective immediately" : "সর্বশেষ আপডেট: অক্টোবর ২০২৬ • অবিলম্বে কার্যকর"}
                </p>
              </div>
            </div>
          </div>

          {/* Prominent Legal Notice */}
          <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 text-sm flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
            <div>
              <p className="font-bold">
                {isEn ? "Legal Affirmation Notice" : "আইনি ব্যবহার সংক্রান্ত বিশেষ নির্দেশনা"}
              </p>
              <p className="text-xs sm:text-sm mt-1 opacity-90 leading-relaxed">
                {isEn
                  ? "You agree to use AnyStream only to download public media that you own, have express permission from the copyright owner to download, or that is provided under open Creative Commons / Public Domain licenses."
                  : "AnyStream ব্যবহার করার মাধ্যমে আপনি অঙ্গীকার করছেন যে, আপনি শুধুমাত্র সেই সকল ভিডিও বা অডিও ডাউনলোড করবেন যার মালিকানা আপনার রয়েছে, স্বত্বাধিকারীর লিখিত অনুমতি রয়েছে অথবা যা ক্রিয়েটিভ কমন্স / পাবলিক ডোমেইন লাইসেন্সপ্রাপ্ত।"}
              </p>
            </div>
          </div>

          {/* Section 1: Permitted Use */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span>{isEn ? "1. Permitted and Lawful Use" : "১. অনুমোদিত ও বৈধ ব্যবহার"}</span>
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {isEn
                ? "AnyStream is designed as a software utility facilitating personal offline viewing and content accessibility. You may use this service exclusively for legitimate purposes, including personal archives, educational study, or fair use commentaries authorized under applicable intellectual property laws."
                : "AnyStream মূলত ব্যক্তিগত অফলাইন দেখার সুবিধার্থে নির্মিত একটি সফটওয়্যার ইউটিলিটি। আপনি শুধুমাত্র ব্যক্তিগত সংরক্ষণ, শিক্ষামূলক পড়াশোনা বা ন্যায্য ব্যবহার (Fair Use) সংক্রান্ত উদ্দেশ্যে এটি ব্যবহার করতে পারবেন।"}
            </p>
          </div>

          {/* Section 2: Prohibited Conduct */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-rose-500" />
              <span>{isEn ? "2. Prohibited Conduct" : "২. নিষিদ্ধ কার্যক্রম"}</span>
            </h2>
            <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-2 list-disc list-inside leading-relaxed">
              <li>
                {isEn
                  ? "Attempting to bypass Digital Rights Management (DRM) or encryption mechanisms."
                  : "কোনো প্রকার ডিজিটাল রাইটস ম্যানেজমেন্ট (DRM) বা এনক্রিপশন সিস্টেম বাইপাস করার চেষ্টা করা।"}
              </li>
              <li>
                {isEn
                  ? "Commercial resale, redistribution, or broadcast of downloaded third-party media."
                  : "ডাউনলোডকৃত থার্ড-পার্টি মিডিয়া ফাইল বাণিজ্যিক উদ্দেশ্যে বিক্রয় বা পুনরায় সম্প্রচার করা।"}
              </li>
              <li>
                {isEn
                  ? "Automated scraping, denial-of-service attacks, or flooding the extraction infrastructure."
                  : "অটোমেটেড স্ক্র্যাপিং, বট চালানো বা সার্ভার ডাউন করার লক্ষ্যে অতিরিক্ত রিকোয়েস্ট পাঠানো।"}
              </li>
              <li>
                {isEn
                  ? "Downloading material that violates criminal laws or intellectual property rights."
                  : "মেধাস্বত্ব বা প্রচলিত আইন লঙ্ঘনকারী যেকোনো কনটেন্ট ডাউনলোড করা।"}
              </li>
            </ul>
          </div>

          {/* Section 3: Data Retention & Storage */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {isEn ? "3. Platform Role & File Retention" : "৩. প্ল্যাটফর্মের ভূমিকা ও ফাইল সংরক্ষণ নীতি"}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {isEn
                ? "AnyStream does not operate a permanent media library or content hosting platform. Downloaded files reside in transient local storage only for the duration required to allow the user to save the file. All cached files are automatically and irreversibly purged after thirty (30) minutes by our automated cleanup janitor."
                : "AnyStream কোনো স্থায়ী মিডিয়া হোস্টিং প্ল্যাটফর্ম নয়। সাময়িকভাবে কনভার্ট করা ফাইল শুধুমাত্র ব্যবহারকারীর কাছে হস্তান্তরের সুবিধার্থে সর্বোচ্চ ৩০ মিনিট ক্যাশে সংরক্ষিত থাকে। এরপর স্বয়ংক্রিয় ক্লিনআপ সার্ভিসের মাধ্যমে স্থায়ীভাবে মুছে ফেলা হয়।"}
            </p>
          </div>

          {/* Section 4: DMCA Notice Link */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                {isEn ? "Are you a copyright holder?" : "আপনি কি কোনো কন্টেন্টের স্বত্বাধিকারী?"}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {isEn
                  ? "Submit a takedown notice to immediately block unauthorized downloads of your URLs."
                  : "আপনার কন্টেন্টের অননুমোদিত ডাউনলোড বন্ধ করতে অবিলম্বে DMCA নোটিশ জমা দিন।"}
              </p>
            </div>
            <Link
              href="/dmca"
              className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-colors shrink-0"
            >
              {isEn ? "DMCA Takedown Form" : "DMCA ফর্ম পূরণ করুন"}
            </Link>
          </div>
        </div>
      </main>

      <Footer lang={lang} />
    </div>
  );
}

