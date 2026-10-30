"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Language } from "@/lib/i18n";
import {
  getStoredLang,
  setStoredLang,
  getStoredTheme,
  setStoredTheme,
  getStoredHistory,
} from "@/lib/storage";
import { Lock, ArrowLeft, ShieldCheck, Database, HardDrive, Cookie } from "lucide-react";

export default function PrivacyPage() {
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
              <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
                <Lock className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
                  {isEn ? "Privacy Policy" : "গোপনীয়তা ও ডেটা সুরক্ষা নীতি"}
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {isEn ? "Zero-knowledge architecture • Privacy by design" : "জিরো-ট্র্যাকিং আর্কিটেকচার • আপনার গোপনীয়তা অক্ষুণ্ণ"}
                </p>
              </div>
            </div>
          </div>

          {/* Core Privacy Pillars Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30">
              <HardDrive className="w-5 h-5 text-blue-500 mb-2" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                {isEn ? "Local Storage Only" : "শুধুমাত্র লোকাল হিস্ট্রি"}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {isEn
                  ? "Download history is saved only inside your personal browser localStorage."
                  : "আপনার ডাউনলোড রেকর্ড শুধুমাত্র আপনার ব্রাউজারের লোকাল স্টোরেজে থাকে।"}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30">
              <ShieldCheck className="w-5 h-5 text-emerald-500 mb-2" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                {isEn ? "Salted IP Hashing" : "সল্টেড আইপি হ্যাশিং"}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {isEn
                  ? "IP addresses are irreversible one-way hashed with cryptographical salts."
                  : "রেট লিমিটের জন্য আইপি অ্যাড্রেস ক্রিপ্টোগ্রাফিক হ্যাশ হিসেবে ব্যবহৃত হয়।"}
              </p>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30">
              <Cookie className="w-5 h-5 text-purple-500 mb-2" />
              <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                {isEn ? "No Tracking Cookies" : "কোনো ট্র্যাকিং কুকি নেই"}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {isEn
                  ? "We never use third-party ad networks, telemetry trackers, or profiling cookies."
                  : "আমরা কোনো বিজ্ঞাপন নেটওয়ার্ক বা ট্র্যাকিং কুকি ব্যবহার করি না।"}
              </p>
            </div>
          </div>

          {/* Section 1: Data Collection */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-500" />
              <span>{isEn ? "1. What We Collect and Why" : "১. আমরা কী তথ্য সংগ্রহ করি এবং কেন"}</span>
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {isEn
                ? "AnyStream does not require user accounts, email addresses, passwords, or telephone numbers to download media. To prevent abuse and protect infrastructure from automated denial-of-service floods, our API computes a salted SHA-256 digest of your IP address. This hash is maintained temporarily in volatile Redis memory solely to enforce rate quotas."
                : "AnyStream ব্যবহার করার জন্য কোনো অ্যাকাউন্ট খোলা, ইমেইল বা ফোন নম্বর দেওয়ার প্রয়োজন নেই। স্প্যাম ও বট আক্রমণ থেকে সিস্টেম সুরক্ষিত রাখতে আপনার আইপি অ্যাড্রেসের একটি সল্টেড SHA-256 হ্যাশ তৈরি করে মেমরিতে সাময়িকভাবে রেট লিমিটের হিসাব রাখা হয়।"}
            </p>
          </div>

          {/* Section 2: Storage Lifespan */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {isEn ? "2. Media Cache & Automatic Pruning" : "২. মিডিয়া ক্যাশ ও স্বয়ংক্রিয়ভাবে মুছে ফেলা"}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {isEn
                ? "Media files extracted during download jobs are kept in an isolated storage directory. Every file is strictly subject to a 30-minute expiration window. Our background Celery Beat Janitor runs every 5 minutes to securely delete all expired files and directories from the disk."
                : "ডাউনলোড চলাকালীন ফাইলগুলো সাময়িকভাবে একটি আইসোলেটেড স্টোরেজে জমা থাকে। প্রতিটি ফাইলের মেয়াদ সর্বোচ্চ ৩০ মিনিট। আমাদের স্বয়ংক্রিয় ব্যাকগ্রাউন্ড ক্লিনার সার্ভিস প্রতি ৫ মিনিট পর পর মেয়াদোত্তীর্ণ ফাইলগুলো ডিস্ক থেকে সম্পূর্ণরূপে ডিলিট করে দেয়।"}
            </p>
          </div>

          {/* Section 3: User Rights */}
          <div className="space-y-3">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {isEn ? "3. Your Privacy Controls" : "৩. ব্যবহারকারীর নিয়ন্ত্রণ"}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {isEn
                ? "You maintain full sovereignty over your data. You may clear your local download history at any time by clicking the trash icon inside the History drawer on the home page or by clearing your browser cache."
                : "আপনার তথ্যের ওপর আপনার পূর্ণ নিয়ন্ত্রণ রয়েছে। হোমপেজের হিস্ট্রি ড্রয়ারের ডিলিট বাটন চেপে অথবা ব্রাউজারের হিস্ট্রি ক্লিয়ার করে আপনি যেকোনো সময় আপনার ডিভাইসের সমস্ত রেকর্ড মুছে ফেলতে পারেন।"}
            </p>
          </div>
        </div>
      </main>

      <Footer lang={lang} />
    </div>
  );
}

