"""WebAppsCollector — versioned output via plist_version helper (VER-04)."""
from __future__ import annotations

import fnmatch
from pathlib import Path

from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.plist_version import get_plist_version

TITLE = "Web-installed Applications"
BASE = Path("/Applications")


class WebAppsCollector(Collector):
    """Collects web-installed applications by scanning /Applications/.

    Raw-write section: items written verbatim without flush_section.
    No availability guard — /Applications always exists on macOS.
    Each app emits "AppName.app (version)" when Info.plist is readable,
    or bare "AppName.app" when version is unavailable (VER-04, VER-05).
    The "Applications" root entry has no Info.plist and always emits name-only.
    Setapp* and *App Store* directories are excluded (filter logic unchanged).
    """

    TITLE = TITLE
    BASE = BASE

    # No available() override — always returns True (base class default).
    # The zsh has no availability check for /Applications.

    def _versioned_entry(self, p: Path) -> str:
        """Return 'name (version)' if Info.plist is readable, else bare 'name'."""
        plist_path = p / "Contents" / "Info.plist"
        version = get_plist_version(plist_path)
        if version:
            return f"{p.name} ({version})"
        return p.name

    def collect(self) -> CollectorResult:
        # Pitfall C: find includes the start path itself — prepend BASE.name ("Applications")
        # Root entry "Applications" has no Info.plist → name-only (no version lookup)
        entries: list[str] = [self.BASE.name]
        for p in self.BASE.iterdir():
            if not p.is_dir():
                continue
            if fnmatch.fnmatch(p.name, "Setapp*"):
                continue
            if fnmatch.fnmatch(p.name, "*App Store*"):
                continue
            entries.append(self._versioned_entry(p))
        entries.sort()
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=entries, raw=True)]
        )
