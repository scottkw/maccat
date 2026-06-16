"""Collector ABC, Section, and CollectorResult — base types for all maccat source collectors."""
from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Collector", "CollectorResult", "Section"]


@dataclass
class Section:
    title: str
    items: list[str]  # raw emit_item() output lines — NOT yet sorted
    raw: bool = False  # if True, orchestrator writes items directly without flush_section
                       # raw=True: Homebrew, App Store, Setapp, Web-installed


@dataclass
class CollectorResult:
    sections: list[Section]
    warnings: list[str] = field(default_factory=list)


class Collector:
    """Abstract base. Subclasses implement collect()."""

    def collect(self) -> CollectorResult:
        raise NotImplementedError

    def available(self) -> bool:
        """Override to gate on tool presence or directory existence."""
        return True

    def degraded_result(self, title: str) -> CollectorResult:
        """Standard empty-section result. items=[] causes flush_section → '  (none found)'."""
        return CollectorResult(sections=[Section(title=title, items=[])])
