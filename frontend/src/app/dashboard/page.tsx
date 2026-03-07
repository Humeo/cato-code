import { getStats, getRepos, getActivities, getInstallUrl } from "@/lib/api";
import { StatCard } from "@/components/StatCard";
import { RepoList } from "@/components/RepoList";
import { ActivityTable } from "@/components/ActivityTable";
import Link from "next/link";

export default async function DashboardPage() {
  const [stats, repos, activities] = await Promise.all([
    getStats(),
    getRepos(),
    getActivities(),
  ]);

  const noRepos = !repos || repos.length === 0;

  return (
    <div className="space-y-6">
      {/* Install CTA */}
      {noRepos && (
        <div className="bg-blue-950 border border-blue-800 rounded-lg p-6 text-center">
          <p className="text-blue-200 mb-4">
            No repositories watched yet. Install the GitHub App to get started.
          </p>
          <Link
            href="/install"
            className="inline-block bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-2 rounded-lg transition-colors"
          >
            Install GitHub App →
          </Link>
        </div>
      )}

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Repos Watched" value={stats.repos.watched} />
          <StatCard label="Total Activities" value={stats.activities.total} />
          <StatCard
            label="Completed"
            value={stats.activities.by_status.done ?? 0}
            accent="text-green-400"
          />
          <StatCard
            label="Total Cost"
            value={`$${stats.cost_usd.toFixed(4)}`}
            accent="text-yellow-400"
          />
        </div>
      )}

      {/* Repos */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Watched Repositories</h2>
        <RepoList repos={repos ?? []} />
      </div>

      {/* Recent Activities */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Activities</h2>
        <ActivityTable activities={stats?.recent_activities ?? activities ?? []} />
      </div>
    </div>
  );
}
