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

    Each entry routes through emit_item(name, version, id_) preserving the
    App Store numeric ID (MAS-01), producing 'AppName (version) [id]' lines.
    """

    def available(self) -> bool:
        return shutil.which("mas") is not None

    def _parse_mas_output(self, stdout: str) -> list[str]:
        """Extract id, multi-word name, and version from mas list output.

        Real mas list format: '<id>  <MultiWordName> (<version>)'
        Column 1: numeric App Store ID
        Columns 2..N-1: multi-word app name (joined with spaces)
        Column N: version wrapped in parens — strip before passing to emit_item.

        Routes through emit_item(name, version, id_) for FMT-01 compliance.
        """
        from maccat.catalog.format import emit_item

        lines: list[str] = []
        for line in stdout.splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            id_ = parts[0]
            last = parts[-1]
            if len(parts) >= 3 and last.startswith("(") and last.endswith(")"):
                version = last[1:-1]          # strip single parens; avoids ((version))
                name = " ".join(parts[1:-1])  # middle fields: multi-word app name
            else:
                version = ""                  # no version; degrade gracefully
                name = " ".join(parts[1:])
            item = emit_item(name, version, id_)
            if item is not None:
                lines.append(item)
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
        try:
            result = subprocess.run(
                ["mas", "list"], capture_output=True, text=True, shell=False
            )
        except OSError as exc:
            # TOCTOU / broken symlink / exec failure: warn-and-continue per the
            # project's graceful-degradation constraint instead of crashing the CLI.
            print(f"  WARNING: could not run mas: {exc}", file=sys.stderr)
            return CollectorResult(
                sections=[
                    Section(
                        title=TITLE,
                        items=["Could not retrieve App Store list."],
                        raw=True,
                    )
                ]
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
