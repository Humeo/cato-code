from __future__ import annotations

import pytest

from catocode.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(db_path=tmp_path / "test.db")


def test_finalize_runtime_session_schedules_gc_after_seven_days(store):
    from catocode.session_runtime import collect_runtime_sessions_for_gc, finalize_runtime_session

    store.add_repo("owner-repo", "https://github.com/owner/repo")
    session_id = store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="refresh_repo_memory_review",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-gc-1",
        branch_name="catocode/session/session-gc-1",
    )

    session = finalize_runtime_session(
        store,
        session_id,
        status="done",
        terminal_at="2026-03-25T12:00:00+00:00",
    )

    assert session["status"] == "done"
    assert session["terminal_at"] == "2026-03-25T12:00:00+00:00"
    assert session["gc_eligible_at"] == "2026-03-25T12:00:00+00:00"
    assert session["gc_delete_after"] == "2026-04-01T12:00:00+00:00"
    assert session["gc_status"] == "pending"

    ready = collect_runtime_sessions_for_gc(store, as_of="2026-04-01T12:00:00+00:00")
    assert [candidate["id"] for candidate in ready] == [session_id]


def test_finalize_runtime_session_blocks_gc_when_pr_still_open(store):
    from catocode.session_runtime import collect_runtime_sessions_for_gc, finalize_runtime_session

    store.add_repo("owner-repo", "https://github.com/owner/repo")
    session_id = store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="fix_issue",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-gc-2",
        branch_name="catocode/session/session-gc-2",
        pr_number=101,
    )

    session = finalize_runtime_session(
        store,
        session_id,
        status="done",
        terminal_at="2026-03-25T12:00:00+00:00",
    )

    assert session["status"] == "done"
    assert session["gc_eligible_at"] is None
    assert session["gc_delete_after"] is None
    assert session["gc_status"] == "blocked"
    assert collect_runtime_sessions_for_gc(store, as_of="2026-04-02T12:00:00+00:00") == []


def test_finalize_runtime_session_blocks_gc_when_session_has_pending_activity(store):
    from catocode.session_runtime import collect_runtime_sessions_for_gc, finalize_runtime_session

    store.add_repo("owner-repo", "https://github.com/owner/repo")
    session_id = store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="task",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-gc-3",
        branch_name="catocode/session/session-gc-3",
    )
    activity_id = store.add_activity("owner-repo", "task", "issue:42:comment:111")
    store.update_activity(activity_id, session_id=session_id, status="pending")

    session = finalize_runtime_session(
        store,
        session_id,
        status="failed",
        terminal_at="2026-03-25T12:00:00+00:00",
    )

    assert session["status"] == "failed"
    assert session["gc_eligible_at"] is None
    assert session["gc_delete_after"] is None
    assert session["gc_status"] == "blocked"
    assert collect_runtime_sessions_for_gc(store, as_of="2026-04-02T12:00:00+00:00") == []


def test_cleanup_expired_runtime_sessions_marks_gc_failed_on_cleanup_error(store):
    from catocode.session_runtime import cleanup_expired_runtime_sessions, finalize_runtime_session

    class FailingContainerManager:
        def remove_session_worktree(self, repo_id: str, session_id: str) -> None:
            raise RuntimeError("worktree removal failed")

    store.add_repo("owner-repo", "https://github.com/owner/repo")
    session_id = store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="refresh_repo_memory_review",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-gc-4",
        branch_name="catocode/session/session-gc-4",
    )
    finalize_runtime_session(
        store,
        session_id,
        status="done",
        terminal_at="2026-03-25T12:00:00+00:00",
    )

    cleaned = cleanup_expired_runtime_sessions(
        store,
        FailingContainerManager(),
        as_of="2026-04-01T12:00:00+00:00",
    )

    assert cleaned == []
    session = store.get_runtime_session(session_id)
    assert session is not None
    assert session["gc_status"] == "failed"
    assert session["gc_error"] == "worktree removal failed"
