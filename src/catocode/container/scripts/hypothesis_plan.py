#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

STATE_FILE = Path(".catocode") / "hypothesis_plan_state.json"


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"hypotheses": [], "todos": [], "insights": []}
    return json.loads(STATE_FILE.read_text())


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _arg_value(flag: str) -> str | None:
    if flag not in sys.argv:
        return None
    index = sys.argv.index(flag)
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _upsert(items: list[dict], item_id: str, payload: dict) -> list[dict]:
    updated = False
    result: list[dict] = []
    for item in items:
        if item.get("id") == item_id:
            result.append(payload)
            updated = True
        else:
            result.append(item)
    if not updated:
        result.append(payload)
    return result


def update_hypothesis() -> dict:
    hypothesis_id = _arg_value("--hypothesis_id") or _arg_value("--id")
    title = _arg_value("--title")
    if not hypothesis_id or not title:
        raise SystemExit("usage: hypothesis_plan update_hypothesis --hypothesis_id <id> --title <title>")
    state = _load_state()
    payload = {
        "id": hypothesis_id,
        "title": title,
        "summary": title,
        "confidence": float(_arg_value("--confidence") or 0.0) if _arg_value("--confidence") else None,
        "status": _arg_value("--status") or "planned",
    }
    state["hypotheses"] = _upsert(state.get("hypotheses", []), hypothesis_id, payload)
    _save_state(state)
    return payload


def update_todo() -> dict:
    todo_id = _arg_value("--todo_id") or _arg_value("--id")
    hypothesis_id = _arg_value("--hypothesis_id")
    content = _arg_value("--content")
    if not todo_id or not hypothesis_id or not content:
        raise SystemExit(
            "usage: hypothesis_plan update_todo --todo_id <id> --hypothesis_id <id> --content <text>"
        )
    state = _load_state()
    payload = {
        "id": todo_id,
        "hypothesis_id": hypothesis_id,
        "content": content,
        "kind": _arg_value("--kind") or "edit",
        "status": _arg_value("--status") or "planned",
    }
    if _arg_value("--sequence"):
        payload["sequence"] = int(_arg_value("--sequence"))
    state["todos"] = _upsert(state.get("todos", []), todo_id, payload)
    _save_state(state)
    return payload


def log_insight() -> dict:
    hypothesis_id = _arg_value("--hypothesis_id")
    insight = _arg_value("--insight")
    if not hypothesis_id or not insight:
        raise SystemExit("usage: hypothesis_plan log_insight --hypothesis_id <id> --insight <text>")
    state = _load_state()
    payload = {
        "hypothesis_id": hypothesis_id,
        "todo_id": _arg_value("--todo_id"),
        "insight": insight,
        "source": _arg_value("--source") or "runtime_feedback",
        "impact": _arg_value("--impact") or "refine",
    }
    state["insights"] = list(state.get("insights", []))
    state["insights"].append(payload)
    _save_state(state)
    return payload


COMMANDS = {
    "update_hypothesis": update_hypothesis,
    "update_todo": update_todo,
    "log_insight": log_insight,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit("usage: hypothesis_plan <update_hypothesis|update_todo|log_insight> ...")
    result = COMMANDS[sys.argv[1]]()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
