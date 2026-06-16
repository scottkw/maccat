"""MasCollector — raw-write byte-parity with update-list.sh:2249."""
from __future__ import annotations

import shutil
import subprocess
import sys

from maccat.collectors.base import Collector, CollectorResult, Section

TITLE = "App Store Applications"


class MasCollector(Collector):
    """Collect Mac App Store applications via the 'mas' CLI.

    Zsh analog: update-list.sh lines 2249-2260 (generate_catalog App Store section).
    Raw-write: returns Section(raw=True); orchestrator writes via write_lines(),
    NOT flush_section().

    Awk equivalence: mas list 2>/dev/null | awk '{print $2, $3}'
    Column 1 is the numeric App Store ID (skipped); columns 2-3 are AppName and (version).
    """

    def available(self) -> bool:
        return shutil.which("mas") is not None

    def _parse_mas_output(self, stdout: str) -> list[str]:
        """Python equivalent of awk '{print $2, $3}'.

        Extracts AppName and (version) columns from mas list output.
        Column 1 is the numeric App Store ID and is skipped.
        """
        lines = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                lines.append(f"{parts[1]} {parts[2]}")
            elif len(parts) == 2:
                # awk '{print $2, $3}' emits "$2 " (trailing space) when $3 is empty.
                lines.append(f"{parts[1]} ")
            # PARITY DEVIATION (intentional, WR-02): a 0/1-field or blank line makes
            # awk '{print $2, $3}' emit a lone " " (space-only line); we drop it
            # instead. Real `mas list` always emits >=3 fields, so this only differs
            # on degenerate input and does not affect golden parity on real data.
        return lines

    def collect(self) -> CollectorResult:
        if not self.available():
            print(
                "  WARNING: mas CLI is not installed. Install with: brew install mas",
                file=sys.stderr,
            )
            return CollectorResult(
                sections=[
                    Section(
                        title=TITLE,
                        items=[
                            "mas (Mac App Store CLI) is not installed.",
                            "Install it with Homebrew: brew install mas",
                        ],
                        raw=True,
                    )
                ]
            )
        result = subprocess.run(
            ["mas", "list"], capture_output=True, text=True, shell=False
        )
        if result.returncode != 0:
            return CollectorResult(
                sections=[
                    Section(
                        title=TITLE,
                        items=["Could not retrieve App Store list."],
                        raw=True,
                    )
                ]
            )
        lines = self._parse_mas_output(result.stdout)
        return CollectorResult(sections=[Section(title=TITLE, items=lines, raw=True)])
