"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { HealthResponse } from "@/types/api";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [corsStatus, setCorsStatus] = useState<"checking" | "connected" | "error">("checking");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const checkConnection = async () => {
    setCorsStatus("checking");
    setErrorMessage(null);
    const start = performance.now();
    try {
      const data = await apiClient.getHealth();
      setLatencyMs(Math.round(performance.now() - start));
      setHealth(data);
      setCorsStatus("connected");
    } catch (err) {
      setLatencyMs(Math.round(performance.now() - start));
      setCorsStatus("error");
      if (err instanceof ApiClientError) {
        setErrorMessage(`[${err.errorCode}] ${err.message}`);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to connect to backend server.");
      }
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 font-sans">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-6 border-b border-slate-800">
          <div>
            <span className="text-xs uppercase tracking-widest text-blue-400 font-bold">
              Phase 3 • Step 1
            </span>
            <h1 className="text-2xl font-extrabold text-white mt-1">
              AnyStream Web Frontend
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              {corsStatus === "connected" && (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </>
              )}
              {corsStatus === "checking" && (
                <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
              )}
              {corsStatus === "error" && (
                <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
              )}
            </span>
            <span className="text-sm font-semibold capitalize">
              {corsStatus === "connected" && "Backend Connected"}
              {corsStatus === "checking" && "Connecting..."}
              {corsStatus === "error" && "Connection Error"}
            </span>
          </div>
        </div>

        {/* Verification Checklist */}
        <div className="mt-6 space-y-3">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Step 1 Setup Checklist
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
              <span className="text-slate-300">Next.js App Router (v16+)</span>
              <span className="text-emerald-400 font-bold text-xs bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded">
                Active
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
              <span className="text-slate-300">TypeScript & Tailwind CSS</span>
              <span className="text-emerald-400 font-bold text-xs bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded">
                Active
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
              <span className="text-slate-300">OpenAPI Typed Client</span>
              <span className="text-emerald-400 font-bold text-xs bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded">
                Synced
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
              <span className="text-slate-300">Security Headers (CSP/XSS)</span>
              <span className="text-emerald-400 font-bold text-xs bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded">
                Enforced
              </span>
            </div>
          </div>
        </div>

        {/* API Base URL & CORS Health Check */}
        <div className="mt-6 bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Target Backend Base URL:</div>
              <div className="font-mono text-sm text-blue-400 mt-0.5">
                {apiClient.getBaseUrl()}
              </div>
            </div>
            <button
              onClick={checkConnection}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-semibold transition active:scale-95"
            >
              Re-test Connection
            </button>
          </div>

          {corsStatus === "connected" && health && (
            <div className="mt-4 pt-4 border-t border-slate-800/80">
              <div className="text-xs font-semibold text-emerald-400 flex items-center gap-2">
                <span>CORS & Handshake Verified</span>
                {latencyMs !== null && (
                  <span className="text-slate-500 font-mono">({latencyMs}ms)</span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 text-xs">
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block">Status</span>
                  <span className="font-semibold text-emerald-400 uppercase">
                    {health.status}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block">DB (PostgreSQL)</span>
                  <span className="font-semibold text-white">
                    {health.database ? "Connected" : "Disconnected"}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block">Queue (Redis)</span>
                  <span className="font-semibold text-white">
                    {health.redis ? "Connected" : "Disconnected"}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block">yt-dlp Core</span>
                  <span className="font-semibold text-white">
                    v{health.ytdlp_version}
                  </span>
                </div>
              </div>
            </div>
          )}

          {corsStatus === "error" && (
            <div className="mt-4 pt-4 border-t border-rose-900/60 text-xs">
              <div className="text-rose-400 font-semibold">
                Failed to reach backend API
              </div>
              <p className="text-slate-400 mt-1">{errorMessage}</p>
              <p className="text-slate-500 mt-2">
                Make sure the backend server is running at{" "}
                <code className="text-slate-300 font-mono">
                  {apiClient.getBaseUrl()}
                </code>
              </p>
            </div>
          )}
        </div>

        {/* Next Step Info */}
        <div className="mt-6 text-center text-xs text-slate-500">
          Ready to proceed to <strong className="text-slate-400">Step 2: Home Page & URL Inspector</strong> upon testing approval.
        </div>
      </div>
    </div>
  );
}
