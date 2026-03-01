from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from ..container.manager import ContainerManager

logger = logging.getLogger(__name__)

MAX_OUTPUT_CHARS = 50_000


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n\n... [OUTPUT TRUNCATED: {len(text)} chars total] ...\n\n" + text[-half:]


def create_container_tools(container_mgr: ContainerManager):
    @tool(
        "container_exec",
        "Execute a shell command inside the Docker container in /workspace/repo",
        {"command": str, "workdir": str},
    )
    async def container_exec(args: dict[str, Any]) -> dict[str, Any]:
        command = args["command"]
        workdir = args.get("workdir", "/workspace/repo")
        logger.debug("container_exec: %s", command[:80])
        try:
            result = container_mgr.exec_sync(command, workdir=workdir)
            output = _truncate(result.combined)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"exit_code={result.exit_code}\n{output}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "is_error": True,
            }

    @tool(
        "container_read",
        "Read a file from inside the Docker container",
        {"path": str},
    )
    async def container_read(args: dict[str, Any]) -> dict[str, Any]:
        path = args["path"]
        logger.debug("container_read: %s", path)
        try:
            content = container_mgr.read_file(path)
            return {"content": [{"type": "text", "text": _truncate(content)}]}
        except FileNotFoundError:
            return {
                "content": [{"type": "text", "text": f"File not found: {path}"}],
                "is_error": True,
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error reading file: {e}"}],
                "is_error": True,
            }

    @tool(
        "container_write",
        "Write content to a file inside the Docker container",
        {"path": str, "content": str},
    )
    async def container_write(args: dict[str, Any]) -> dict[str, Any]:
        path = args["path"]
        content = args["content"]
        logger.debug("container_write: %s (%d chars)", path, len(content))
        try:
            container_mgr.write_file(path, content)
            return {"content": [{"type": "text", "text": f"Written {len(content)} chars to {path}"}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error writing file: {e}"}],
                "is_error": True,
            }

    @tool(
        "container_list_files",
        "List files in a directory inside the Docker container (max depth 3)",
        {"path": str},
    )
    async def container_list_files(args: dict[str, Any]) -> dict[str, Any]:
        path = args.get("path", "/workspace/repo")
        logger.debug("container_list_files: %s", path)
        try:
            listing = container_mgr.list_files(path)
            return {"content": [{"type": "text", "text": _truncate(listing)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error listing files: {e}"}],
                "is_error": True,
            }

    server = create_sdk_mcp_server(
        name="container",
        version="1.0.0",
        tools=[container_exec, container_read, container_write, container_list_files],
    )
    tool_names = [
        "mcp__container__container_exec",
        "mcp__container__container_read",
        "mcp__container__container_write",
        "mcp__container__container_list_files",
    ]
    return server, tool_names
