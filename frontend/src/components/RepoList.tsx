import type { Repo } from "@/lib/types";

interface RepoListProps {
  repos: Repo[];
}

export function RepoList({ repos }: RepoListProps) {
  if (!repos.length) {
    return <p className="text-gray-500 text-sm">No repositories yet.</p>;
  }

  return (
    <div className="space-y-2">
      {repos.map((r) => (
        <div key={r.id} className="flex items-center gap-2 py-1 text-sm">
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              r.watch ? "bg-green-400" : "bg-gray-600"
            }`}
          />
          <a
            href={r.repo_url}
            target="_blank"
            rel="noreferrer"
            className="text-blue-400 hover:underline truncate"
          >
            {r.repo_url}
          </a>
          <span className="ml-auto text-gray-600 flex-shrink-0">
            {r.watch ? "watching" : "paused"}
          </span>
        </div>
      ))}
    </div>
  );
}
