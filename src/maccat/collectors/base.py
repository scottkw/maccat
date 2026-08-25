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
        """Override to gate on tool presence or directory existence.

        Deliberately NOT called by the orchestrator. The three collectors that
        use it (homebrew.py, mas.py, setapp.py) call it from INSIDE their own
        collect(); webapps.py relies on this True default.

        The cli.py registry loop must not gate on this. A collector whose tool
        is absent still has to emit its section — HomebrewCollector emits a
        section whose single item is the "Homebrew is not installed." notice —
        so gating centrally would silently drop those notice sections and
        destabilise the fixed 22-section catalog set.
        """
        return True
