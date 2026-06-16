"""HomebrewCollector — raw-write byte-parity with update-list.sh:2233."""
from __future__ import annotations

import shutil
import subprocess
import sys

from maccat.collectors.base import Collector, CollectorResult, Section

TITLE = "Homebrew Packages"


class HomebrewCollector(Collector):
    """Collect Homebrew formulae and casks.

    Zsh analog: update-list.sh lines 2233-2242 (generate_catalog Homebrew section).
    Raw-write: returns Section(raw=True); orchestrator writes via write_lines(),
    NOT flush_section().
    """

    def available(self) -> bool:
        return shutil.which("brew") is not None

    def _run(self, cmd: list[str]) -> list[str]:
        """Run a command and return stdout lines.

        Returns [] on non-zero exit or empty output.
        """
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        if result.returncode != 0:
            return []
        return result.stdout.rstrip("\n").split("\n") if result.stdout.strip() else []

    def collect(self) -> CollectorResult:
        if not self.available():
            print("  WARNING: brew not found.", file=sys.stderr)
            return CollectorResult(
                sections=[
                    Section(
                        title=TITLE,
                        items=["Homebrew is not installed."],
                        raw=True,
                    )
                ]
            )
        formulae = self._run(["brew", "list", "--formula"])
        casks = self._run(["brew", "list", "--cask"])
        lines = formulae + casks
        return CollectorResult(sections=[Section(title=TITLE, items=lines, raw=True)])
