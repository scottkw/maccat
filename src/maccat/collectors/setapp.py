"""SetappCollector — versioned output via plist_version helper (VER-03)."""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.plist_version import get_plist_version

TITLE = "Setapp Applications"
BASE = Path("/Applications/Setapp")


class SetappCollector(Collector):
    """Collects Setapp applications by scanning /Applications/Setapp/.

    Raw-write section: items written verbatim without flush_section.
    Each app emits "AppName.app (version)" when Info.plist is readable,
    or bare "AppName.app" when version is unavailable (VER-03, VER-05).
    The "Setapp" container entry has no Info.plist and always emits name-only.
    """

    TITLE = TITLE
    BASE = BASE

    def available(self) -> bool:
        return self.BASE.is_dir()

    def _versioned_entry(self, p: Path) -> str:
        """Return 'name (version)' if Info.plist is readable, else bare 'name'."""
        plist_path = p / "Contents" / "Info.plist"
        version = get_plist_version(plist_path)
        if version:
            return f"{p.name} ({version})"
        return p.name

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
        # Container entry "Setapp" has no Info.plist → name-only (no version lookup)
        entries: list[str] = [self.BASE.name]
        entries += [self._versioned_entry(p) for p in self.BASE.iterdir() if p.is_dir()]
        entries.sort()
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=entries, raw=True)]
        )
