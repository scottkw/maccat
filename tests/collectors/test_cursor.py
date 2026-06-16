"""Tests for maccat.collectors.cursor.

Behavioral spec: update-list.sh lines 1494-1583 (collect_cursor_extensions).
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

from maccat.collectors.cursor import CursorCollector

# ===========================================================================
# CursorCollector
# ===========================================================================


class TestCursorCollector:
    """Tests for CursorCollector — mirrors test_vscode.py with ~/.cursor/extensions."""

    def test_cursor_cli_path_collects_extensions(self, tmp_path: Path) -> None:
        """Mock 'cursor' in PATH + subprocess returns extension line -> items populated."""
        cursor_extensions = tmp_path / "cursor_extensions"
        cursor_extensions.mkdir()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "ms-python.python@2025.1.0\n"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/cursor"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(CursorCollector, "_EXT_DIR", cursor_extensions),
        ):
            result = CursorCollector().collect()

        assert len(result.sections) == 1
        items = result.sections[0].items
        assert len(items) == 1
        assert "ms-python.python" in items[0]
        assert "2025.1.0" in items[0]

    def test_cursor_file_fallback(self, tmp_path: Path) -> None:
        """cursor absent; extensions.json at ~/.cursor/extensions/ -> items populated.
        """
        cursor_extensions = tmp_path / "cursor_extensions"
        cursor_extensions.mkdir()
        (cursor_extensions / "extensions.json").write_text(
            json.dumps([
                {
                    "identifier": {"id": "ms-python.python"},
                    "relativeLocation": "",
                    "version": "2025.1.0",
                }
            ]),
            encoding="utf-8",
        )

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(CursorCollector, "_EXT_DIR", cursor_extensions),
        ):
            result = CursorCollector().collect()

        items = result.sections[0].items
        assert len(items) == 1
        assert "ms-python.python" in items[0]

    def test_cursor_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Cursor Extensions'."""
        missing_dir = tmp_path / "nonexistent"
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(CursorCollector, "_EXT_DIR", missing_dir),
        ):
            result = CursorCollector().collect()
        assert result.sections[0].title == "Cursor Extensions"

    def test_cursor_raw_is_false(self, tmp_path: Path) -> None:
        """Section.raw must be False — Cursor extensions go through flush_section."""
        missing_dir = tmp_path / "nonexistent"
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(CursorCollector, "_EXT_DIR", missing_dir),
        ):
            result = CursorCollector().collect()
        assert result.sections[0].raw is False

    def test_cursor_uses_shared_helper(self) -> None:
        """CursorCollector.collect() delegates to _collect_editor_extensions — no duplication.
        """
        import maccat.collectors.cursor as cursor_mod  # noqa: PLC0415
        assert hasattr(cursor_mod, "CursorCollector")
        src = inspect.getsource(CursorCollector.collect)
        assert "_collect_editor_extensions" in src
