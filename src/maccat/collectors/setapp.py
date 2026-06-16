"""SetappCollector — raw-write byte-parity with update-list.sh:2267 (Setapp section)."""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.base import Collector, CollectorResult, Section

TITLE = "Setapp Applications"
BASE = Path("/Applications/Setapp")


class SetappCollector(Collector):
    """Collects Setapp applications by scanning /Applications/Setapp/.

    Raw-write section: items written verbatim without flush_section.
    Zsh parity: find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} ; | sort
    """

    TITLE = TITLE
    BASE = BASE

    def available(self) -> bool:
        return self.BASE.is_dir()

    def collect(self) -> CollectorResult:
        if not self.available():
            return CollectorResult(
                sections=[
                    Section(
                        title=self.TITLE,
                        items=["Setapp is not installed or detected."],
                        raw=True,
                    )
                ]
            )
        # Pitfall C: find includes the start path itself — prepend BASE.name ("Setapp")
        entries: list[str] = [self.BASE.name]
        entries += [p.name for p in self.BASE.iterdir() if p.is_dir()]
        entries.sort()
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=entries, raw=True)]
        )
