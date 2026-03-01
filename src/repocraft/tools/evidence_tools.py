from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from ..evidence.collector import EvidenceCollector
from ..evidence.models import EvidenceType, Phase

logger = logging.getLogger(__name__)


def create_evidence_tools(collector: EvidenceCollector, current_phase: Phase):
    @tool(
        "capture_evidence",
        "Capture evidence from the current phase. Call this to record important findings, command outputs, test results, or conclusions.",
        {
            "evidence_type": str,
            "title": str,
            "content": str,
        },
    )
    async def capture_evidence(args: dict[str, Any]) -> dict[str, Any]:
        raw_type = args.get("evidence_type", "observation")
        try:
            etype = EvidenceType(raw_type)
        except ValueError:
            etype = EvidenceType.OBSERVATION

        title = args["title"]
        content = args["content"]
        logger.debug("capture_evidence [%s] %s", etype.value, title[:60])
        collector.add(
            phase=current_phase,
            evidence_type=etype,
            title=title,
            content=content,
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Evidence captured: [{etype.value}] {title}",
                }
            ]
        }

    server = create_sdk_mcp_server(
        name="evidence",
        version="1.0.0",
        tools=[capture_evidence],
    )
    tool_name = "mcp__evidence__capture_evidence"
    return server, tool_name
