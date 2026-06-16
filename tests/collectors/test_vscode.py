"""Tests for maccat.collectors.vscode.

Behavioral spec: update-list.sh lines 1387-1476 (collect_vscode_extensions).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

from maccat.collectors.vscode import VSCodeCollector

# ===========================================================================
# CLI path (Path A)
# ===========================================================================


class TestVSCodeCLIPath:
    """Tests for VSCodeCollector when CLI is present and returns extension lines."""

    def test_cli_path_collects_extensions(self, tmp_path: Path) -> None:
        """Mock 'code' in PATH + subprocess returns extension line -> items contain id and version.

        No extensions.json present so relativeLocation is absent -> display_name = id_.
        """
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "ms-python.python@2025.1.0\n"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/code"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        assert len(result.sections) == 1
        items = result.sections[0].items
        assert len(items) == 1
        # No relativeLocation -> display_name falls back to id_; id-as-name promotion in emit_item
        assert "ms-python.python" in items[0]
        assert "2025.1.0" in items[0]

    def test_cli_path_resolves_display_name(self, tmp_path: Path) -> None:
        """CLI output + extensions.json with relativeLocation -> name resolved via package.json."""
        extensions_dir = tmp_path / "extensions"
        # Create package.json with display name
        pkg_dir = extensions_dir / "ms-python.python-2025.1.0"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(
            json.dumps({"displayName": "Python"}),
            encoding="utf-8",
        )
        # Create extensions.json with relativeLocation entry
        (extensions_dir / "extensions.json").write_text(
            json.dumps([
                {
                    "identifier": {"id": "ms-python.python"},
                    "relativeLocation": "ms-python.python-2025.1.0",
                    "version": "2025.1.0",
                }
            ]),
            encoding="utf-8",
        )
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "ms-python.python@2025.1.0\n"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/code"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        items = result.sections[0].items
        assert any("Python" in item for item in items)

    def test_rsplit_on_last_at(self, tmp_path: Path) -> None:
        """Extension ID containing @ must split on the LAST @ only (Pitfall D: rsplit('@', 1))."""
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        # Publisher.name-with@symbols@1.0.0 — two @ characters
        mock_r.stdout = "pub.name-with@symbols@1.0.0\n"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/code"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        items = result.sections[0].items
        assert len(items) == 1
        # id = "pub.name-with@symbols", version = "1.0.0"
        assert "pub.name-with@symbols" in items[0]
        assert "1.0.0" in items[0]

    def test_malformed_cli_line_skipped(self, tmp_path: Path) -> None:
        """CLI line with no '@' separator must be skipped (rsplit guard len(parts) != 2)."""
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "no-at-separator\n"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/code"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        assert result.sections[0].items == []

    def test_cli_empty_falls_back_to_extensions_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI in PATH but subprocess returns empty stdout -> WARNING + fallback to extensions.json.
        """
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        (extensions_dir / "extensions.json").write_text(
            json.dumps([
                {
                    "identifier": {"id": "ms-python.python"},
                    "relativeLocation": "",
                    "version": "2025.1.0",
                }
            ]),
            encoding="utf-8",
        )
        mock_r: MagicMock = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = ""  # empty stdout triggers Path B

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value="/usr/bin/code"),
            patch("maccat.collectors.vscode.subprocess.run", return_value=mock_r),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        items = result.sections[0].items
        assert len(items) == 1
        assert "ms-python.python" in items[0]


# ===========================================================================
# File fallback (Path B)
# ===========================================================================


class TestVSCodeFileFallback:
    """Tests for VSCodeCollector extensions.json file fallback path."""

    def test_file_fallback_absent_both(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI absent AND no extensions.json -> NOTE to stderr; items == []."""
        missing_dir = tmp_path / "nonexistent"

        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(VSCodeCollector, "_EXT_DIR", missing_dir),
        ):
            result = VSCodeCollector().collect()

        captured = capsys.readouterr()
        assert "NOTE" in captured.err
        assert result.sections[0].items == []

    def test_file_fallback_extensions_json_only(self, tmp_path: Path) -> None:
        """CLI absent; extensions.json present -> items populated from extensions.json."""
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        (extensions_dir / "extensions.json").write_text(
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
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()

        items = result.sections[0].items
        assert len(items) == 1
        assert "ms-python.python" in items[0]

    # --- CAT-06 shape-guard regressions (WR-01) ---

    def test_file_fallback_non_list_top_level_degrades(self, tmp_path: Path) -> None:
        """extensions.json whose top level is an object (not array) degrades to empty."""
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        (extensions_dir / "extensions.json").write_text(
            json.dumps({"identifier": {"id": "x"}}),  # object, not array
            encoding="utf-8",
        )
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()  # must not raise
        assert result.sections[0].items == []

    def test_file_fallback_non_dict_entry_skipped(self, tmp_path: Path) -> None:
        """A non-dict array element in extensions.json is skipped, not raised."""
        extensions_dir = tmp_path / "extensions"
        extensions_dir.mkdir()
        (extensions_dir / "extensions.json").write_text(
            json.dumps([
                "just-a-string",
                {"identifier": {"id": "ms-python.python"}, "version": "1.0"},
            ]),
            encoding="utf-8",
        )
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(VSCodeCollector, "_EXT_DIR", extensions_dir),
        ):
            result = VSCodeCollector().collect()  # must not raise
        items = result.sections[0].items
        assert len(items) == 1
        assert "ms-python.python" in items[0]


# ===========================================================================
# Section properties
# ===========================================================================


class TestVSCodeDegradation:
    """Tests for VSCodeCollector section structure invariants."""

    def test_vscode_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'VS Code Extensions'."""
        missing_dir = tmp_path / "nonexistent"
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(VSCodeCollector, "_EXT_DIR", missing_dir),
        ):
            result = VSCodeCollector().collect()
        assert result.sections[0].title == "VS Code Extensions"

    def test_vscode_raw_is_false(self, tmp_path: Path) -> None:
        """Section.raw must be False — VS Code extensions go through flush_section."""
        missing_dir = tmp_path / "nonexistent"
        with (
            patch("maccat.collectors.vscode.shutil.which", return_value=None),
            patch.object(VSCodeCollector, "_EXT_DIR", missing_dir),
        ):
            result = VSCodeCollector().collect()
        assert result.sections[0].raw is False
