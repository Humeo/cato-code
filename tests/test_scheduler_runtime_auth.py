from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from catocode.auth.base import Auth, GitHubAppTokenProvider
from catocode.scheduler import Scheduler
from catocode.session_runtime import finalize_runtime_session
from catocode.store import Store


class FakeGitHubAppAuth(Auth, GitHubAppTokenProvider):
    def __init__(self) -> None:
        self.installation_calls: list[str] = []
        self.get_token_calls = 0

    async def get_installation_token(self, installation_id: str) -> str:
        self.installation_calls.append(installation_id)
        return f"ghs-{installation_id}"

    async def get_token(self) -> str:
        self.get_token_calls += 1
        return "ghp-global"

    def auth_type(self) -> str:
        return "github_app"


@pytest.mark.asyncio
async def test_scheduler_dispatch_uses_repo_installation_token(monkeypatch, tmp_path):
    store = Store(db_path=tmp_path / "test.db")
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    store.update_repo("owner-repo", watch=1, installation_id="inst-123")
    activity_id = store.add_activity("owner-repo", "fix_issue", "issue:42")

    auth = FakeGitHubAppAuth()
    scheduler = Scheduler(store=store, container_mgr=object(), auth=auth)
    fake_dispatch = AsyncMock()

    monkeypatch.setattr("catocode.scheduler.dispatch", fake_dispatch)
    monkeypatch.setattr("catocode.scheduler.get_anthropic_api_key", lambda: "sk-ant")
    monkeypatch.setattr("catocode.scheduler.get_anthropic_base_url", lambda: None)

    await scheduler._dispatch_one(activity_id, "owner-repo")

    assert auth.installation_calls == ["inst-123"]
    assert auth.get_token_calls == 0
    assert fake_dispatch.await_count == 1
    assert fake_dispatch.await_args.kwargs["github_token"] == "ghs-inst-123"


@pytest.mark.asyncio
async def test_scheduler_approval_check_uses_repo_installation_token(monkeypatch, tmp_path):
    store = Store(db_path=tmp_path / "test.db")
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    store.update_repo("owner-repo", watch=1, installation_id="inst-123")
    activity_id = store.add_activity("owner-repo", "analyze_issue", "issue:42")
    store.update_activity(activity_id, status="pending", requires_approval=1)

    auth = FakeGitHubAppAuth()
    scheduler = Scheduler(store=store, container_mgr=object(), auth=auth)

    class _Response:
        status_code = 200

        def json(self) -> list[dict]:
            return [
                {
                    "body": "/approve",
                    "user": {"login": "octocat"},
                    "html_url": "https://github.com/owner/repo/issues/42#issuecomment-1",
                }
            ]

    async def fake_get(self, url, headers=None, timeout=None):  # noqa: ANN001
        assert url.endswith("/repos/owner/repo/issues/42/comments")
        assert headers["Authorization"] == "Bearer ghs-inst-123"
        return _Response()

    async def fake_check_user_is_admin(username: str, owner: str, repo: str, github_token: str) -> bool:
        assert (username, owner, repo) == ("octocat", "owner", "repo")
        assert github_token == "ghs-inst-123"
        return True

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    monkeypatch.setattr("catocode.scheduler.check_user_is_admin", fake_check_user_is_admin)

    await scheduler._check_for_approval(store.get_activity(activity_id))

    updated = store.get_activity(activity_id)
    assert auth.installation_calls == ["inst-123"]
    assert auth.get_token_calls == 0
    assert updated["requires_approval"] == 0
    assert updated["approved_by"] == "octocat"


@pytest.mark.asyncio
async def test_scheduler_cleans_up_expired_runtime_sessions(monkeypatch, tmp_path):
    store = Store(db_path=tmp_path / "test.db")
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    session_id = store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="refresh_repo_memory_review",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-gc-5",
        branch_name="catocode/session/session-gc-5",
    )
    finalize_runtime_session(
        store,
        session_id,
        status="done",
        terminal_at="2026-03-25T12:00:00+00:00",
    )

    class FakeContainerManager:
        def __init__(self) -> None:
            self.cleaned: list[tuple[str, str]] = []

        def remove_session_worktree(self, repo_id: str, session_id: str) -> None:
            self.cleaned.append((repo_id, session_id))

    container_mgr = FakeContainerManager()
    scheduler = Scheduler(store=store, container_mgr=container_mgr, auth=FakeGitHubAppAuth())

    await scheduler._cleanup_expired_runtime_sessions(as_of="2026-04-01T12:00:00+00:00")

    assert container_mgr.cleaned == [("owner-repo", session_id)]
    session = store.get_runtime_session(session_id)
    assert session is not None
    assert session["gc_status"] == "done"
