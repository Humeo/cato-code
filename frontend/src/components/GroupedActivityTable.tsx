"use client";

import { useState, useMemo } from "react";
import type { Activity, Repo } from "@/lib/types";
import { ActivityTable } from "@/components/ActivityTable";

interface GroupedActivityTableProps {
  activities: Activity[];
  repos: Repo[];
}

export function GroupedActivityTable({ activities, repos }: GroupedActivityTableProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // Build a lookup: repo_id -> display name
  const repoNames = useMemo(() => {
    const map: Record<string, string> = {};
    for (const r of repos) {
      map[r.id] = r.repo_url.replace("https://github.com/", "");
    }
    return map;
  }, [repos]);

  // Group activities by repo_id, preserving order of first appearance
  const groups = useMemo(() => {
    const map = new Map<string, Activity[]>();
    for (const a of activities) {
      const key = a.repo_id;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    }
    return Array.from(map.entries());
  }, [activities]);

  if (!activities.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-gray-600">
        <span className="text-2xl mb-2">📋</span>
        <p className="text-sm">No activities yet.</p>
      </div>
    );
  }

  // Single repo — no grouping needed
  if (groups.length === 1) {
    return <ActivityTable activities={activities} hideRepo />;
  }

  const toggle = (repoId: string) =>
    setCollapsed((prev) => ({ ...prev, [repoId]: !prev[repoId] }));

  return (
    <div className="space-y-3">
      {groups.map(([repoId, repoActivities]) => {
        const isCollapsed = !!collapsed[repoId];
        const name = repoNames[repoId] ?? repoId.substring(0, 12);
        const runningCount = repoActivities.filter(
          (a) => (a.pipeline_stage ?? a.status) === "running"
        ).length;

        return (
          <div key={repoId} className="rounded-lg border border-border-subtle/50 overflow-hidden">
            {/* Group header */}
            <button
              onClick={() => toggle(repoId)}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
            >
              <svg
                className={`w-3 h-3 text-gray-500 transition-transform ${
                  isCollapsed ? "" : "rotate-90"
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              <span className="text-xs text-gray-300 font-medium">{name}</span>
              <span className="text-xs text-gray-600 ml-auto">
                {repoActivities.length} {repoActivities.length === 1 ? "activity" : "activities"}
              </span>
              {runningCount > 0 && (
                <span className="flex items-center gap-1 text-xs text-blue-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                  {runningCount} running
                </span>
              )}
            </button>

            {/* Collapsible body */}
            {!isCollapsed && (
              <div className="border-t border-border-subtle/50 px-2">
                <ActivityTable activities={repoActivities} hideRepo />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
