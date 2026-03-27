from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

RUN_ACTIVITY_PATH = Path(__file__).resolve().parents[1] / "src/catocode/container/scripts/run_activity.py"


def _load_run_activity_module(monkeypatch, fake_sdk: types.ModuleType):
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", fake_sdk)
    spec = importlib.util.spec_from_file_location("catocode_run_activity_test", RUN_ACTIVITY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_activity_consumes_sdk_stream_to_completion(monkeypatch):
    events: list[str] = []

    fake_sdk = types.ModuleType("claude_agent_sdk")

    class AssistantMessage:
        def __init__(self, content):
            self.content = content

    class ResultMessage:
        def __init__(self, result: str, *, is_error: bool = False):
            self.result = result
            self.is_error = is_error
            self.total_cost_usd = 0.12
            self.session_id = "sdk-session-1"
            self.num_turns = 2
            self.duration_ms = 345

    class SystemMessage:
        def __init__(self, subtype: str):
            self.subtype = subtype

    class TextBlock:
        def __init__(self, text: str):
            self.text = text

    class ToolUseBlock:
        def __init__(self, block_id: str, name: str, input: dict):
            self.id = block_id
            self.name = name
            self.input = input

    class ToolResultBlock:
        def __init__(self, tool_use_id: str, content: str, *, is_error: bool = False):
            self.tool_use_id = tool_use_id
            self.content = content
            self.is_error = is_error

    class ClaudeAgentOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    async def fake_query(*, prompt: str, options: ClaudeAgentOptions):
        events.append(f"prompt:{prompt}")
        events.append(f"cwd:{options.kwargs['cwd']}")
        yield ResultMessage("done")
        events.append("after_result")

    fake_sdk.AssistantMessage = AssistantMessage
    fake_sdk.ResultMessage = ResultMessage
    fake_sdk.SystemMessage = SystemMessage
    fake_sdk.TextBlock = TextBlock
    fake_sdk.ToolUseBlock = ToolUseBlock
    fake_sdk.ToolResultBlock = ToolResultBlock
    fake_sdk.ClaudeAgentOptions = ClaudeAgentOptions
    fake_sdk.query = fake_query

    module = _load_run_activity_module(monkeypatch, fake_sdk)
    emitted: list[dict] = []
    monkeypatch.setattr(module, "_emit", emitted.append)

    exit_code = asyncio.run(module.run("investigate issue", 4, "/tmp"))

    assert exit_code == 0
    assert "after_result" in events
    assert emitted[-1] == {
        "type": "result",
        "result": "done",
        "is_error": False,
        "cost_usd": 0.12,
        "session_id": "sdk-session-1",
        "num_turns": 2,
        "duration_ms": 345,
    }
