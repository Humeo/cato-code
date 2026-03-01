from __future__ import annotations

from .models import EvidenceItem, EvidenceType, Phase


class EvidenceCollector:
    def __init__(self) -> None:
        self._items: list[EvidenceItem] = []

    def add(
        self,
        phase: Phase,
        evidence_type: EvidenceType,
        title: str,
        content: str,
    ) -> EvidenceItem:
        item = EvidenceItem(
            phase=phase,
            evidence_type=evidence_type,
            title=title,
            content=content,
        )
        self._items.append(item)
        return item

    def get_by_phase(self, phase: Phase) -> list[EvidenceItem]:
        return [i for i in self._items if i.phase == phase]

    def get_all(self) -> list[EvidenceItem]:
        return list(self._items)

    def get_summary_for_phase(self, phase: Phase, max_chars: int = 8000) -> str:
        items = self.get_by_phase(phase)
        if not items:
            return f"No evidence collected for phase: {phase.value}"

        parts: list[str] = [f"## Evidence from {phase.value.upper()} phase\n"]
        total = len(parts[0])
        for item in items:
            entry = f"### [{item.evidence_type.value}] {item.title}\n{item.content}\n\n"
            if total + len(entry) > max_chars:
                parts.append("... (truncated)\n")
                break
            parts.append(entry)
            total += len(entry)
        return "".join(parts)
