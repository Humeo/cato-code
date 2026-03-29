from __future__ import annotations

from typing import Any

from .store import Store


def _load_resolution(store: Store, session_id: str) -> dict[str, Any]:
    resolution = store.get_runtime_session_resolution(session_id)
    if resolution is None:
        return {
            "hypotheses": [],
            "todos": [],
            "checkpoints": [],
            "insights": [],
        }
    resolution.setdefault("hypotheses", [])
    resolution.setdefault("todos", [])
    resolution.setdefault("checkpoints", [])
    resolution.setdefault("insights", [])
    return resolution


def _upsert_by_id(items: list[dict[str, Any]], item_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    updated = False
    normalized: list[dict[str, Any]] = []
    for item in items:
        if item.get("id") == item_id:
            normalized.append(payload)
            updated = True
        else:
            normalized.append(dict(item))
    if not updated:
        normalized.append(payload)
    return normalized


def update_hypothesis(
    *,
    store: Store,
    session_id: str,
    hypothesis_id: str,
    title: str,
    confidence: float | None = None,
    status: str = "planned",
    description: str | None = None,
    location_refs: list[str] | None = None,
) -> dict[str, Any]:
    resolution = _load_resolution(store, session_id)
    payload = {
        "id": hypothesis_id,
        "title": title,
        "summary": title,
        "confidence": confidence,
        "status": status,
    }
    if description:
        payload["description"] = description
    if location_refs:
        payload["location_refs"] = list(location_refs)
    resolution["hypotheses"] = _upsert_by_id(resolution["hypotheses"], hypothesis_id, payload)
    store.replace_runtime_session_resolution(session_id, resolution)
    return payload


def update_todo(
    *,
    store: Store,
    session_id: str,
    todo_id: str,
    hypothesis_id: str,
    content: str,
    kind: str,
    status: str = "planned",
    sequence: int | None = None,
) -> dict[str, Any]:
    resolution = _load_resolution(store, session_id)
    payload = {
        "id": todo_id,
        "hypothesis_id": hypothesis_id,
        "content": content,
        "kind": kind,
        "status": status,
    }
    if sequence is not None:
        payload["sequence"] = sequence
    resolution["todos"] = _upsert_by_id(resolution["todos"], todo_id, payload)
    store.replace_runtime_session_resolution(session_id, resolution)
    return payload


def log_insight(
    *,
    store: Store,
    session_id: str,
    hypothesis_id: str,
    insight: str,
    source: str,
    impact: str,
    todo_id: str | None = None,
) -> dict[str, Any]:
    resolution = _load_resolution(store, session_id)
    payload = {
        "hypothesis_id": hypothesis_id,
        "todo_id": todo_id,
        "insight": insight,
        "source": source,
        "impact": impact,
    }
    resolution["insights"] = [dict(item) for item in resolution.get("insights", [])]
    resolution["insights"].append(payload)
    store.replace_runtime_session_resolution(session_id, resolution)
    return payload
