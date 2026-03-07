import type { Activity } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  done: "text-green-400 border-green-400",
  failed: "text-red-400 border-red-400",
  running: "text-blue-400 border-blue-400",
  pending: "text-yellow-400 border-yellow-400",
  pending_approval: "text-purple-400 border-purple-400",
};

interface ActivityTableProps {
  activities: Activity[];
}

export function ActivityTable({ activities }: ActivityTableProps) {
  if (!activities.length) {
    return <p className="text-gray-500 text-sm">No activities yet.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-700">
            <th className="text-left py-2 pr-4">Repo</th>
            <th className="text-left py-2 pr-4">Kind</th>
            <th className="text-left py-2 pr-4">Trigger</th>
            <th className="text-left py-2 pr-4">Status</th>
            <th className="text-left py-2 pr-4">Cost</th>
            <th className="text-left py-2">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {activities.map((a) => (
            <tr key={a.id} className="text-gray-400">
              <td className="py-1.5 pr-4 text-gray-300">{a.repo_id}</td>
              <td className="py-1.5 pr-4">{a.kind}</td>
              <td className="py-1.5 pr-4">{a.trigger ?? ""}</td>
              <td className="py-1.5 pr-4">
                <span
                  className={`px-2 py-0.5 rounded text-xs border ${
                    STATUS_COLORS[a.status] ?? "text-gray-400 border-gray-400"
                  }`}
                >
                  {a.status}
                </span>
              </td>
              <td className="py-1.5 pr-4">
                {a.cost_usd != null ? `$${a.cost_usd.toFixed(4)}` : "—"}
              </td>
              <td className="py-1.5">
                {a.updated_at ? a.updated_at.substring(0, 19).replace("T", " ") : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
