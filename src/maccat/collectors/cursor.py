"""CursorCollector — identical to VSCodeCollector with ~/.cursor/extensions and 'cursor' CLI.

Byte-parity with update-list.sh:1494 (collect_cursor_extensions).
Delegates entirely to _collect_editor_extensions from vscode.py — no logic duplication.
"""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.collectors.vscode import _collect_editor_extensions

__all__ = ["CursorCollector"]


class CursorCollector(Collector):
    """Collect Cursor editor extensions.

    Zsh analog: update-list.sh lines 1494-1583 (collect_cursor_extensions).
    Substitutions from VS Code: ext_dir = ~/.cursor/extensions, cli_name = "cursor".
    """

    TITLE = "Cursor Extensions"
    _EXT_DIR = Path.home() / ".cursor/extensions"

    def collect(self) -> CollectorResult:
        items, warnings = _collect_editor_extensions(self._EXT_DIR, "cursor", self.TITLE)
        return CollectorResult(
            sections=[Section(title=self.TITLE, items=items)],
            warnings=warnings,
        )
