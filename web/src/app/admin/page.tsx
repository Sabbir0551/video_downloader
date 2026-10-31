"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  ShieldAlert,
  Key,
  CheckCircle,
  XCircle,
  Clock,
  ArrowLeft,
  RefreshCw,
  ExternalLink,
  Lock,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface TakedownItem {
  case_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  requester_name: string;
  requester_email: string;
  infringing_url: string;
  copyrighted_work_url: string;
  statement?: string | null;
  channel_id?: string | null;
  created_at: string;
}

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [takedowns, setTakedowns] = useState<TakedownItem[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Load stored admin key from sessionStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("anystream_admin_key");
      if (stored) {
        setAdminKey(stored);
        setIsAuthenticated(true);
      }
    }
  }, []);

  const fetchTakedowns = useCallback(async (key: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const url = `${apiClient.getBaseUrl()}/api/v1/admin/takedowns`;
      const res = await fetch(url, {
        headers: { "X-Admin-Key": key },
      });
      if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
          throw new Error("Invalid or unauthorized Admin API Key.");
        }
        throw new Error(`Failed to load claims (HTTP ${res.status})`);
      }
      const data = await res.json();
      setTakedowns(data.takedowns || []);
      setIsAuthenticated(true);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("anystream_admin_key", key);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Authentication error");
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && adminKey) {
      fetchTakedowns(adminKey);
    }
  }, [isAuthenticated, adminKey, fetchTakedowns]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey.trim()) return;
    fetchTakedowns(adminKey.trim());
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setAdminKey("");
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("anystream_admin_key");
    }
  };

  const handleReview = async (caseId: string, action: "APPROVED" | "REJECTED") => {
    setIsLoading(true);
    setActionSuccess(null);
    setErrorMessage(null);
    try {
      const url = `${apiClient.getBaseUrl()}/api/v1/admin/takedowns/${caseId}/review`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Key": adminKey,
        },
        body: JSON.stringify({ action }),
      });
      if (!res.ok) {
        throw new Error(`Action failed (HTTP ${res.status})`);
      }
      const data = await res.json();
      setActionSuccess(`Case #${caseId.slice(0, 8)} updated to ${action}: ${data.message}`);
      await fetchTakedowns(adminKey);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Review submission failed");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredItems = takedowns.filter((item) => {
    if (filter === "ALL") return true;
    return item.status === filter;
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#080d1a] text-slate-900 dark:text-slate-100 p-4 sm:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-xl sm:text-2xl font-black flex items-center gap-2">
                <ShieldCheck className="w-6 h-6 text-indigo-500" />
                AnyStream DMCA & Takedown Console
              </h1>
              <p className="text-xs sm:text-sm text-slate-500">
                Administrative copyright claim verification and blacklisting dashboard
              </p>
            </div>
          </div>

          {isAuthenticated && (
            <button
              onClick={handleLogout}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-900/40 border border-rose-200 dark:border-rose-900/60 transition-colors"
            >
              Sign Out
            </button>
          )}
        </div>

        {/* Authentication Modal / Form */}
        {!isAuthenticated ? (
          <div className="max-w-md mx-auto mt-16 p-6 sm:p-8 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl">
            <div className="flex justify-center mb-4">
              <div className="p-3 bg-indigo-50 dark:bg-indigo-950/60 rounded-2xl">
                <Lock className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
              </div>
            </div>
            <h2 className="text-lg font-bold text-center mb-2">Restricted Access</h2>
            <p className="text-xs text-center text-slate-500 dark:text-slate-400 mb-6">
              Enter your server <code>ADMIN_API_KEY</code> to review pending DMCA claims.
            </p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                  Admin API Key
                </label>
                <div className="relative">
                  <Key className="w-4 h-4 absolute left-3 top-3.5 text-slate-400" />
                  <input
                    type="password"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    placeholder="Enter secret key..."
                    className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
              </div>

              {errorMessage && (
                <p className="text-xs text-rose-500 font-medium">{errorMessage}</p>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition-colors shadow-md disabled:opacity-50 cursor-pointer"
              >
                {isLoading ? "Verifying..." : "Authorize Access"}
              </button>
            </form>
          </div>
        ) : (
          /* Authenticated Console */
          <div className="mt-8 space-y-6">
            {/* Action Banners */}
            {actionSuccess && (
              <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs font-medium flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{actionSuccess}</span>
              </div>
            )}

            {errorMessage && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs font-medium flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Filter Tabs and Refresh */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl">
                {["ALL", "PENDING", "APPROVED", "REJECTED"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFilter(st)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      filter === st
                        ? "bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-300 shadow-xs"
                        : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <button
                onClick={() => fetchTakedowns(adminKey)}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
                <span>Refresh</span>
              </button>
            </div>

            {/* Takedown Records List */}
            {filteredItems.length === 0 ? (
              <div className="text-center py-12 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
                <Clock className="w-8 h-8 mx-auto text-slate-400 mb-2" />
                <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                  No takedown requests found.
                </p>
                <p className="text-xs text-slate-400">
                  Filtered by: {filter}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredItems.map((item) => (
                  <div
                    key={item.case_id}
                    className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                            item.status === "APPROVED"
                              ? "bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300"
                              : item.status === "PENDING"
                              ? "bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300"
                              : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300"
                          }`}
                        >
                          {item.status}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">
                          Case #{item.case_id}
                        </span>
                      </div>
                      <span className="text-xs text-slate-400">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="font-semibold text-slate-500">Requester: </span>
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          {item.requester_name} ({item.requester_email})
                        </span>
                      </div>
                      {item.channel_id && (
                        <div>
                          <span className="font-semibold text-slate-500">Target Channel/ID: </span>
                          <span className="font-mono text-slate-800 dark:text-slate-200">
                            {item.channel_id}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="space-y-1 text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-500">Target Infringing URL:</span>
                        <a
                          href={item.infringing_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:underline flex items-center gap-1 truncate max-w-md"
                        >
                          {item.infringing_url}
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-500">Original Source Work:</span>
                        <a
                          href={item.copyrighted_work_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-500 hover:underline flex items-center gap-1 truncate max-w-md"
                        >
                          {item.copyrighted_work_url}
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      </div>
                    </div>

                    {item.statement && (
                      <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl text-xs text-slate-600 dark:text-slate-300 border border-slate-100 dark:border-slate-800">
                        <span className="font-semibold block mb-1 text-slate-700 dark:text-slate-200">
                          Declaration of Claim:
                        </span>
                        {item.statement}
                      </div>
                    )}

                    {/* Review Decision Buttons */}
                    {item.status === "PENDING" && (
                      <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-3">
                        <button
                          onClick={() => handleReview(item.case_id, "REJECTED")}
                          disabled={isLoading}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors cursor-pointer"
                        >
                          <XCircle className="w-3.5 h-3.5 text-slate-500" />
                          <span>Reject Claim</span>
                        </button>

                        <button
                          onClick={() => handleReview(item.case_id, "APPROVED")}
                          disabled={isLoading}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition-colors shadow-xs cursor-pointer"
                        >
                          <ShieldAlert className="w-3.5 h-3.5" />
                          <span>Approve & Block Media</span>
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
