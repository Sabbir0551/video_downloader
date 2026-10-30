"use client";

import React from "react";

export function MediaSkeleton() {
  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-sm animate-pulse transition-colors">
      <div className="flex flex-col sm:flex-row gap-5">
        {/* Thumbnail shimmer */}
        <div className="w-full sm:w-60 aspect-video rounded-xl bg-slate-200 dark:bg-slate-800 shrink-0" />

        {/* Details shimmer */}
        <div className="flex-1 space-y-3 py-1">
          <div className="h-5 bg-slate-200 dark:bg-slate-800 rounded-md w-4/5" />
          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-md w-1/2" />
          <div className="flex gap-2 pt-2">
            <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded-full w-20" />
            <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded-full w-24" />
          </div>
        </div>
      </div>

      {/* Quality Picker Shimmer */}
      <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800/80">
        <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-40 mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-slate-100 dark:bg-slate-800/60" />
          ))}
        </div>
      </div>
    </div>
  );
}

