from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from .store import Store

SESSIONIZED_ACTIVITY_KINDS = {
    "analyze_issue",
    "fix_issue",
    "triage",
    "task",
    "review_pr",
    "respond_review",
    "refresh_repo_memory_review",
}
ISSUE_SESSION_ACTIVITY_KINDS = {"analyze_issue", "fix_issue", "triage"}
PR_SESSION_ACTIVITY_KINDS = {"review_pr", "respond_review"}
TERMINAL_SESSION_STATUSES = {"done", "failed", "cancelled"}
AUTO_TERMINAL_ACTIVITY_KINDS = {"refresh_repo_memory_review"}
GC_RETENTION = timedelta(days=7)


def session_worktree_path(repo_id: str, session_id: str) -> str:
    return f"/repos/.worktrees/{repo_id}/{session_id}"


def session_branch_name(session_id: str) -> str:
    return f"catocode/session/{session_id}"


def issue_number_from_trigger(trigger: str | None) -> int | None:
    if not trigger or not trigger.startswith("issue:"):
        return None
    parts = trigger.split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def pr_number_from_trigger(trigger: str | None) -> int | None:
    if not trigger:
        return None
    if trigger.startswith("pr:"):
        parts = trigger.split(":")
        if len(parts) < 2:
            return None
        try:
            return int(parts[1])
        except ValueError:
            return None
    if trigger.startswith("repo_memory_refresh:pr:"):
        parts = trigger.split(":")
        if len(parts) < 3:
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None
    return None


def approval_scope_from_trigger(trigger: str | None) -> str | None:
    if not trigger:
        return None
    parts = trigger.split(":")
    if len(parts) < 2:
        return None
    if parts[0] not in {"issue", "pr"}:
        return None
    return f"{parts[0]}:{parts[1]}"


def should_sessionize_activity(kind: str) -> bool:
    return kind in SESSIONIZED_ACTIVITY_KINDS


def _is_reusable_runtime_session(session: dict | None) -> bool:
    return session is not None and session.get("status") not in TERMINAL_SESSION_STATUSES


def create_runtime_session_for_activity(
    store: Store,
    repo_id: str,
    activity_kind: str,
    trigger: str | None,
) -> dict:
    session_id = str(uuid.uuid4())
    issue_number = issue_number_from_trigger(trigger)
    pr_number = pr_number_from_trigger(trigger)
    session_id = store.create_runtime_session(
        session_id=session_id,
        repo_id=repo_id,
        entry_kind=activity_kind,
        status="active",
        worktree_path=session_worktree_path(repo_id, session_id),
        branch_name=session_branch_name(session_id),
        issue_number=issue_number,
        pr_number=pr_number,
        pr_state="closed" if activity_kind == "refresh_repo_memory_review" and pr_number is not None else "open",
    )
    session = store.get_runtime_session(session_id)
    if session is None:
        raise RuntimeError(f"Failed to persist runtime session {session_id}")
    return session


def resolve_runtime_session_for_activity(
    store: Store,
    repo_id: str,
    activity_kind: str,
    trigger: str | None,
    existing_session_id: str | None = None,
) -> dict | None:
    if not should_sessionize_activity(activity_kind):
        return None

    if existing_session_id:
        existing_session = store.get_runtime_session(existing_session_id)
        if existing_session is not None:
            return existing_session

    if activity_kind == "refresh_repo_memory_review":
        return create_runtime_session_for_activity(store, repo_id, activity_kind, trigger)

    issue_number = issue_number_from_trigger(trigger)
    pr_number = pr_number_from_trigger(trigger)

    if activity_kind in ISSUE_SESSION_ACTIVITY_KINDS or (activity_kind == "task" and issue_number is not None):
        session = store.find_issue_runtime_session(repo_id, issue_number) if issue_number is not None else None
        if _is_reusable_runtime_session(session):
            return session
        return create_runtime_session_for_activity(store, repo_id, activity_kind, trigger)

    if activity_kind in PR_SESSION_ACTIVITY_KINDS or (activity_kind == "task" and pr_number is not None):
        session = store.find_pr_runtime_session(repo_id, pr_number) if pr_number is not None else None
        if _is_reusable_runtime_session(session):
            return session
        return create_runtime_session_for_activity(store, repo_id, activity_kind, trigger)

    return create_runtime_session_for_activity(store, repo_id, activity_kind, trigger)


def should_auto_terminal_session(activity_kind: str) -> bool:
    return activity_kind in AUTO_TERMINAL_ACTIVITY_KINDS


def _parse_iso(value: str | None) -> datetime:
    if value:
        return datetime.fromisoformat(value)
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def finalize_runtime_session(
    store: Store,
    session_id: str,
    *,
    status: str,
    terminal_at: str | None = None,
) -> dict:
    terminal_dt = _parse_iso(terminal_at)
    terminal_at_iso = _iso(terminal_dt)

    pr_link = store.get_runtime_session_pr_link(session_id)
    has_open_pr = pr_link is not None and pr_link.get("pr_state", "open") == "open"
    has_pending_activity = store.has_inflight_runtime_session_activity(session_id)

    gc_eligible_at: str | None = None
    gc_delete_after: str | None = None
    gc_status = "blocked"
    gc_error = None

    if not has_open_pr and not has_pending_activity:
        gc_eligible_at = terminal_at_iso
        gc_delete_after = _iso(terminal_dt + GC_RETENTION)
        gc_status = "pending"

    store.mark_runtime_session_terminal(
        session_id,
        status=status,
        terminal_at=terminal_at_iso,
        gc_eligible_at=gc_eligible_at,
        gc_delete_after=gc_delete_after,
        gc_status=gc_status,
        gc_error=gc_error,
    )
    session = store.get_runtime_session(session_id)
    if session is None:
        raise RuntimeError(f"Runtime session {session_id} disappeared during finalization")
    return session


def collect_runtime_sessions_for_gc(store: Store, *, as_of: str | None = None) -> list[dict]:
    return store.list_runtime_sessions_ready_for_gc(_iso(_parse_iso(as_of)))


def cleanup_expired_runtime_sessions(
    store: Store,
    container_mgr,
    *,
    as_of: str | None = None,
) -> list[str]:
    cleaned: list[str] = []
    for session in collect_runtime_sessions_for_gc(store, as_of=as_of):
        try:
            container_mgr.remove_session_worktree(session["repo_id"], session["id"])
        except Exception as exc:
            store.update_runtime_session(session["id"], gc_status="failed", gc_error=str(exc))
            continue
        store.update_runtime_session(session["id"], gc_status="done", gc_error=None)
        cleaned.append(session["id"])
    return cleaned
