"""Tests for the dashboard API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from catocode.auth.token import TokenAuth
from catocode.store import Store
from catocode.webhook.server import WebhookServer


def _make_client(tmp_path: Path) -> tuple[TestClient, Store]:
    store = Store(db_path=tmp_path / "test.db")
    auth = TokenAuth("ghp_test")
    server = WebhookServer(store, auth=auth)
    return TestClient(server.app), store


def test_dashboard_html(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CatoCode" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_api_stats_empty(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["repos"]["total"] == 0
    assert data["repos"]["watched"] == 0
    assert data["activities"]["total"] == 0
    assert data["cost_usd"] == 0.0


def test_api_stats_with_data(tmp_path):
    client, store = _make_client(tmp_path)

    store.add_repo("owner-repo", "https://github.com/owner/repo")
    store.update_repo("owner-repo", watch=1)
    a1 = store.add_activity("owner-repo", "analyze_issue", "issue:1")
    store.update_activity(a1, status="done", cost_usd=0.05)
    a2 = store.add_activity("owner-repo", "review_pr", "pr:2")
    store.update_activity(a2, status="failed", cost_usd=0.02)

    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["repos"]["watched"] == 1
    assert data["activities"]["total"] == 2
    assert data["activities"]["by_status"]["done"] == 1
    assert data["activities"]["by_status"]["failed"] == 1
    assert data["cost_usd"] == pytest.approx(0.07, abs=0.001)
    assert data["activities"]["by_kind"]["analyze_issue"] == 1


def test_api_repos(tmp_path):
    client, store = _make_client(tmp_path)
    store.add_repo("owner-repo", "https://github.com/owner/repo")

    resp = client.get("/api/repos")
    assert resp.status_code == 200
    repos = resp.json()
    assert len(repos) == 1
    assert repos[0]["id"] == "owner-repo"


def test_api_repo_stats(tmp_path):
    client, store = _make_client(tmp_path)
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    a1 = store.add_activity("owner-repo", "fix_issue", "issue:10")
    store.update_activity(a1, status="done", cost_usd=0.10)

    resp = client.get("/api/repos/owner-repo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cost_usd"] == pytest.approx(0.10, abs=0.001)
    assert data["activities"]["by_status"]["done"] == 1


def test_api_repo_not_found(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/api/repos/nonexistent")
    assert resp.status_code == 404


def test_api_activities(tmp_path):
    client, store = _make_client(tmp_path)
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    store.add_activity("owner-repo", "patrol", "budget:5")

    resp = client.get("/api/activities")
    assert resp.status_code == 200
    activities = resp.json()
    assert len(activities) == 1
    assert activities[0]["kind"] == "patrol"


def test_api_health(tmp_path):
    client, _ = _make_client(tmp_path)
    resp = client.get("/webhook/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
