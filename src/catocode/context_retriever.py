"""Context retriever — issue-aware code search.

Extracts hints (file paths, function names, error types) from issue text,
queries the code_definitions index, and assembles a structured code context
for prompt injection.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CodeHints:
    """Hints extracted from issue text for targeted code search."""
    file_paths: list[str] = field(default_factory=list)
    symbol_names: list[str] = field(default_factory=list)
    error_types: list[str] = field(default_factory=list)


@dataclass
class CodeContext:
    """Assembled code context ready for prompt injection."""
    relevant_definitions: list[dict] = field(default_factory=list)
    repo_map: str = ""

    def to_markdown(self) -> str:
        if not self.relevant_definitions:
            return ""

        sections = []
        sections.append("## Pre-loaded Code Context\n")
        sections.append("The following code locations were identified as potentially relevant. "
                       "Use this as a starting point — you may still need to explore further.\n")

        by_file: dict[str, list[dict]] = {}
        for d in self.relevant_definitions:
            fp = d["file_path"]
            by_file.setdefault(fp, []).append(d)

        for file_path, defs in by_file.items():
            sections.append(f"### `{file_path}`\n")
            for d in defs:
                symbol_label = f"{d['symbol_type']} `{d['symbol_name']}`"
                sections.append(f"**{symbol_label}** (lines {d['line_start']}-{d['line_end']})")
                sections.append(f"```\n{d['signature']}\n```\n")
                if d.get("body_preview"):
                    preview = d["body_preview"]
                    if len(preview) > 500:
                        preview = preview[:500] + "\n# ... (truncated)"
                    sections.append(f"<details><summary>Preview</summary>\n\n```\n{preview}\n```\n</details>\n")

        if self.repo_map:
            sections.append(f"### Repository Structure\n\n```\n{self.repo_map}\n```\n")

        return "\n".join(sections)


# --- Hint extraction ---

_FILE_PATH_RE = re.compile(
    r'(?:^|[\s"`\'(])('
    r'(?:[\w./-]+/)?'
    r'[\w.-]+'
    r'\.(?:py|js|jsx|ts|tsx|go|rs|java|rb|cpp|c|h)'
    r')(?:[\s"`\'),:]|$)',
    re.MULTILINE,
)

_BACKTICK_RE = re.compile(r'`(\w+(?:\.\w+)*(?:\(\))?)`')

_TRACEBACK_RE = re.compile(
    r'File "([^"]+)", line \d+, in (\w+)'
)

_ERROR_TYPE_RE = re.compile(
    r'\b(\w*(?:Error|Exception|Fault|Failure))\b'
)


def extract_code_hints(issue_text: str) -> CodeHints:
    hints = CodeHints()

    for match in _FILE_PATH_RE.finditer(issue_text):
        path = match.group(1)
        if path not in hints.file_paths:
            hints.file_paths.append(path)

    for match in _TRACEBACK_RE.finditer(issue_text):
        path, func = match.group(1), match.group(2)
        if path not in hints.file_paths:
            hints.file_paths.append(path)
        if func not in hints.symbol_names and func != "<module>":
            hints.symbol_names.append(func)

    for match in _BACKTICK_RE.finditer(issue_text):
        name = match.group(1).rstrip("()")
        if name not in hints.symbol_names and len(name) > 1:
            hints.symbol_names.append(name)

    for match in _ERROR_TYPE_RE.finditer(issue_text):
        etype = match.group(1)
        if etype not in hints.error_types:
            hints.error_types.append(etype)

    return hints


# --- Context building ---

def build_code_context(
    repo_id: str,
    issue_text: str,
    store,
    max_definitions: int = 15,
) -> CodeContext:
    hints = extract_code_hints(issue_text)
    seen: set[tuple[str, str, str]] = set()
    results: list[dict] = []

    def _add(defs: list[dict]) -> None:
        for d in defs:
            key = (d["file_path"], d["symbol_name"], d["symbol_type"])
            if key not in seen and len(results) < max_definitions:
                seen.add(key)
                results.append(d)

    for fp in hints.file_paths:
        defs = store.get_code_definitions(repo_id, file_path=fp)
        _add(defs)

    for name in hints.symbol_names:
        defs = store.search_code_definitions(repo_id, name_pattern=name)
        _add(defs)

    for fp in hints.file_paths:
        parts = fp.rsplit("/", 1)
        if len(parts) > 1:
            defs = store.search_code_definitions(repo_id, file_pattern=parts[0])
            _add(defs)

    return CodeContext(relevant_definitions=results)
