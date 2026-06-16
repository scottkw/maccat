"""WebAppsCollector — raw-write byte-parity with update-list.sh:2281 (Web-installed section)."""
from __future__ import annotations

import fnmatch
from pathlib import Path

from maccat.collectors.base import Collector, CollectorResult, Section

TITLE = "Web-installed Applications"
BASE = Path("/Applications")


class WebAppsCollector(Collector):
    """Collects web-installed applications by scanning /Applications/.

    Raw-write section: items written verbatim without flush_section.
    No availability guard — /Applications always exists on macOS.
    Zsh parity:
      find "/Applications" -maxdepth 1 -type d \\
          -not -path "/Applications/Setapp*" \\
          -not -path "/Applications/*App Store*" \\
          -exec basename {} ; | sort
    """

    TITLE = TITLE
    BASE = BASE

    # No available() override — always returns True (base class default).
    # The zsh has no availability check for /Applications.

    def collect(self) -> CollectorResult:
        # Pitfall C: find includes the start path itself — prepend BASE.name ("Applications")
        entries: list[str] = [self.BASE.name]
        for p in self.BASE.iterdir():
            if not p.is_dir():
                continue
            if fnmatch.fnmatch(p.name, "Setapp*"):
                continue
            if fnmatch.fnmatch(p.name, "*App Store*"):
                continue
            entries.append(p.name)
        entries.sort()
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=entries, raw=True)]
        )
