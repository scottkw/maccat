"""RED phase: failing tests for parse_markdown_catalog and helpers (Task 1 TDD gate).

These tests will FAIL before implementation and PASS after.
Removed after Task 2 folds them into test_parser_contract.py.
"""
from __future__ import annotations

import pytest
from pathlib import Path


class TestUnescapeCell:
    """Unit tests for _unescape_cell."""

    def test_empty_cell_returns_empty_string(self) -> None:
        from maccat.reinstall.parser import _unescape_cell
        assert _unescape_cell(" ") == ""

    def test_pipe_unescape(self) -> None:
        from maccat.reinstall.parser import _unescape_cell
        assert _unescape_cell("foo\\|bar") == "foo|bar"

    def test_backslash_unescape(self) -> None:
        from maccat.reinstall.parser import _unescape_cell
        assert _unescape_cell("a\\\\b") == "a\\b"

    def test_plain_value_unchanged(self) -> None:
        from maccat.reinstall.parser import _unescape_cell
        assert _unescape_cell("wget") == "wget"


class TestParseMarkdownRow:
    """Unit tests for _parse_markdown_row."""

    def test_three_column_row(self) -> None:
        from maccat.reinstall.parser import _parse_markdown_row
        item = _parse_markdown_row("| Final Cut Pro | 10.7.1 | 424389933 |")
        assert item is not None
        assert item.name == "Final Cut Pro"
        assert item.version == "10.7.1"
        assert item.id == "424389933"

    def test_empty_id_cell(self) -> None:
        from maccat.reinstall.parser import _parse_markdown_row
        item = _parse_markdown_row("| wget | 1.21.3 |   |")
        assert item is not None
        assert item.name == "wget"
        assert item.version == "1.21.3"
        assert item.id is None

    def test_pipe_in_name(self) -> None:
        from maccat.reinstall.parser import _parse_markdown_row
        item = _parse_markdown_row("| foo\\|bar | 1.0 |   |")
        assert item is not None
        assert item.name == "foo|bar"

    def test_raw_line_preserved(self) -> None:
        from maccat.reinstall.parser import _parse_markdown_row
        row = "| wget | 1.21.3 |   |"
        item = _parse_markdown_row(row)
        assert item is not None
        assert item.raw_line == row


class TestParseMarkdownCatalog:
    """Unit tests for parse_markdown_catalog."""

    def test_txt_extension_raises_value_error(self, tmp_path: Path) -> None:
        from maccat.reinstall.parser import parse_markdown_catalog
        f = tmp_path / "catalog.txt"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_md_without_frontmatter_raises_value_error(self, tmp_path: Path) -> None:
        from maccat.reinstall.parser import parse_markdown_catalog
        f = tmp_path / "catalog.md"
        f.write_text("# Installed Mac Software List\n\n## Homebrew\n", encoding="utf-8")
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_valid_md_returns_parsed_catalog(self, tmp_path: Path) -> None:
        from maccat.reinstall.parser import parse_markdown_catalog
        content = (
            '---\n'
            'computer: "TestMac"\n'
            'hostname: "test-mac.local"\n'
            'generated: "2026-06-18T12:34:56"\n'
            'maccat_version: "2.1.0"\n'
            '---\n'
            '# Installed Mac Software List\n'
            '\n'
            '## Homebrew Packages\n'
            '| Name | Version | ID |\n'
            '| --- | --- | --- |\n'
            '| wget | 1.21.3 |   |\n'
            '\n'
        )
        f = tmp_path / "mac-software-list-[TestMac]-20260618123456.md"
        f.write_text(content, encoding="utf-8")
        result = parse_markdown_catalog(f)
        assert len(result.sections) == 1
        assert result.sections[0].title == "Homebrew Packages"
        assert result.sections[0].items[0].name == "wget"

    def test_md_none_found_constant_no_leading_spaces(self) -> None:
        from maccat.reinstall.parser import MD_NONE_FOUND
        assert MD_NONE_FOUND == "(none found)"
        assert not MD_NONE_FOUND.startswith(" ")
