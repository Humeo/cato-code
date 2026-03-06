"""Dashboard REST API + HTML UI."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..store import Store


def make_router(store: Store) -> APIRouter:
    """Return a new router with store injected."""
    router = APIRouter(prefix="/api", tags=["dashboard"])

    @router.get("/stats")
    async def get_stats() -> dict:
        return store.get_stats()

    @router.get("/repos")
    async def list_repos() -> list[dict]:
        return [dict(r) for r in store.list_repos()]

    @router.get("/repos/{repo_id}")
    async def get_repo_stats(repo_id: str) -> dict:
        stats = store.get_repo_stats(repo_id)
        if stats is None:
            raise HTTPException(status_code=404, detail="Repo not found")
        return stats

    @router.get("/repos/{repo_id}/activities")
    async def list_repo_activities(repo_id: str) -> list[dict]:
        return [dict(a) for a in store.list_activities(repo_id)]

    @router.get("/activities")
    async def list_activities() -> list[dict]:
        return [dict(a) for a in store.list_activities()]

    @router.get("/activities/{activity_id}/logs")
    async def get_activity_logs(activity_id: str) -> list[dict]:
        return [dict(log) for log in store.get_logs(activity_id)]

    return router


DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CatoCode Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen font-mono">

<div class="max-w-6xl mx-auto p-6">
  <!-- Header -->
  <div class="flex items-center gap-3 mb-8">
    <span class="text-3xl">🐱</span>
    <div>
      <h1 class="text-2xl font-bold text-white">CatoCode</h1>
      <p class="text-gray-400 text-sm">Autonomous Code Maintenance Agent</p>
    </div>
    <div id="status-dot" class="ml-auto w-3 h-3 rounded-full bg-green-400 animate-pulse"></div>
  </div>

  <!-- Stat Cards -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8" id="stat-cards">
    <div class="bg-gray-800 rounded-lg p-4">
      <p class="text-gray-400 text-xs mb-1">Repos Watched</p>
      <p class="text-2xl font-bold" id="stat-repos">—</p>
    </div>
    <div class="bg-gray-800 rounded-lg p-4">
      <p class="text-gray-400 text-xs mb-1">Total Activities</p>
      <p class="text-2xl font-bold" id="stat-total">—</p>
    </div>
    <div class="bg-gray-800 rounded-lg p-4">
      <p class="text-gray-400 text-xs mb-1">Completed</p>
      <p class="text-2xl font-bold text-green-400" id="stat-done">—</p>
    </div>
    <div class="bg-gray-800 rounded-lg p-4">
      <p class="text-gray-400 text-xs mb-1">Total Cost</p>
      <p class="text-2xl font-bold text-yellow-400" id="stat-cost">—</p>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <!-- Activity by kind -->
    <div class="bg-gray-800 rounded-lg p-4">
      <h2 class="text-sm font-semibold text-gray-300 mb-4">Activities by Type</h2>
      <canvas id="kind-chart" height="180"></canvas>
    </div>
    <!-- Activity by status -->
    <div class="bg-gray-800 rounded-lg p-4">
      <h2 class="text-sm font-semibold text-gray-300 mb-4">Activities by Status</h2>
      <canvas id="status-chart" height="180"></canvas>
    </div>
  </div>

  <!-- Repos -->
  <div class="bg-gray-800 rounded-lg p-4 mb-6">
    <h2 class="text-sm font-semibold text-gray-300 mb-4">Watched Repositories</h2>
    <div id="repos-list" class="space-y-2 text-sm text-gray-400">Loading...</div>
  </div>

  <!-- Recent Activities -->
  <div class="bg-gray-800 rounded-lg p-4">
    <h2 class="text-sm font-semibold text-gray-300 mb-4">Recent Activities</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-xs">
        <thead>
          <tr class="text-gray-500 border-b border-gray-700">
            <th class="text-left py-2 pr-4">Repo</th>
            <th class="text-left py-2 pr-4">Kind</th>
            <th class="text-left py-2 pr-4">Trigger</th>
            <th class="text-left py-2 pr-4">Status</th>
            <th class="text-left py-2 pr-4">Cost</th>
            <th class="text-left py-2">Updated</th>
          </tr>
        </thead>
        <tbody id="activities-tbody" class="divide-y divide-gray-700"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const STATUS_COLORS = {
  done: '#4ade80',
  failed: '#f87171',
  running: '#60a5fa',
  pending: '#facc15',
  pending_approval: '#c084fc',
};

let kindChart, statusChart;

function statusBadge(s) {
  const c = STATUS_COLORS[s] || '#9ca3af';
  return `<span style="color:${c};border:1px solid ${c}" class="px-2 py-0.5 rounded text-xs">${s}</span>`;
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const d = await res.json();

    document.getElementById('stat-repos').textContent = d.repos.watched;
    document.getElementById('stat-total').textContent = d.activities.total;
    document.getElementById('stat-done').textContent = d.activities.by_status.done ?? 0;
    document.getElementById('stat-cost').textContent = '$' + d.cost_usd.toFixed(4);

    // Kind chart
    const kinds = Object.entries(d.activities.by_kind || {});
    const kindData = { labels: kinds.map(k=>k[0]), datasets:[{ data: kinds.map(k=>k[1]),
      backgroundColor: ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#3b82f6','#ef4444'] }] };
    if (kindChart) kindChart.destroy();
    kindChart = new Chart(document.getElementById('kind-chart'), {
      type: 'doughnut', data: kindData,
      options: { plugins: { legend: { labels: { color:'#9ca3af', font:{size:11} } } } }
    });

    // Status chart
    const statuses = Object.entries(d.activities.by_status || {});
    const statusData = { labels: statuses.map(s=>s[0]),
      datasets:[{ data: statuses.map(s=>s[1]),
        backgroundColor: statuses.map(s=>STATUS_COLORS[s[0]]||'#9ca3af') }] };
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(document.getElementById('status-chart'), {
      type: 'bar', data: statusData,
      options: {
        plugins: { legend: { display: false } },
        scales: { x: { ticks:{color:'#9ca3af'} }, y: { ticks:{color:'#9ca3af'}, beginAtZero:true } }
      }
    });

    // Recent activities
    const tbody = document.getElementById('activities-tbody');
    tbody.innerHTML = (d.recent_activities || []).map(a => `
      <tr class="text-gray-400">
        <td class="py-1.5 pr-4 text-gray-300">${a.repo_id}</td>
        <td class="py-1.5 pr-4">${a.kind}</td>
        <td class="py-1.5 pr-4">${a.trigger || ''}</td>
        <td class="py-1.5 pr-4">${statusBadge(a.status)}</td>
        <td class="py-1.5 pr-4">${a.cost_usd ? '$'+parseFloat(a.cost_usd).toFixed(4) : '—'}</td>
        <td class="py-1.5">${a.updated_at ? a.updated_at.substring(0,19).replace('T',' ') : ''}</td>
      </tr>`).join('');
  } catch(e) {
    console.error('Failed to load stats', e);
  }
}

async function loadRepos() {
  try {
    const res = await fetch('/api/repos');
    const repos = await res.json();
    const el = document.getElementById('repos-list');
    if (!repos.length) { el.textContent = 'No repos registered.'; return; }
    el.innerHTML = repos.map(r => `
      <div class="flex items-center gap-2 py-1">
        <span class="w-2 h-2 rounded-full ${r.watch ? 'bg-green-400' : 'bg-gray-600'}"></span>
        <a href="${r.repo_url}" target="_blank" class="text-blue-400 hover:underline">${r.repo_url}</a>
        <span class="ml-auto text-gray-600">${r.watch ? 'watching' : 'paused'}</span>
      </div>`).join('');
  } catch(e) { console.error(e); }
}

loadStats();
loadRepos();
setInterval(loadStats, 15000);
</script>
</body>
</html>
"""


def dashboard_html_route() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)
