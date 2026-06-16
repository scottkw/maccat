"""Tests for maccat.reinstall.parser — round-trip contract: parse(emit(x)) == x.

Locks the parser <-> catalog/format.py coupling so the two cannot silently drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maccat.catalog.format import emit_item
from maccat.reinstall.parser import (
    _parse_item_line,
    parse_catalog,
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
