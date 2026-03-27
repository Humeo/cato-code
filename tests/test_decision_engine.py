from __future__ import annotations

import pytest

from catocode.decision.engine import decide_engagement
from catocode.store import Store
from catocode.webhook.parser import WebhookEvent


@pytest.mark.asyncio
async def test_pr_opened_skips_configured_bot_pr(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_APP_NAME", "catocode-bot")
    store = Store(tmp_path / "test.db")
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    repo = store.get_repo("owner-repo")
    assert repo is not None

    event = WebhookEvent(
        event_id="evt-1",
        event_type="pr_opened",
        repo_id="owner-repo",
        trigger="pr:29",
        payload={"pull_request": {"user": {"login": "catocode-bot[bot]"}}},
        actor="humeo",
    )

    decision = await decide_engagement(event, repo, store)

    assert decision.should_engage is False
    assert decision.activity_kind is None


@pytest.mark.asyncio
async def test_pr_review_submitted_engages_on_configured_bot_pr(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_APP_NAME", "catocode-bot")
    store = Store(tmp_path / "test.db")
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    repo = store.get_repo("owner-repo")
    assert repo is not None

    event = WebhookEvent(
        event_id="evt-2",
        event_type="pr_review_submitted",
        repo_id="owner-repo",
        trigger="pr:29",
        payload={"pull_request": {"user": {"login": "catocode-bot[bot]"}}},
        actor="humeo",
    )

    decision = await decide_engagement(event, repo, store)

    assert decision.should_engage is True
    assert decision.activity_kind == "respond_review"
    assert decision.requires_approval is False
