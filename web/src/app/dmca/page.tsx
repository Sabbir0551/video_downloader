"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { Language } from "@/lib/i18n";
import {
  getStoredLang,
  setStoredLang,
  getStoredTheme,
  setStoredTheme,
  getStoredHistory,
} from "@/lib/storage";
import {
  Scale,
  ArrowLeft,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Send,
  FileCheck2,
} from "lucide-react";

export default function DmcaPage() {
  const [lang, setLang] = useState<Language>("bn");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Form State
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [originalUrl, setOriginalUrl] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [statement, setStatement] = useState("");
  const [declaration, setDeclaration] = useState(false);

  // Submission State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!declaration) {
      setErrorMessage(
        isEn
          ? "You must affirm the declaration of truth under penalty of perjury."
          : "আপনাকে অবশ্যই সত্যতা নিশ্চিতকরণ বাক্সে টিক চিহ্ন দিতে হবে।"
      );
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiClient.submitTakedown({
        requester_name: name.trim(),
        requester_email: email.trim(),
        copyrighted_work_url: originalUrl.trim(),
        infringing_url: targetUrl.trim(),
        statement: statement.trim() || null,
        declaration_truth: declaration,
      });

      setCaseId(response.case_id || response.reference_id || null);
      setSuccessMessage(response.message);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(
          isEn
            ? "Failed to submit takedown notice. Please try again."
            : "নোটিশ জমা দেওয়া সম্ভব হয়নি। অনুগ্রহ করে পুনরায় চেষ্টা করুন।"
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

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

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8 sm:py-12">
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
              <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400">
                <Scale className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
                  {isEn ? "DMCA Copyright Takedown Notice" : "কপিরাইট ও DMCA টেকডাউন নোটিশ"}
                </h1>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {isEn
                    ? "Digital Millennium Copyright Act (DMCA) & Legal Compliance"
                    : "ডিজিটাল রাইটস ও কপিরাইট লঙ্ঘন প্রতিরোধ সংক্রান্ত আইনি নোটিশ"}
                </p>
              </div>
            </div>
          </div>

          {/* Success State */}
          {caseId ? (
            <div className="p-6 rounded-2xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-200 space-y-4 animate-in fade-in">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <h3 className="font-bold text-lg">
                    {isEn ? "Takedown Notice Successfully Registered" : "টেকডাউন নোটিশ সফলভাবে নিবন্ধিত হয়েছে"}
                  </h3>
                  <p className="text-xs sm:text-sm opacity-90 mt-0.5">
                    {successMessage || (isEn ? "The target URL has been blocked from further downloads pending review." : "উক্ত URL থেকে সকল প্রকার ডাউনলোড তাৎক্ষণিকভাবে ব্লক করা হয়েছে।")}
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-white/70 dark:bg-slate-900/70 border border-emerald-200 dark:border-emerald-800 text-xs font-mono space-y-1">
                <div>Case Reference ID: <strong className="text-emerald-600 dark:text-emerald-400">{caseId}</strong></div>
                <div>Status: <span className="font-semibold">BLOCKED_PENDING_REVIEW</span></div>
                <div>Target URL: <span className="text-slate-600 dark:text-slate-400 break-all">{targetUrl}</span></div>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-300">
                {isEn
                  ? "A confirmation has been logged. Our compliance officer reviews all filings within 24 hours."
                  : "আমাদের কমপ্লায়েন্স টিম ২৪ ঘণ্টার মধ্যে নোটিশটি যাচাই করবে। প্রয়োজনে আপনার সাথে ইমেইলে যোগাযোগ করা হবে।"}
              </p>

              <button
                onClick={() => {
                  setCaseId(null);
                  setName("");
                  setEmail("");
                  setOriginalUrl("");
                  setTargetUrl("");
                  setStatement("");
                  setDeclaration(false);
                }}
                className="mt-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300 underline"
              >
                {isEn ? "Submit another notice" : "আরেকটি নোটিশ জমা দিন"}
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Notice Banner */}
              <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/60 dark:bg-rose-950/20 text-rose-800 dark:text-rose-300 text-xs sm:text-sm flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
                <div>
                  <p className="font-semibold">
                    {isEn
                      ? "Notice for Rights Holders & Authorized Agents"
                      : "স্বত্বাধিকারী ও অনুমোদিত প্রতিনিধিদের জন্য জরুরি তথ্য"}
                  </p>
                  <p className="text-xs mt-1 opacity-90 leading-relaxed">
                    {isEn
                      ? "If you believe your copyrighted content is accessible through our conversion tool without authorization, submit this form. Valid submissions immediately block extraction of the specified link."
                      : "আপনার কপিরাইটযুক্ত কোনো কন্টেন্ট যদি এই প্ল্যাটফর্মের মাধ্যমে অননুমোদিতভাবে ব্যবহৃত হয়ে থাকে, তবে নিচের ফর্মটি পূরণ করুন। নোটিশ জমা হওয়ার সাথে সাথেই উক্ত লিঙ্কটি ব্লক তালিকায় যুক্ত করা হবে।"}
                  </p>
                </div>
              </div>

              {/* Error Box */}
              {errorMessage && (
                <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Form Fields Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    {isEn ? "Full Legal Name *" : "আপনার পূর্ণ নাম *"}
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={isEn ? "e.g. Jane Doe" : "যেমন: মো: রফিকুল ইসলাম"}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-sm outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    {isEn ? "Official Email Address *" : "অফিসিয়াল ইমেইল অ্যাড্রেস *"}
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="legal@rights-holder.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-sm outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  {isEn ? "Original Work URL / Copyright Proof *" : "মূল ভিডিও বা কপিরাইট প্রমাণের লিঙ্ক *"}
                </label>
                <input
                  type="url"
                  required
                  value={originalUrl}
                  onChange={(e) => setOriginalUrl(e.target.value)}
                  placeholder="https://original-publisher.com/video/123"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-sm outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  {isEn ? "Infringing Media URL to Block *" : "ব্লক করার জন্য টার্গেট ভিডিও লিঙ্ক *"}
                </label>
                <input
                  type="url"
                  required
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-sm outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  {isEn ? "Statement / Additional Infringement Details" : "অতিরিক্ত বিবরণ / কপিরাইট দাবির বিবরণী"}
                </label>
                <textarea
                  rows={3}
                  value={statement}
                  onChange={(e) => setStatement(e.target.value)}
                  placeholder={
                    isEn
                      ? "Describe the copyrighted work and nature of unauthorized distribution..."
                      : "কপিরাইট লঙ্ঘন সংক্রান্ত প্রয়োজনীয় তথ্য লিখুন..."
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-sm outline-none focus:border-blue-500"
                />
              </div>

              {/* Perjury Affirmation Checkbox */}
              <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/30 flex items-start gap-3">
                <input
                  type="checkbox"
                  id="declaration"
                  checked={declaration}
                  onChange={(e) => setDeclaration(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <label htmlFor="declaration" className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed cursor-pointer">
                  {isEn ? (
                    <>
                      I state, <strong>under penalty of perjury</strong>, that I am the copyright owner or authorized agent, and that the information in this notice is accurate and submitted in good faith.
                    </>
                  ) : (
                    <>
                      আমি শপথপূর্বক ঘোষণা করছি যে, আমি উক্ত কন্টেন্টের প্রকৃত স্বত্বাধিকারী অথবা অনুমোদিত প্রতিনিধি এবং এই ফর্মে প্রদত্ত সকল তথ্য সম্পূর্ণ নির্ভুল ও সত্য।
                    </>
                  )}
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-700 hover:to-red-700 text-white font-bold text-sm sm:text-base shadow-lg shadow-rose-500/20 transition-all disabled:opacity-60 cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>{isEn ? "Registering Takedown..." : "নোটিশ জমা হচ্ছে..."}</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>{isEn ? "Submit Takedown Notice" : "নোটিশ জমা দিন"}</span>
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      </main>

      <Footer lang={lang} />
    </div>
  );
}

