"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import type { Stats, Activity, Repo, CurrentUser } from "@/lib/types";
import { getDashboard, getInstallUrl } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { RepoList } from "@/components/RepoList";
import { GroupedActivityTable } from "@/components/GroupedActivityTable";
import {
  DASHBOARD_REFRESH_INTERVAL_MS,
  isDashboardDataStale,
  shouldRefreshDashboardOnMount,
} from "@/lib/dashboard-refresh";

interface LiveDashboardProps {
  currentUser: CurrentUser | null;
  initialStats: Stats | null;
  initialActivities: Activity[];
  initialRepos: Repo[];
}

export function LiveDashboard({ currentUser, initialStats, initialActivities, initialRepos }: LiveDashboardProps) {
  const [stats, setStats] = useState<Stats | null>(initialStats);
  const [activities, setActivities] = useState<Activity[]>(initialActivities);
  const [repos, setRepos] = useState<Repo[]>(initialRepos);
  const [installing, setInstalling] = useState(false);
  const hasInitialData = Boolean(initialStats) || initialActivities.length > 0 || initialRepos.length > 0;
  const lastLoadedAtRef = useRef(Date.now());
  const refreshInFlightRef = useRef(false);

  const refresh = useCallback(async () => {
    if (refreshInFlightRef.current) {
      return;
    }
    refreshInFlightRef.current = true;
    try {
      const data = await getDashboard();
      if (!data) return;
      if (data.stats) setStats(data.stats);
      setActivities(data.activities);
      setRepos(data.repos);
      lastLoadedAtRef.current = Date.now();
    } finally {
      refreshInFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (
      shouldRefreshDashboardOnMount({
        hasInitialData,
        lastLoadedAt: lastLoadedAtRef.current,
      })
    ) {
      void refresh();
    }

    const tick = () => {
      if (document.visibilityState !== "visible") {
        return;
      }
      if (
        isDashboardDataStale({
          hasInitialData,
          lastLoadedAt: lastLoadedAtRef.current,
        })
      ) {
        void refresh();
      }
    };

    const interval = window.setInterval(tick, DASHBOARD_REFRESH_INTERVAL_MS);
    const onVisibilityChange = () => tick();
    const onFocus = () => tick();

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("focus", onFocus);
    };
  }, [hasInitialData, refresh]);

  const displayActivities = stats?.recent_activities ?? activities;

  const handleInstallApp = useCallback(async () => {
    setInstalling(true);
    const url = await getInstallUrl();
    setInstalling(false);
    if (url) {
      window.location.href = url;
    }
  }, []);

  return (
    <>
      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Repos Watched"
            value={stats.repos.watched}
            icon="📦"
          />
          <StatCard
            label="Total Activities"
            value={stats.activities.total}
            icon="⚡"
          />
          <StatCard
            label="Completed"
            value={stats.activities.by_status.done ?? 0}
            icon="✅"
            accent="text-emerald-400"
          />
          <StatCard
            label="Total Cost"
            value={`$${stats.cost_usd.toFixed(2)}`}
            icon="💰"
            accent="text-amber-400"
          />
        </div>
      )}

      {currentUser && (
        <section className="glass rounded-xl p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {currentUser.avatar_url ? (
                <img
                  src={currentUser.avatar_url}
                  alt={currentUser.github_login}
                  className="h-11 w-11 rounded-full border border-white/10 object-cover"
                />
              ) : (
                <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sm font-semibold text-white">
                  {currentUser.github_login.slice(0, 1).toUpperCase()}
                </div>
              )}
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Signed In</p>
                <p className="mt-1 text-sm font-medium text-white">{currentUser.github_login}</p>
                {currentUser.github_email && <p className="text-xs text-gray-500">{currentUser.github_email}</p>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-[0.22em] text-gray-500">Usage</p>
              <p className="mt-1 text-sm font-medium text-white">
                {currentUser.is_whitelisted
                  ? "Unlimited access"
                  : `${currentUser.activity_quota_remaining ?? 0} / ${currentUser.activity_quota_limit} activities left`}
              </p>
              <p className="text-xs text-gray-500">
                {currentUser.is_whitelisted
                  ? "This account is on the allowlist."
                  : `${currentUser.activity_quota_used} activities already consumed.`}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Watched Repositories — above activities */}
      <section className="glass rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Watched Repositories
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-600">{repos.length} repos</span>
            <button
              onClick={handleInstallApp}
              disabled={installing}
              className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-[11px] font-medium text-cyan-200 transition hover:bg-cyan-400/20 disabled:opacity-50"
            >
              {installing ? "Opening…" : "Install App"}
            </button>
          </div>
        </div>
        <RepoList repos={repos} />
      </section>

      {/* Recent Activities — grouped by repo */}
      <section className="glass rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            Recent Activities
          </h2>
          <span className="text-xs text-gray-600">
            {displayActivities.length} entries
          </span>
        </div>
        <GroupedActivityTable activities={displayActivities} repos={repos} />
      </section>
    </>
  );
}
