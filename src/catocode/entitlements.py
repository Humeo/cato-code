from __future__ import annotations

from typing import Any

from .config import get_non_whitelist_activity_limit, get_user_whitelist
from .store import Store


def is_whitelisted_login(github_login: str | None) -> bool:
    if not github_login:
        return False
    return github_login.strip().lower() in get_user_whitelist()


def build_user_quota_payload(store: Store, user: dict[str, Any]) -> dict[str, Any]:
    limit = get_non_whitelist_activity_limit()
    whitelisted = is_whitelisted_login(user.get("github_login"))
    used = store.get_user_activity_usage_count(user["id"])
    remaining = None if whitelisted else max(limit - used, 0)
    return {
        "is_whitelisted": whitelisted,
        "activity_quota_limit": limit,
        "activity_quota_used": used,
        "activity_quota_remaining": remaining,
    }


def user_can_trigger_activity(store: Store, user: dict[str, Any]) -> bool:
    quota = build_user_quota_payload(store, user)
    remaining = quota["activity_quota_remaining"]
    return remaining is None or remaining > 0


def repo_manager_user(store: Store, repo: dict[str, Any] | None) -> dict[str, Any] | None:
    if repo is None:
        return None
    manager_user_id = repo.get("manager_user_id") or repo.get("user_id")
    if not manager_user_id:
        return None
    return store.get_user(manager_user_id)
