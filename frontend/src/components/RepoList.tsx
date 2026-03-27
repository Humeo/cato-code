"use client";

import { useState, useCallback, useEffect } from "react";
import { getInstallUrl, retrySetup, unwatchRepo, watchRepo } from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import type { Repo } from "@/lib/types";

interface RepoListProps {
  repos: Repo[];
}

export function RepoList({ repos: initialRepos }: RepoListProps) {
  const [repos, setRepos] = useState(initialRepos);
  const [pendingDelete, setPendingDelete] = useState<Repo | null>(null);
  const [retryingRepoId, setRetryingRepoId] = useState<string | null>(null);
  const [watchingRepoId, setWatchingRepoId] = useState<string | null>(null);

  useEffect(() => {
    setRepos(initialRepos);
  }, [initialRepos]);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInstallApp = useCallback(async () => {
    const url = await getInstallUrl();
    if (!url) {
      setError("Failed to fetch install URL.");
      return;
    }
    window.location.href = url;
  }, []);

  const handleRetrySetup = useCallback(async (repoId: string) => {
    setRetryingRepoId(repoId);
    setError(null);
    const result = await retrySetup(repoId);
    setRetryingRepoId(null);
    if (!result || "error" in result) {
      setError(result?.error ?? "Failed to retry setup.");
      return;
    }
    setRepos((prev) =>
      prev.map((repo) =>
        repo.id === repoId
          ? {
              ...repo,
              lifecycle_status: "setting_up",
              last_error: null,
              last_setup_activity_id: result.activity_id,
            }
          : repo
      )
    );
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setError(null);
    const ok = await unwatchRepo(pendingDelete.id);
    if (ok) {
      setRepos((prev) =>
        prev.map((repo) =>
          repo.id === pendingDelete.id
            ? { ...repo, watch: 0, lifecycle_status: "watched", last_error: null }
            : repo
        )
      );
      setPendingDelete(null);
    } else {
      setError("Failed to stop watching. Check if the backend is running.");
    }
    setDeleting(false);
  }, [pendingDelete]);

  const handleWatchRepo = useCallback(async (repoId: string) => {
    setWatchingRepoId(repoId);
    setError(null);
    const result = await watchRepo(repoId);
    setWatchingRepoId(null);
    if (!result || "error" in result) {
      setError(result?.error ?? "Failed to watch repository.");
      return;
    }
    setRepos((prev) =>
      prev.map((repo) =>
        repo.id === repoId
          ? {
              ...repo,
              watch: 1,
              lifecycle_status: result.status === "ready" ? "ready" : "setting_up",
              last_error: null,
              last_setup_activity_id: result.activity_id,
            }
          : repo
      )
    );
  }, []);

  const handleCancel = useCallback(() => {
    if (!deleting) {
      setPendingDelete(null);
      setError(null);
    }
  }, [deleting]);

  if (!repos.length) {
    return (
      <div className="rounded-2xl border border-white/8 bg-black/20 px-6 py-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
          <span className="text-xl">+</span>
        </div>
        <p className="text-sm font-medium text-gray-200">No repositories connected yet.</p>
        <p className="mx-auto mt-2 max-w-md text-xs leading-6 text-gray-500">
          Connect GitHub, install the App on your account or organization, then choose which repositories to watch.
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={handleInstallApp}
            className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs font-medium text-cyan-200 transition hover:bg-cyan-400/20"
          >
            Install App
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-1">
        {repos.map((r) => {
          const shortName = r.repo_url.replace("https://github.com/", "");
          const isRetryingSetup = retryingRepoId === r.id;
          const isWatching = watchingRepoId === r.id;
          const lifecycle = r.lifecycle_status ?? (r.watch ? "ready" : "watched");
          const lifecycleStyle =
            lifecycle === "ready"
              ? "text-emerald-400 bg-emerald-400/10"
              : lifecycle === "setting_up"
                ? "text-blue-400 bg-blue-400/10"
                : lifecycle === "error"
                  ? "text-red-400 bg-red-400/10"
                  : "text-gray-500 bg-gray-500/10";
          return (
            <div key={r.id} className="py-1">
              <div
                className="flex items-center gap-3 py-2.5 px-3 -mx-3 rounded-lg hover:bg-white/[0.02] transition-colors text-sm group"
              >
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    r.watch ? "bg-emerald-400" : "bg-gray-600"
                  }`}
                />
                <a
                  href={r.repo_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-gray-300 hover:text-white truncate transition-colors font-medium"
                >
                  {shortName}
                </a>
                <span
                  className={`ml-auto text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${lifecycleStyle}`}
                >
                  {lifecycle.replace("_", " ")}
                </span>
                {!r.watch && (
                  <button
                    onClick={() => handleWatchRepo(r.id)}
                    disabled={isWatching}
                    className="opacity-0 group-hover:opacity-100 text-xs px-2 py-0.5 rounded transition-all flex-shrink-0 text-cyan-300 bg-cyan-400/10 hover:bg-cyan-400/20 disabled:opacity-50"
                    title="Watch repository"
                  >
                    {isWatching ? "watching…" : "watch"}
                  </button>
                )}
                {lifecycle === "error" && (
                  <button
                    onClick={() => handleRetrySetup(r.id)}
                    disabled={isRetryingSetup}
                    className="opacity-0 group-hover:opacity-100 text-xs px-2 py-0.5 rounded transition-all flex-shrink-0 text-amber-300 bg-amber-400/10 hover:bg-amber-400/20 disabled:opacity-50"
                    title="Retry setup"
                  >
                    {isRetryingSetup ? "retrying…" : "retry setup"}
                  </button>
                )}
                {r.watch && (
                  <>
                    <button
                      onClick={() => setPendingDelete(r)}
                      className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all flex-shrink-0 p-1 rounded hover:bg-red-400/10"
                      title="Stop watching"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
              {(r.last_error || lifecycle === "setting_up" || !r.watch) && (
                <div className="ml-5 mr-1 rounded-lg border border-white/5 bg-black/15 px-3 py-2 text-[11px] text-gray-400">
                  {!r.watch && (
                    <div className="text-cyan-200/90">
                      installed and visible. click watch to clone, initialize CLAUDE.md, run `cg index`, and make this repo ready.
                    </div>
                  )}
                  {lifecycle === "setting_up" && (
                    <div className="flex items-center gap-2 text-blue-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
                      setup running: clone, CLAUDE.md init, `cg index`, health check
                    </div>
                  )}
                  {r.last_error && (
                    <div className="mt-1 text-red-300/90">
                      last setup error: {r.last_error}
                    </div>
                  )}
                  {r.last_ready_at && lifecycle === "ready" && (
                    <div className="mt-1 text-gray-500">
                      ready since {new Date(r.last_ready_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        title="Stop Watching"
        message={
          pendingDelete
            ? `Stop watching ${pendingDelete.repo_url.replace("https://github.com/", "")}? This will stop automated issue analysis, fixes, and repo maintenance for this repo.`
            : ""
        }
        confirmLabel="Stop Watching"
        onConfirm={handleConfirmDelete}
        onCancel={handleCancel}
        loading={deleting}
      />

      {error && (
        <div className="mt-2 text-xs text-red-400 bg-red-400/10 rounded-lg px-3 py-2">
          {error}
        </div>
      )}
    </>
  );
}
