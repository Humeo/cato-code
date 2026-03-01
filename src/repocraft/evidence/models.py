from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Phase(str, Enum):
    REPRODUCE = "reproduce"
    FIX = "fix"
    VERIFY = "verify"


class EvidenceType(str, Enum):
    COMMAND_OUTPUT = "command_output"
    FILE_CONTENT = "file_content"
    ERROR_OUTPUT = "error_output"
    TEST_RESULT = "test_result"
    DIFF = "diff"
    OBSERVATION = "observation"
    CONCLUSION = "conclusion"


@dataclass
class EvidenceItem:
    phase: Phase
    evidence_type: EvidenceType
    title: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PhaseResult:
    phase: Phase
    success: bool
    summary: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    cost_usd: float = 0.0
    num_turns: int = 0
    error: str | None = None


@dataclass
class RunReport:
    repo_url: str
    issue_number: int
    issue_title: str
    phases: list[PhaseResult] = field(default_factory=list)
    overall_success: bool = False
    total_cost_usd: float = 0.0
    diff: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_phase(self, result: PhaseResult) -> None:
        self.phases.append(result)
        self.total_cost_usd += result.cost_usd
