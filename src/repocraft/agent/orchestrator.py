from __future__ import annotations

import logging
from typing import Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from ..container.manager import ContainerManager
from ..evidence.collector import EvidenceCollector
from ..evidence.models import Phase, PhaseResult, RunReport
from ..github.issue_fetcher import GitHubIssue
from ..tools.container_tools import create_container_tools
from ..tools.evidence_tools import create_evidence_tools
from .prompts import (
    SYSTEM_PROMPT,
    build_fix_prompt,
    build_reproduce_prompt,
    build_verify_prompt,
)

logger = logging.getLogger(__name__)

POSITIVE_SIGNALS = {
    Phase.REPRODUCE: ["REPRODUCED: YES"],
    Phase.FIX: ["FIXED: YES"],
    Phase.VERIFY: ["VERIFIED: YES"],
}

NEGATIVE_SIGNALS = {
    Phase.REPRODUCE: ["REPRODUCED: NO"],
    Phase.FIX: ["FIXED: NO"],
    Phase.VERIFY: ["VERIFIED: NO"],
}


class AgentOrchestrator:
    def __init__(
        self,
        container_mgr: ContainerManager,
        model: str,
        max_turns_per_phase: int,
        max_budget_usd: float,
        on_event: Callable[[str, str], None] | None = None,
    ) -> None:
        self._container_mgr = container_mgr
        self._model = model
        self._max_turns = max_turns_per_phase
        self._max_budget = max_budget_usd
        self._on_event = on_event or (lambda event, msg: None)

    async def run(self, issue: GitHubIssue) -> RunReport:
        report = RunReport(
            repo_url=f"https://github.com/{issue.url}",
            issue_number=issue.number,
            issue_title=issue.title,
        )
        collector = EvidenceCollector()

        # Phase 1: Reproduce
        self._on_event("phase_start", "Phase 1: Reproducing the bug...")
        reproduce_result = await self._run_phase(
            phase=Phase.REPRODUCE,
            prompt=build_reproduce_prompt(issue),
            collector=collector,
        )
        report.add_phase(reproduce_result)
        self._on_event("phase_end", f"Reproduce: {'SUCCESS' if reproduce_result.success else 'FAILED'}")

        if not reproduce_result.success:
            report.overall_success = False
            return report

        # Phase 2: Fix
        repro_summary = collector.get_summary_for_phase(Phase.REPRODUCE)
        self._on_event("phase_start", "Phase 2: Fixing the bug...")
        fix_result = await self._run_phase(
            phase=Phase.FIX,
            prompt=build_fix_prompt(issue, repro_summary),
            collector=collector,
        )
        report.add_phase(fix_result)
        self._on_event("phase_end", f"Fix: {'SUCCESS' if fix_result.success else 'FAILED'}")

        if not fix_result.success:
            report.overall_success = False
            return report

        # Phase 3: Verify
        fix_summary = collector.get_summary_for_phase(Phase.FIX)
        self._on_event("phase_start", "Phase 3: Verifying the fix...")
        verify_result = await self._run_phase(
            phase=Phase.VERIFY,
            prompt=build_verify_prompt(issue, repro_summary, fix_summary),
            collector=collector,
        )
        report.add_phase(verify_result)
        self._on_event("phase_end", f"Verify: {'SUCCESS' if verify_result.success else 'FAILED'}")

        # Collect diff
        diff_result = self._container_mgr.exec_sync("git diff HEAD")
        report.diff = diff_result.stdout

        report.overall_success = verify_result.success
        return report

    async def _run_phase(
        self,
        phase: Phase,
        prompt: str,
        collector: EvidenceCollector,
    ) -> PhaseResult:
        container_server, container_tool_names = create_container_tools(self._container_mgr)
        evidence_server, evidence_tool_name = create_evidence_tools(collector, phase)

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={
                "container": container_server,
                "evidence": evidence_server,
            },
            allowed_tools=container_tool_names + [evidence_tool_name],
            model=self._model,
            max_turns=self._max_turns,
            max_budget_usd=self._max_budget,
        )

        full_text = ""
        cost_usd = 0.0
        num_turns = 0
        error: str | None = None

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for msg in client.receive_messages():
                    if isinstance(msg, AssistantMessage):
                        num_turns += 1
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                full_text += block.text + "\n"
                                self._on_event("text", block.text)
                    elif isinstance(msg, ResultMessage):
                        if msg.total_cost_usd:
                            cost_usd = msg.total_cost_usd
                        if msg.num_turns:
                            num_turns = msg.num_turns
        except Exception as e:
            logger.error("Phase %s error: %s", phase.value, e)
            error = str(e)

        success = self._parse_phase_success(phase, full_text)
        summary = self._extract_conclusion(full_text) or (
            f"Phase {phase.value} completed. Success: {success}"
        )

        return PhaseResult(
            phase=phase,
            success=success,
            summary=summary,
            evidence=collector.get_by_phase(phase),
            cost_usd=cost_usd,
            num_turns=num_turns,
            error=error,
        )

    def _parse_phase_success(self, phase: Phase, text: str) -> bool:
        text_upper = text.upper()
        for signal in POSITIVE_SIGNALS[phase]:
            if signal.upper() in text_upper:
                return True
        return False

    def _extract_conclusion(self, text: str) -> str:
        lines = text.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line and len(line) > 10:
                return line[:500]
        return ""
