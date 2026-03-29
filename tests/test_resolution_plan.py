from __future__ import annotations

import pytest

from catocode.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(db_path=tmp_path / "test.db")


@pytest.fixture
def session_id(store):
    store.add_repo("owner-repo", "https://github.com/owner/repo")
    return store.create_runtime_session(
        repo_id="owner-repo",
        entry_kind="fix_issue",
        status="active",
        worktree_path="/repos/.worktrees/owner-repo/session-1",
        branch_name="catocode/session/session-1",
        issue_number=42,
    )


def test_update_hypothesis_creates_semantic_record(store, session_id):
    from catocode.resolution_plan import update_hypothesis

    update_hypothesis(
        store=store,
        session_id=session_id,
        hypothesis_id="hypo_1",
        title="Alias collision in Query.values",
        confidence=0.7,
        status="planned",
    )

    hypotheses = store.list_runtime_session_hypotheses(session_id)

    assert hypotheses == [
        {
            "id": "hypo_1",
            "title": "Alias collision in Query.values",
            "summary": "Alias collision in Query.values",
            "confidence": 0.7,
            "status": "planned",
        }
    ]


def test_update_todo_keeps_semantic_sequence(store, session_id):
    from catocode.resolution_plan import update_todo

    update_todo(
        store=store,
        session_id=session_id,
        todo_id="todo_1",
        hypothesis_id="hypo_1",
        content="Add a failing regression around ambiguous status aliasing",
        kind="test",
        status="planned",
        sequence=1,
    )

    todos = store.list_runtime_session_todos(session_id)

    assert todos == [
        {
            "id": "todo_1",
            "hypothesis_id": "hypo_1",
            "content": "Add a failing regression around ambiguous status aliasing",
            "kind": "test",
            "status": "planned",
            "sequence": 1,
        }
    ]


def test_log_insight_persists_in_resolution_state(store, session_id):
    from catocode.resolution_plan import log_insight

    log_insight(
        store=store,
        session_id=session_id,
        hypothesis_id="hypo_1",
        todo_id="todo_2",
        insight="Earlier alias collection looks correct, but later disabling causes test failures.",
        source="test_feedback",
        impact="refine",
    )

    resolution = store.get_runtime_session_resolution(session_id)

    assert resolution["insights"] == [
        {
            "hypothesis_id": "hypo_1",
            "todo_id": "todo_2",
            "insight": "Earlier alias collection looks correct, but later disabling causes test failures.",
            "source": "test_feedback",
            "impact": "refine",
        }
    ]
