from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoCraftConfig:
    repo_url: str
    issue_number: int
    owner: str = field(init=False)
    repo: str = field(init=False)
    container_image: str = "repocraft-base:latest"
    model: str = "claude-sonnet-4-5-20251001"
    max_turns_per_phase: int = 30
    max_budget_usd: float = 10.0
    output_dir: Path = field(default_factory=lambda: Path("output"))
    github_token: str | None = field(
        default_factory=lambda: os.environ.get("GITHUB_TOKEN")
    )

    def __post_init__(self) -> None:
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/?",
            self.repo_url,
        )
        if not match:
            raise ValueError(f"Cannot parse GitHub repo URL: {self.repo_url!r}")
        self.owner = match.group(1)
        self.repo = match.group(2)
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
