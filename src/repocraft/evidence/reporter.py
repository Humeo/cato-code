from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import RunReport


class ReportGenerator:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: RunReport) -> dict[str, Path]:
        slug = f"issue-{report.issue_number}"
        paths: dict[str, Path] = {}

        paths["markdown"] = self._write_markdown(report, slug)
        paths["json"] = self._write_json(report, slug)
        if report.diff:
            paths["patch"] = self._write_patch(report, slug)

        return paths

    def _write_markdown(self, report: RunReport, slug: str) -> Path:
        path = self._output_dir / f"{slug}-report.md"
        lines: list[str] = []

        status_emoji = "✅" if report.overall_success else "❌"
        lines += [
            f"# RepoCraft Report — {status_emoji} Issue #{report.issue_number}",
            f"",
            f"**Issue:** {report.issue_title}",
            f"**Repository:** {report.repo_url}",
            f"**Status:** {'SUCCESS' if report.overall_success else 'FAILED'}",
            f"**Total Cost:** ${report.total_cost_usd:.4f} USD",
            f"**Generated:** {report.created_at}",
            f"",
            "---",
            "",
        ]

        for phase_result in report.phases:
            phase_status = "✅ PASSED" if phase_result.success else "❌ FAILED"
            lines += [
                f"## Phase: {phase_result.phase.value.upper()} — {phase_status}",
                f"",
                f"**Summary:** {phase_result.summary}",
                f"**Turns:** {phase_result.num_turns} | **Cost:** ${phase_result.cost_usd:.4f} USD",
            ]
            if phase_result.error:
                lines += [f"**Error:** {phase_result.error}"]
            lines += [""]

            if phase_result.evidence:
                lines += ["### Evidence\n"]
                for item in phase_result.evidence:
                    lines += [
                        f"#### [{item.evidence_type.value}] {item.title}",
                        f"",
                        f"```",
                        item.content[:5000],
                        f"```",
                        f"",
                    ]

        if report.diff:
            lines += [
                "---",
                "",
                "## Git Diff (Patch)",
                "",
                "```diff",
                report.diff[:20000],
                "```",
                "",
            ]

        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_json(self, report: RunReport, slug: str) -> Path:
        path = self._output_dir / f"{slug}-report.json"
        data = asdict(report)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def _write_patch(self, report: RunReport, slug: str) -> Path:
        path = self._output_dir / f"{slug}.patch"
        path.write_text(report.diff, encoding="utf-8")
        return path
