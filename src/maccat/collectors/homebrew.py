"""HomebrewCollector — versioned formulae + cask output (VER-01 / VER-02)."""
from __future__ import annotations

import shutil
import subprocess
import sys

from maccat.collectors.base import Collector, CollectorResult, Section

TITLE = "Homebrew Packages"


class HomebrewCollector(Collector):
    """Collect Homebrew formulae and casks with versions.

    Uses ``brew list --formula --versions`` / ``--cask --versions`` so each line
    is ``name version [version2 ...]``. Every installed version is preserved,
    space-joined inside the parens (VER-01/VER-02), e.g. ``python@3.11 (3.11.1 3.11.2)``.

    Formulae are intersected with ``brew leaves`` so only top-level
    (user-installed) formulae are cataloged — transitive dependencies are
    dropped, since Homebrew re-resolves them on install. ``brew leaves`` prints
    names only, so it is used purely as a filter over the versioned list, which
    stays the source of both line content and ordering. Casks are listed in
    full: ``brew leaves`` covers formulae only.

    Raw-write: returns Section(raw=True); orchestrator writes via write_lines(),
    NOT flush_section() (ordering from ``brew`` is preserved for determinism, VER-06).
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

    def _parse_brew_versions_line(self, line: str) -> str:
        """Format one ``brew list --versions`` line as ``name (version...)``.

        - ``"git 2.44.0"``                → ``"git (2.44.0)"``
        - ``"python@3.11 3.11.1 3.11.2"`` → ``"python@3.11 (3.11.1 3.11.2)"`` (all versions)
        - ``"git"`` (no version)          → ``"git"`` (graceful degradation, VER-05)
        - ``""``                          → ``""`` (filtered out by caller)
        """
        tokens = line.split()
        if not tokens:
            return ""
        name = tokens[0]
        versions = tokens[1:]
        if not versions:
            return name
        return f"{name} ({' '.join(versions)})"

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
        # Call order is a test contract — do not reorder.
        formulae = self._run(["brew", "list", "--formula", "--versions"])
        leaves = self._run(["brew", "leaves"])
        casks = self._run(["brew", "list", "--cask", "--versions"])
        leaf_names = {tokens[0] for line in leaves if (tokens := line.split())}
        if leaf_names:
            formulae = [
                line
                for line in formulae
                if (tokens := line.split()) and tokens[0] in leaf_names
            ]
        items = [
            entry
            for line in formulae + casks
            if (entry := self._parse_brew_versions_line(line))
        ]
        return CollectorResult(sections=[Section(title=TITLE, items=items, raw=True)])
