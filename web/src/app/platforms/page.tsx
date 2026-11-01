"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { PlatformMetadata, PlatformsListResponse } from "@/types/api";

const TIER_LABELS: Record<string, { label: string; labelBn: string; color: string; desc: string }> = {
  all: { label: "All Platforms", labelBn: "সকল প্ল্যাটফর্ম", color: "bg-slate-800 text-white", desc: "All 100 scoped social platforms" },
  supported: { label: "Fully Supported", labelBn: "পূর্ণ সমর্থিত", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", desc: "Dedicated high-speed video/audio extraction up to 4K" },
  best_effort: { label: "Best Effort", labelBn: "সর্বোচ্চ প্রচেষ্টা", color: "bg-blue-500/20 text-blue-400 border-blue-500/30", desc: "Generic / embed / public direct media links" },
  unsupported_no_video: { label: "No Video / Chat", labelBn: "ভিডিওহীন / মেসেজিং", color: "bg-amber-500/20 text-amber-400 border-amber-500/30", desc: "Encrypted messaging, dating, or text Q&A without video" },
  login_or_paid: { label: "Login / Paywalled", labelBn: "লগইন বা পেইড", color: "bg-purple-500/20 text-purple-400 border-purple-500/30", desc: "Subscription paywall or login required (refused by policy)" },
  defunct: { label: "Defunct / Closed", labelBn: "বন্ধ হওয়া সাইট", color: "bg-rose-500/20 text-rose-400 border-rose-500/30", desc: "Permanently shut down or discontinued services" },
};

export default function PlatformsPage() {
  const [data, setData] = useState<PlatformsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function fetchPlatforms() {
      try {
        setLoading(true);
        const res = await apiClient.getPlatforms();
        setData(res);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load platforms registry.");
      } finally {
        setLoading(false);
      }
    }
    fetchPlatforms();
  }, []);

  const filteredPlatforms = useMemo(() => {
    if (!data) return [];
    return data.platforms.filter((p) => {
      const matchTier = selectedTier === "all" || p.tier === selectedTier;
      const matchSearch =
        !searchQuery ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.domains.some((d) => d.toLowerCase().includes(searchQuery.toLowerCase())) ||
        p.category.toLowerCase().includes(searchQuery.toLowerCase());
      return matchTier && matchSearch;
    });
  }, [data, selectedTier, searchQuery]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Header Navigation */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
          <Link
            href="/"
            className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            ← মূল ডাউনলোডার পেজে ফিরুন (Back to Downloader)
          </Link>
          <span className="text-xs bg-slate-800 text-slate-300 px-3 py-1 rounded-full border border-slate-700">
            100 Platforms Verified
          </span>
        </div>

        {/* Hero Title */}
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-3">
            সমর্থিত প্ল্যাটফর্ম তালিকা (Platform Support Matrix)
          </h1>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm sm:text-base">
            AnyStream ১০০টি সামাজিক যোগাযোগ মাধ্যমের জন্য সরাসরি এবং সুনির্দিষ্ট নীতি সমর্থন করে।
            পাবলিক কনটেন্ট সর্বোচ্চ কোয়ালিটিতে ডাউনলোড করা যায়।
          </p>
        </div>

        {/* Summary Badges */}
        {data && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-8">
            {Object.entries(data.tiers_summary).map(([tierKey, count]) => {
              const meta = TIER_LABELS[tierKey] || { label: tierKey, labelBn: tierKey, color: "bg-slate-800 text-white" };
              return (
                <button
                  key={tierKey}
                  onClick={() => setSelectedTier(selectedTier === tierKey ? "all" : tierKey)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    selectedTier === tierKey
                      ? "ring-2 ring-indigo-500 bg-slate-800 border-indigo-500"
                      : "bg-slate-900 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="text-2xl font-bold text-white">{count}</div>
                  <div className="text-xs font-medium text-slate-300 mt-1">{meta.labelBn}</div>
                  <div className="text-[11px] text-slate-400">{meta.label}</div>
                </button>
              );
            })}
          </div>
        )}

        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <input
            type="text"
            placeholder="প্ল্যাটফর্ম বা ডোমেইন খুঁজুন (Search by name or domain, e.g. youtube, tiktok, x.com)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
            {["all", "supported", "best_effort", "unsupported_no_video", "login_or_paid", "defunct"].map((tierKey) => (
              <button
                key={tierKey}
                onClick={() => setSelectedTier(tierKey)}
                className={`text-xs px-3 py-1.5 rounded-lg border whitespace-nowrap transition-colors ${
                  selectedTier === tierKey
                    ? "bg-indigo-600 border-indigo-500 text-white"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {TIER_LABELS[tierKey]?.labelBn || tierKey}
              </button>
            ))}
          </div>
        </div>

        {/* Loading / Error States */}
        {loading && (
          <div className="text-center py-16 text-slate-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-4" />
            <p>প্ল্যাটফর্ম তালিকা লোড হচ্ছে...</p>
          </div>
        )}

        {error && (
          <div className="bg-rose-950/40 border border-rose-800 text-rose-300 p-4 rounded-xl text-center mb-8">
            {error}
          </div>
        )}

        {/* Platforms Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredPlatforms.map((platform) => {
              const tierInfo = TIER_LABELS[platform.tier] || {
                label: platform.tier,
                labelBn: platform.tier,
                color: "bg-slate-800 text-slate-300",
              };
              return (
                <div
                  key={platform.id}
                  className="bg-slate-900 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-bold text-white text-base">{platform.name}</h3>
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${tierInfo.color}`}>
                        {tierInfo.labelBn}
                      </span>
                    </div>

                    {/* Domains */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      {platform.domains.slice(0, 3).map((dom) => (
                        <span key={dom} className="text-[11px] font-mono bg-slate-950 text-slate-400 px-2 py-0.5 rounded border border-slate-800">
                          {dom}
                        </span>
                      ))}
                      {platform.domains.length > 3 && (
                        <span className="text-[10px] text-slate-400 self-center">+{platform.domains.length - 3}</span>
                      )}
                    </div>

                    {/* Quality & Audio Capabilities */}
                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 mb-3 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                      <div>
                        <span className="text-slate-400">সর্বোচ্চ মান:</span>{" "}
                        <span className="text-slate-200 font-semibold">{platform.max_quality_expected.toUpperCase()}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">অডিও ডাউনলোড:</span>{" "}
                        <span className="text-slate-200 font-semibold">{platform.supports_audio_only ? "হ্যাঁ (Yes)" : "না (No)"}</span>
                      </div>
                    </div>

                    {/* Notes */}
                    {platform.notes && (
                      <p className="text-xs text-slate-400 leading-relaxed mb-3">
                        {platform.notes}
                      </p>
                    )}
                  </div>

                  {/* Footer metadata */}
                  <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="capitalize">{platform.category.replace("_", " ")}</span>
                    {platform.has_public_video ? (
                      <span className="text-emerald-400 flex items-center gap-1">● পাবলিক ভিডিও সমর্থিত</span>
                    ) : (
                      <span className="text-amber-400 flex items-center gap-1">○ ভিডিও নেই / প্রাইভেট</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Empty Search Result */}
        {!loading && !error && filteredPlatforms.length === 0 && (
          <div className="text-center py-16 text-slate-400 bg-slate-900 border border-slate-800 rounded-2xl">
            <p className="text-base font-medium mb-1">কোনো প্ল্যাটফর্ম খুঁজে পাওয়া যায়নি।</p>
            <p className="text-xs text-slate-400">অন্য কোনো বানান বা ডোমেইন দিয়ে আবার সার্চ করুন।</p>
          </div>
        )}
      </div>
    </div>
  );
}

