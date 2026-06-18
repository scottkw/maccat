"""Tests for maccat.catalog.markdown — locks render_markdown_catalog correctness."""
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section

# ---------------------------------------------------------------------------
# Constants shared by multiple test classes
# ---------------------------------------------------------------------------

FIXED_TS = "2026-06-18T12:34:56"
_DEFAULT_KWARGS: dict[str, str] = {
    "computer": "MyMac",
    "hostname": "my-mac.local",
    "generated": FIXED_TS,
    "maccat_version": "2.1.0",
}


def _render(*sections: Section, **kw: str) -> str:
    merged = {**_DEFAULT_KWARGS, **kw}
    return render_markdown_catalog(list(sections), **merged)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFrontmatter
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_fences_present(self) -> None:
        result = _render()
        assert result.startswith("---\n")
        assert "---\n" in result[4:]  # closing fence

    def test_key_order_computer_first(self) -> None:
        result = _render()
        # computer must come before hostname
        assert result.index("computer:") < result.index("hostname:")

    def test_key_order_hostname_before_generated(self) -> None:
        result = _render()
        assert result.index("hostname:") < result.index("generated:")

    def test_key_order_generated_before_maccat_version(self) -> None:
        result = _render()
        assert result.index("generated:") < result.index("maccat_version:")

    def test_computer_value_present(self) -> None:
        result = _render(computer="TestMac")
        assert 'computer: "TestMac"\n' in result

    def test_hostname_value_present(self) -> None:
        result = _render(hostname="test-host.local")
        assert 'hostname: "test-host.local"\n' in result

    def test_generated_double_quoted(self) -> None:
        """generated must be double-quoted to prevent YAML 1.1 datetime auto-cast."""
        result = _render(generated="2026-06-18T12:34:56")
        assert 'generated: "2026-06-18T12:34:56"\n' in result

    def test_generated_not_bare_scalar(self) -> None:
        """Bare unquoted generated would be auto-cast to datetime by YAML 1.1 parsers."""
        result = _render(generated="2026-06-18T12:34:56")
        # Must NOT appear as bare scalar
        assert "generated: 2026-06-18T12:34:56\n" not in result

    def test_maccat_version_double_quoted(self) -> None:
        """maccat_version is double-quoted for consistent safe YAML output."""
        result = _render(maccat_version="2.1.0")
        assert 'maccat_version: "2.1.0"\n' in result

    def test_computer_with_colon_produces_valid_yaml(self) -> None:
        """Regression for CR-01: a colon in computer name must not break YAML structure.

        Before the fix, 'My: Work' produced 'computer: My: Work' which is structurally
        invalid YAML (ScannerError: mapping values are not allowed here).  The fix
        double-quotes all scalar values so the colon is safely enclosed.
        """
        result = _render(computer="My: Work")
        assert 'computer: "My: Work"\n' in result
        # The raw unquoted form must never appear — it would break the YAML parser
        assert "computer: My: Work\n" not in result

    def test_hostname_with_colon_produces_valid_yaml(self) -> None:
        """Regression for CR-01: a colon in hostname must not break YAML structure."""
        result = _render(hostname="my-host: 1")
        assert 'hostname: "my-host: 1"\n' in result
        assert "hostname: my-host: 1\n" not in result

    def test_computer_embedded_double_quote_escaped(self) -> None:
        """CR-01: an embedded double-quote in computer name must be backslash-escaped."""
        result = _render(computer='My"Mac')
        assert 'computer: "My\\"Mac"\n' in result

    def test_frontmatter_followed_by_title(self) -> None:
        result = _render()
        # The title line must come after the closing ---
        closing_fence_pos = result.index("---\n", 4)
        title_pos = result.index("# Installed Mac Software List")
        assert title_pos > closing_fence_pos


# ---------------------------------------------------------------------------
# TestTableRendering
# ---------------------------------------------------------------------------


class TestTableRendering:
    def test_header_row_exact(self) -> None:
        section = Section("Homebrew Packages", ["git (2.44.0)"], raw=True)
        result = _render(section)
        assert "| Name | Version | ID |" in result

    def test_separator_row_exact(self) -> None:
        section = Section("Homebrew Packages", ["git (2.44.0)"], raw=True)
        result = _render(section)
        assert "| --- | --- | --- |" in result

    @pytest.mark.parametrize(
        "raw_line,exp_name,exp_ver,exp_id",
        [
            ("git (2.44.0)", "git", "2.44.0", ""),
            ("python@3.11 (3.11.1 3.11.2)", "python@3.11", "3.11.1 3.11.2", ""),
            ("git", "git", "", ""),
            ("Final Cut Pro (10.7.1) [424389933]", "Final Cut Pro", "10.7.1", "424389933"),
            ("Final Cut Pro (10.7.1)", "Final Cut Pro", "10.7.1", ""),
            ("Final Cut Pro [424389933]", "Final Cut Pro", "", "424389933"),
            ("Final Cut Pro", "Final Cut Pro", "", ""),
            ("com.app.id", "com.app.id", "", ""),
            ("AppName.app (1.2.3)", "AppName.app", "1.2.3", ""),
            ("server-name [stdio]", "server-name", "", "stdio"),
        ],
    )
    def test_item_shapes_render_correctly(
        self, raw_line: str, exp_name: str, exp_ver: str, exp_id: str
    ) -> None:
        section = Section("Test", [raw_line], raw=True)
        result = _render(section)
        # Expected cell values: empty version/id render as space
        ver_cell = exp_ver if exp_ver else " "
        id_cell = exp_id if exp_id else " "
        assert f"| {exp_name} | {ver_cell} | {id_cell} |" in result

    def test_missing_version_renders_as_space(self) -> None:
        section = Section("Test", ["Final Cut Pro [424389933]"], raw=True)
        result = _render(section)
        assert "| Final Cut Pro |   | 424389933 |" in result

    def test_missing_id_renders_as_space(self) -> None:
        section = Section("Test", ["git (2.44.0)"], raw=True)
        result = _render(section)
        assert "| git | 2.44.0 |   |" in result


# ---------------------------------------------------------------------------
# TestPipeEscaping
# ---------------------------------------------------------------------------


class TestPipeEscaping:
    def test_pipe_in_name_is_escaped(self) -> None:
        section = Section("Test", ["foo | bar (1.0)"], raw=True)
        result = _render(section)
        assert r"foo \| bar" in result

    def test_pipe_in_id_is_escaped(self) -> None:
        section = Section("Test", ["server [stdio|sse]"], raw=True)
        result = _render(section)
        assert r"stdio\|sse" in result

    def test_pipe_escape_does_not_break_row_structure(self) -> None:
        section = Section("Test", ["foo | bar (1.0)"], raw=True)
        result = _render(section)
        # Each row must start and end with |
        lines = result.splitlines()
        data_rows = [ln for ln in lines if ln.startswith("| ") and "foo" in ln]
        assert len(data_rows) == 1
        assert data_rows[0].startswith("| ")
        assert data_rows[0].endswith(" |")


# ---------------------------------------------------------------------------
# TestEmptySections
# ---------------------------------------------------------------------------


class TestEmptySections:
    def test_empty_items_renders_none_found(self) -> None:
        section = Section("App Store Applications", [], raw=False)
        result = _render(section)
        assert "(none found)" in result

    def test_empty_items_no_table_header(self) -> None:
        section = Section("App Store Applications", [], raw=False)
        result = _render(section)
        assert "| Name |" not in result

    def test_none_found_has_no_leading_spaces(self) -> None:
        """Markdown format uses plain (none found), not two-space-indented."""
        section = Section("Test", [], raw=False)
        result = _render(section)
        assert "(none found)" in result
        # The plain-text format used "  (none found)" with two spaces; markdown doesn't
        assert "  (none found)" not in result

    def test_empty_raw_section_renders_none_found(self) -> None:
        section = Section("Homebrew Packages", [], raw=True)
        result = _render(section)
        assert "(none found)" in result


# ---------------------------------------------------------------------------
# TestDegradedSections
# ---------------------------------------------------------------------------


class TestDegradedSections:
    def test_homebrew_not_installed_renders_none_found(self) -> None:
        section = Section(
            "Homebrew Packages",
            ["Homebrew is not installed."],
            raw=True,
        )
        result = _render(section)
        assert "(none found)" in result
        assert "Homebrew is not installed." not in result

    def test_mas_not_installed_renders_none_found(self) -> None:
        section = Section(
            "App Store Applications",
            [
                "mas (Mac App Store CLI) is not installed.",
                "Install it with Homebrew: brew install mas",
            ],
            raw=True,
        )
        result = _render(section)
        assert "(none found)" in result

    def test_setapp_not_installed_renders_none_found(self) -> None:
        section = Section(
            "Setapp Applications",
            ["Setapp is not installed or detected."],
            raw=True,
        )
        result = _render(section)
        assert "(none found)" in result

    def test_degradation_lines_do_not_appear_as_table_rows(self) -> None:
        section = Section(
            "Homebrew Packages",
            ["Homebrew is not installed."],
            raw=True,
        )
        result = _render(section)
        # No table header when all items are degradation lines
        assert "| Name |" not in result

    def test_could_not_retrieve_app_store_renders_none_found(self) -> None:
        section = Section(
            "App Store Applications",
            ["Could not retrieve App Store list."],
            raw=True,
        )
        result = _render(section)
        assert "(none found)" in result


# ---------------------------------------------------------------------------
# TestRawVsNonRaw
# ---------------------------------------------------------------------------


class TestRawVsNonRaw:
    def test_raw_true_items_in_original_order(self) -> None:
        """raw=True: items must appear in collector order (not sorted)."""
        # zsh comes before git alphabetically but we supply git first
        section = Section("Homebrew Packages", ["git (2.44.0)", "zsh (5.9)"], raw=True)
        result = _render(section)
        git_pos = result.index("| git |")
        zsh_pos = result.index("| zsh |")
        assert git_pos < zsh_pos, "raw=True: order must be preserved, not sorted"

    def test_raw_false_items_are_sorted(self) -> None:
        """raw=False: flush_section sort must be applied."""
        # zsh sorts AFTER git via LC_ALL=C; supply zsh first to verify sorting
        section = Section(
            "VS Code Extensions",
            ["zsh-syntax (1.0)", "git-lens (1.2)"],
            raw=False,
        )
        result = _render(section)
        git_pos = result.index("| git-lens |")
        zsh_pos = result.index("| zsh-syntax |")
        assert git_pos < zsh_pos, "raw=False: items must be flush_section-sorted"

    def test_raw_false_deduplicates(self) -> None:
        """flush_section deduplication must remove exact duplicates."""
        section = Section("Test", ["git (2.44.0)", "git (2.44.0)"], raw=False)
        result = _render(section)
        count = result.count("| git |")
        assert count == 1, f"Expected 1 git row after dedup, got {count}"


# ---------------------------------------------------------------------------
# TestDeterminism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_render_deterministic(self) -> None:
        """Two calls with same inputs and fixed generated timestamp → byte-identical."""
        sections = [
            Section(title="Homebrew Packages", items=["git (2.44.0)", "zsh (5.9)"], raw=True),
            Section(title="App Store Applications", items=[], raw=False),
        ]
        result1 = render_markdown_catalog(
            sections,
            computer="MyMac",
            hostname="my-mac.local",
            generated=FIXED_TS,
            maccat_version="2.1.0",
        )
        result2 = render_markdown_catalog(
            sections,
            computer="MyMac",
            hostname="my-mac.local",
            generated=FIXED_TS,
            maccat_version="2.1.0",
        )
        assert result1 == result2

    def test_render_utf8_roundtrip(self) -> None:
        """Output must survive UTF-8 encode/decode without loss."""
        result = _render()
        assert result == result.encode("utf-8").decode("utf-8")


# ---------------------------------------------------------------------------
# TestWriteRaw (CatalogWriter integration)
# ---------------------------------------------------------------------------


class TestWriteRaw:
    def test_write_raw_writes_content(self, tmp_path: Path) -> None:
        from maccat.catalog.writer import CatalogWriter

        output = tmp_path / "catalog.md"
        content = "---\ncomputer: test\n---\n# Hello\n"
        with CatalogWriter(output) as w:
            w.write_raw(content)
        assert output.read_text(encoding="utf-8") == content

    def test_write_raw_assert_guard(self, tmp_path: Path) -> None:
        from maccat.catalog.writer import CatalogWriter

        w = CatalogWriter(tmp_path / "catalog.md")
        with pytest.raises(AssertionError, match="write_raw called outside context manager"):
            w.write_raw("content")

    def test_write_raw_atomic(self, tmp_path: Path) -> None:
        """On exception, write_raw must not leave a partial file."""
        from maccat.catalog.writer import CatalogWriter

        output = tmp_path / "catalog.md"
        try:
            with CatalogWriter(output) as w:
                w.write_raw("partial content")
                raise RuntimeError("crash")
        except RuntimeError:
            pass
        assert not output.exists()
