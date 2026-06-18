"""Tests for maccat.reinstall.parser — round-trip contract: parse(emit(x)) == x.

Locks the parser <-> catalog/format.py coupling so the two cannot silently drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.catalog.format import emit_item
from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section
from maccat.reinstall.parser import (
    _parse_item_line,
    parse_catalog,
    parse_markdown_catalog,
)

# ---------------------------------------------------------------------------
# Test data tables
# ---------------------------------------------------------------------------

# Six shapes that emit_item() can produce.
# (name, version, id_, exp_name, exp_ver, exp_id)
ROUND_TRIP_CASES = [
    ("Final Cut Pro", "10.7.1", "424389933", "Final Cut Pro", "10.7.1", "424389933"),
    ("Safari", "15.0", "", "Safari", "15.0", None),
    ("Final Cut Pro", "", "424389933", "Final Cut Pro", None, "424389933"),
    ("Final Cut Pro", "", "", "Final Cut Pro", None, None),
    # id-promoted: empty name with id — id becomes name, no bracket
    ("", "", "424389933", "424389933", None, None),
    # id-promoted + version: empty name with id and version
    ("", "15.0", "424389933", "424389933", "15.0", None),
]

# Adversarial cases with embedded parentheses in names.
# (raw_line, exp_name, exp_ver, exp_id, round_trip_ok)
ADVERSARIAL_CASES = [
    # Inner parens preserved in name — round-trip is clean
    ("App (Beta) (1.2.3) [999]", "App (Beta)", "1.2.3", "999", True),
    # KNOWN LOSSY: embedded paren in name without distinct version is ambiguous;
    # right-anchored matching takes LAST (...) as version by design (CONTEXT.md decision).
    ("App (Beta) [999]", "App", "Beta", "999", False),
    # KNOWN LOSSY: embedded paren in name without id is ambiguous;
    # right-anchored matching takes LAST (...) as version by design (CONTEXT.md decision).
    ("App (Beta)", "App", "Beta", None, False),
    # KNOWN LOSSY (WR-03): nested parens. [^)]+ in the version group cannot span
    # the inner ")", so the trailing "(...)" is NOT taken as a version — the name
    # is kept verbatim and the version is dropped. The id is still recovered.
    ("Foo (Bar (Baz)) [9]", "Foo (Bar (Baz))", None, "9", False),
    # KNOWN LOSSY (WR-03): nested parens, no id — falls back to name-only.
    ("Foo (Bar (Baz))", "Foo (Bar (Baz))", None, None, False),
    # KNOWN LOSSY (WR-02): embedded bracket in a name without a real id is
    # ambiguous — symmetric to the embedded-paren case. Right-anchored matching
    # takes the trailing "[...]" as the id, so an app named "Foo [Bar]" is
    # re-interpreted as name "Foo" with id "Bar". Real mas/brew names rarely
    # contain brackets, so this only affects hand-edited/external catalogs.
    ("Foo [Bar]", "Foo", None, "Bar", False),
    # KNOWN LOSSY (WR-01): a name that legitimately ends in whitespace is not
    # round-trippable. emit_item("App ", "1.0", "") -> "App  (1.0)" (name's space
    # + emit's separator space); the WR-04 "\\s+" tolerance consumes BOTH, so the
    # trailing space is dropped from `name`. emit_item never produces trailing-space
    # names, so this only affects hand-edited/external catalogs.
    ("App  (1.0)", "App", "1.0", None, False),
]


# ---------------------------------------------------------------------------
# TestItemLineParser — unit tests for _parse_item_line in isolation
# ---------------------------------------------------------------------------


class TestItemLineParser:
    """Unit tests for _parse_item_line — pure regex tests, no emit_item."""

    @pytest.mark.parametrize(
        "raw_line,exp_name,exp_ver,exp_id",
        [
            ("Final Cut Pro (10.7.1) [424389933]", "Final Cut Pro", "10.7.1", "424389933"),
            ("Safari (15.0)", "Safari", "15.0", None),
            ("Final Cut Pro [424389933]", "Final Cut Pro", None, "424389933"),
            ("Final Cut Pro", "Final Cut Pro", None, None),
        ],
    )
    def test_parses_all_four_shapes(
        self, raw_line: str, exp_name: str, exp_ver: str | None, exp_id: str | None
    ) -> None:
        """All four canonical emit_item shapes parse to correct name/version/id."""
        item = _parse_item_line(raw_line)
        assert item.name == exp_name
        assert item.version == exp_ver
        assert item.id == exp_id
        assert item.raw_line == raw_line

    @pytest.mark.parametrize(
        "raw_line,exp_name,exp_ver,exp_id",
        [
            # WR-04: trailing whitespace on hand-edited/external lines is tolerated;
            # version/id are still recovered and raw_line is preserved verbatim.
            ("Safari (15.0) ", "Safari", "15.0", None),
            ("Safari (15.0) [123] ", "Safari", "15.0", "123"),
            ("Final Cut Pro [99] ", "Final Cut Pro", None, "99"),
            ("plain name ", "plain name", None, None),
        ],
    )
    def test_trailing_whitespace_is_tolerated(
        self, raw_line: str, exp_name: str, exp_ver: str | None, exp_id: str | None
    ) -> None:
        """Trailing whitespace no longer degrades a line to name-only (WR-04)."""
        item = _parse_item_line(raw_line)
        assert item.name == exp_name
        assert item.version == exp_ver
        assert item.id == exp_id
        assert item.raw_line == raw_line  # original line preserved verbatim

    def test_none_found_sentinel_is_not_specially_handled_by_item_parser(self) -> None:
        """'  (none found)' is handled upstream in parse_catalog, not by _parse_item_line.

        When the sentinel is passed directly to _parse_item_line, ITEM_RE matches it
        (name=' ', version2='none found') — the sentinel check lives in parse_catalog,
        which short-circuits before ever calling _parse_item_line. This test documents
        that contract: section-level logic (sentinel, degradation) belongs in parse_catalog.
        """
        item = _parse_item_line("  (none found)")
        # The regex matches: name=" " (one space, non-greedy), version="none found"
        # This is the expected raw behavior — sentinel is NOT a _parse_item_line concern.
        assert item.raw_line == "  (none found)"
        # Critical behavior lives in TestParseCatalog.test_none_found_sentinel_yields_empty_items
        # — parse_catalog() intercepts the sentinel before calling _parse_item_line.

    def test_unparseable_line_falls_back_to_name_only(self) -> None:
        """Unparseable lines (e.g. '---' or empty string) fall back to name-only ParsedItem."""
        for raw_line in ["---", "!!!", ""]:
            item = _parse_item_line(raw_line)
            assert item.name == raw_line
            assert item.version is None
            assert item.id is None
            assert item.raw_line == raw_line


# ---------------------------------------------------------------------------
# TestRoundTrip — parametrized over all six emit_item shapes
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Round-trip contract: parse(_parse_item_line(emit(x))) re-emits identically."""

    @pytest.mark.parametrize("name,version,id_,exp_name,exp_ver,exp_id", ROUND_TRIP_CASES)
    def test_round_trip(
        self,
        name: str,
        version: str,
        id_: str,
        exp_name: str,
        exp_ver: str | None,
        exp_id: str | None,
    ) -> None:
        """emit_item output parses and re-emits identically for all six canonical shapes."""
        emitted = emit_item(name, version, id_)
        assert emitted is not None, f"emit_item({name!r}, {version!r}, {id_!r}) returned None"
        item = _parse_item_line(emitted)
        assert item.name == exp_name, f"name: {item.name!r} != {exp_name!r}"
        assert item.version == exp_ver, f"version: {item.version!r} != {exp_ver!r}"
        assert item.id == exp_id, f"id: {item.id!r} != {exp_id!r}"
        # Re-emit contract: parse(emit(x)) re-emits identically
        re_emitted = emit_item(item.name, item.version or "", item.id or "")
        assert re_emitted == emitted, f"re-emit: {re_emitted!r} != {emitted!r}"


# ---------------------------------------------------------------------------
# TestAdversarialFixtures — embedded parens/brackets in names
# ---------------------------------------------------------------------------


class TestAdversarialFixtures:
    """Adversarial cases with embedded parentheses in app names."""

    @pytest.mark.parametrize(
        "raw_line,exp_name,exp_ver,exp_id,round_trip_ok", ADVERSARIAL_CASES
    )
    def test_adversarial_fixtures(
        self,
        raw_line: str,
        exp_name: str,
        exp_ver: str | None,
        exp_id: str | None,
        round_trip_ok: bool,
    ) -> None:
        """Embedded parens parse per right-anchored design; KNOWN LOSSY cases documented."""
        item = _parse_item_line(raw_line)
        assert item.name == exp_name, f"name: {item.name!r} != {exp_name!r}"
        assert item.version == exp_ver, f"version: {item.version!r} != {exp_ver!r}"
        assert item.id == exp_id, f"id: {item.id!r} != {exp_id!r}"
        if round_trip_ok:
            re_emitted = emit_item(item.name, item.version or "", item.id or "")
            assert re_emitted == raw_line, f"re-emit: {re_emitted!r} != {raw_line!r}"


# ---------------------------------------------------------------------------
# TestParseCatalog — integration tests using tmp_path fixture
# ---------------------------------------------------------------------------

# Catalog fragment bytes using CatalogWriter's exact byte protocol:
#   write_section(title): "\n{title}\n" + "-"*36 + "\n"
#   write_lines(lines): each "{line}\n"
# Two sections joined (second section ends WITHOUT trailing blank — tests EOF flush).
_CATALOG_TWO_SECTIONS = (
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "git (2.44.0)\n"
    "node (18.0.0)\n"
    "\n"
    "App Store Applications\n"
    "------------------------------------\n"
    "Safari (15.0) [1234567890]\n"
)

_CATALOG_NONE_FOUND = (
    "\nSetapp Applications\n"
    "------------------------------------\n"
    "  (none found)\n"
)

# WR-05: the exact layout cli.py produces — a content-less header section
# (write_section("Installed Mac Software List")) immediately followed by the
# first collector's write_section, then real sections.
_CATALOG_REAL_HEADER_LAYOUT = (
    "\nInstalled Mac Software List\n"
    "------------------------------------\n"
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "git (2.44.0)\n"
    "\nApp Store Applications\n"
    "------------------------------------\n"
    "Safari (15.0) [1234567890]\n"
)

_CATALOG_DEGRADED = (
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "Homebrew is not installed.\n"
)

_CATALOG_NO_TRAILING_BLANK = (
    "\nHomebrew Packages\n"
    "------------------------------------\n"
    "git (2.44.0)\n"
    "node (18.0.0)"
    # NOTE: no trailing "\n" — tests the EOF flush rule (Pitfall 5 in RESEARCH.md)
)


class TestParseCatalog:
    """Integration tests: parse_catalog() on catalog fragments written to tmp_path."""

    def test_two_section_catalog_returns_both_sections(self, tmp_path: Path) -> None:
        """Two-section catalog yields ParsedCatalog with 2 ParsedSections with correct titles."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_TWO_SECTIONS, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 2
        assert result.sections[0].title == "Homebrew Packages"
        assert result.sections[1].title == "App Store Applications"

    def test_section_items_match_parsed_content(self, tmp_path: Path) -> None:
        """ParsedItem fields match the parsed item line content."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_TWO_SECTIONS, encoding="utf-8")
        result = parse_catalog(catalog_file)
        homebrew = result.sections[0]
        assert len(homebrew.items) == 2
        git_item = homebrew.items[0]
        assert git_item.name == "git"
        assert git_item.version == "2.44.0"
        assert git_item.id is None
        appstore = result.sections[1]
        assert len(appstore.items) == 1
        safari = appstore.items[0]
        assert safari.name == "Safari"
        assert safari.version == "15.0"
        assert safari.id == "1234567890"

    def test_none_found_sentinel_yields_empty_items(self, tmp_path: Path) -> None:
        """Section with '  (none found)' sentinel yields items=[], degraded=False."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_NONE_FOUND, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 1
        section = result.sections[0]
        assert section.items == []
        assert section.degraded is False

    def test_degradation_line_marks_section_degraded(self, tmp_path: Path) -> None:
        """Section with 'Homebrew is not installed.' yields items=[], degraded=True."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_DEGRADED, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 1
        section = result.sections[0]
        assert section.items == []
        assert section.degraded is True

    def test_last_section_without_trailing_blank_is_not_dropped(self, tmp_path: Path) -> None:
        """Catalog ending without trailing blank line — last section is present (EOF flush rule)."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_NO_TRAILING_BLANK, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert len(result.sections) == 1
        section = result.sections[0]
        assert section.title == "Homebrew Packages"
        assert len(section.items) == 2

    def test_parse_catalog_stores_path_as_string(self, tmp_path: Path) -> None:
        """ParsedCatalog.path equals str(path) passed to parse_catalog."""
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_TWO_SECTIONS, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert result.path == str(catalog_file)

    def test_real_header_layout_yields_leading_empty_header_section(
        self, tmp_path: Path
    ) -> None:
        """WR-05: the real cli.py header layout produces a leading empty header section.

        Locks the contract: parse_catalog does NOT filter the content-less
        "Installed Mac Software List" header; it appears as items=[],
        degraded=False ahead of the real collector sections. Downstream
        (Phase 25) consumers are responsible for skipping it.
        """
        catalog_file = tmp_path / "catalog.txt"
        catalog_file.write_text(_CATALOG_REAL_HEADER_LAYOUT, encoding="utf-8")
        result = parse_catalog(catalog_file)
        assert [s.title for s in result.sections] == [
            "Installed Mac Software List",
            "Homebrew Packages",
            "App Store Applications",
        ]
        header = result.sections[0]
        assert header.items == []
        assert header.degraded is False
        # Real sections still parse correctly behind the empty header.
        assert len(result.sections[1].items) == 1
        assert result.sections[1].items[0].name == "git"
        assert len(result.sections[2].items) == 1
        assert result.sections[2].items[0].id == "1234567890"


# ---------------------------------------------------------------------------
# Minimal markdown catalog fixture string
# ---------------------------------------------------------------------------

_MINIMAL_MD_CATALOG = (
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


# ---------------------------------------------------------------------------
# TestMarkdownRoundTrip — RIN-01: render_markdown_catalog → parse_markdown_catalog
# ---------------------------------------------------------------------------


class TestMarkdownRoundTrip:
    """RIN-01: render_markdown_catalog → parse_markdown_catalog preserves sections+items."""

    @pytest.fixture()
    def rendered_catalog(self, tmp_path: Path) -> tuple[list[Section], Path]:
        """Build a multi-section catalog via render_markdown_catalog and write to disk.

        Covers all item shapes: name+version+id, name+version only, name+id only,
        name only, empty section.  Adversarial shapes (pipe/backslash in name) are
        tested in dedicated methods below with their own mini-catalogs.
        """
        sections = [
            Section("Homebrew Packages", ["git (2.44.0)", "node (18.0.0)"], raw=True),
            Section(
                "App Store Applications",
                ["Final Cut Pro (10.7.1) [424389933]"],
                raw=False,
            ),
            Section("Setapp Applications", [], raw=False),
            Section("Web Applications", ["Figma [figma]"], raw=True),
        ]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "mac-software-list-[TestMac]-20260618123456.md"
        p.write_text(content, encoding="utf-8")
        return sections, p

    def test_section_titles_preserved(
        self, rendered_catalog: tuple[list[Section], Path]
    ) -> None:
        """Parsed section titles equal the input section titles."""
        sections, path = rendered_catalog
        result = parse_markdown_catalog(path)
        assert [s.title for s in result.sections] == [s.title for s in sections]

    def test_item_count_preserved(
        self, rendered_catalog: tuple[list[Section], Path]
    ) -> None:
        """For each non-empty section, parsed item count matches expected item count."""
        sections, path = rendered_catalog
        result = parse_markdown_catalog(path)
        # Homebrew: 2 items (raw=True, order preserved)
        homebrew = next(s for s in result.sections if s.title == "Homebrew Packages")
        assert len(homebrew.items) == 2
        # App Store: 1 item (raw=False, sorted — single item so order unchanged)
        appstore = next(s for s in result.sections if s.title == "App Store Applications")
        assert len(appstore.items) == 1
        # Web: 1 item (raw=True)
        web = next(s for s in result.sections if s.title == "Web Applications")
        assert len(web.items) == 1

    def test_item_names_preserved(
        self, rendered_catalog: tuple[list[Section], Path]
    ) -> None:
        """Item names in the first Homebrew item match the emitter input."""
        sections, path = rendered_catalog
        result = parse_markdown_catalog(path)
        homebrew = next(s for s in result.sections if s.title == "Homebrew Packages")
        # raw=True preserves order; first item is "git (2.44.0)"
        assert homebrew.items[0].name == "git"

    def test_version_and_id_preserved(
        self, rendered_catalog: tuple[list[Section], Path]
    ) -> None:
        """Version and ID are preserved through the round-trip for App Store section."""
        sections, path = rendered_catalog
        result = parse_markdown_catalog(path)
        appstore = next(s for s in result.sections if s.title == "App Store Applications")
        assert len(appstore.items) == 1
        item = appstore.items[0]
        assert item.name == "Final Cut Pro"
        assert item.version == "10.7.1"
        assert item.id == "424389933"

    def test_empty_section_parses_to_empty_items(
        self, rendered_catalog: tuple[list[Section], Path]
    ) -> None:
        """Setapp section (empty input) → ParsedSection with items=[]."""
        sections, path = rendered_catalog
        result = parse_markdown_catalog(path)
        setapp = next(s for s in result.sections if "Setapp" in s.title)
        assert setapp.items == []

    def test_pipe_in_name_round_trips(self, tmp_path: Path) -> None:
        """A name containing '|' is escaped by the emitter and unescaped by the parser."""
        # Build a minimal catalog with a section whose item name contains a literal pipe.
        # Use raw=True so the item string is passed directly to _render_table.
        # The item string "pipe|bar [id-x]" → name="pipe|bar", id="id-x"
        # _escape_cell("pipe|bar") → "pipe\\|bar" in the table row.
        # _unescape_cell("pipe\\|bar") → "pipe|bar" — round-trip complete.
        sections = [Section("Extensions", ["pipe|bar [id-x]"], raw=True)]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "catalog.md"
        p.write_text(content, encoding="utf-8")
        result = parse_markdown_catalog(p)
        assert len(result.sections) == 1
        ext = result.sections[0]
        assert len(ext.items) == 1
        assert "|" in ext.items[0].name, f"Expected '|' in name, got: {ext.items[0].name!r}"

    def test_backslash_in_name_round_trips(self, tmp_path: Path) -> None:
        """A name containing '\\' is escaped by the emitter and unescaped by the parser."""
        # "back\\slash [id-y]" → name="back\\slash", id="id-y"
        # _escape_cell("back\\slash") → "back\\\\slash" in the table row.
        # _unescape_cell("back\\\\slash") → "back\\slash" — round-trip complete.
        sections = [Section("Extensions", ["back\\slash [id-y]"], raw=True)]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "catalog.md"
        p.write_text(content, encoding="utf-8")
        result = parse_markdown_catalog(p)
        assert len(result.sections) == 1
        ext = result.sections[0]
        assert len(ext.items) == 1
        assert "\\" in ext.items[0].name, (
            f"Expected '\\' in name, got: {ext.items[0].name!r}"
        )

    def test_version_only_item_round_trips(self, tmp_path: Path) -> None:
        """An item with version but no id: version is preserved, id is None after round-trip."""
        sections = [Section("Homebrew", ["wget (1.21.3)"], raw=True)]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "catalog.md"
        p.write_text(content, encoding="utf-8")
        result = parse_markdown_catalog(p)
        item = result.sections[0].items[0]
        assert item.name == "wget"
        assert item.version == "1.21.3"
        assert item.id is None

    def test_id_only_item_round_trips(self, tmp_path: Path) -> None:
        """An item with id but no version: id is preserved, version is None after round-trip."""
        sections = [Section("Extensions", ["ms-python.python [ms-python.python]"], raw=True)]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "catalog.md"
        p.write_text(content, encoding="utf-8")
        result = parse_markdown_catalog(p)
        item = result.sections[0].items[0]
        assert item.name == "ms-python.python"
        assert item.version is None
        assert item.id == "ms-python.python"


# ---------------------------------------------------------------------------
# TestMarkdownParserRefusal — RIN-02: parse_markdown_catalog refuses non-.md input
# ---------------------------------------------------------------------------


class TestMarkdownParserRefusal:
    """RIN-02: parse_markdown_catalog refuses .txt and frontmatter-less .md with ValueError."""

    def test_txt_extension_raises_value_error(self, tmp_path: Path) -> None:
        """A .txt path raises ValueError containing 'maccat convert --from'."""
        f = tmp_path / "catalog.txt"
        f.write_text("content", encoding="utf-8")
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_md_without_frontmatter_raises_value_error(self, tmp_path: Path) -> None:
        """A .md file with no opening '---' fence raises ValueError."""
        f = tmp_path / "catalog.md"
        f.write_text("# Installed Mac Software List\n\n## Homebrew\n", encoding="utf-8")
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_md_with_unclosed_frontmatter_raises_value_error(self, tmp_path: Path) -> None:
        """A .md file with opening '---' but no closing fence raises ValueError."""
        f = tmp_path / "catalog.md"
        f.write_text(
            "---\ncomputer: TestMac\nhostname: test.local\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_run_reinstall_exits_nonzero_on_txt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run_reinstall with a .txt path exits non-zero with a message about 'convert'."""
        import argparse

        f = tmp_path / "mac-software-list-[T]-20260618120000.txt"
        f.write_text("content", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        args = argparse.Namespace(from_path=str(f), computer=None, rename=False)
        from maccat.reinstall.cli import run_reinstall

        with pytest.raises(SystemExit) as exc:
            run_reinstall(args)
        assert exc.value.code != 0
        # The error message (embedded in sys.exit arg) must reference 'convert'
        assert "convert" in str(exc.value).lower()
