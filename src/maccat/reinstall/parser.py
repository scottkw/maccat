"""Catalog parser — inverts emit_item() line shapes into typed dataclasses.

parse_catalog(path) -> ParsedCatalog is the public API consumed by the
Phase 25 reinstall emitter.  The parser is the logical inverse of
catalog/format.py::emit_item(); do NOT import emit_item here to avoid
coupling (the regex is the sole contract between the two modules).

KNOWN LOSSY cases (explicit contract — see ADVERSARIAL_CASES in
tests/reinstall/test_parser_contract.py):
  * Nested parentheses in a name ("Foo (Bar (Baz)) [9]"): the version group
    [^)]+ cannot span the inner ")", so the trailing "(...)" is NOT taken as a
    version. The name is kept verbatim and the version is dropped (the id, if
    present, is still recovered). emit_item never emits nested parens, so this
    only affects hand-edited/external catalogs.
  * Embedded single-level parens without a distinct version ("App (Beta)"):
    right-anchored matching takes the LAST "(...)" as the version by design.
  * Embedded brackets in a name without a real id ("Foo [Bar]"): symmetric to
    the embedded-paren case — right-anchored matching takes the trailing "[...]"
    as the id, so "Foo [Bar]" parses to name "Foo", id "Bar". A name that
    legitimately contains brackets is therefore not round-trippable. Real
    mas/brew names rarely contain brackets, so this only affects
    hand-edited/external catalogs.
  * Trailing-whitespace names ("App " emitted as "App  (1.0)"): the WR-04
    "\\s+"/"\\s*$" tolerance also consumes a space that is part of the name
    itself, so a name that legitimately ends in whitespace is NOT round-trippable
    (the trailing space is dropped from `name`, though `raw_line` is preserved).
    emit_item-derived catalogs never produce trailing-space names
    (MasCollector/HomebrewCollector build names via str.split()), so this only
    affects hand-edited/external catalogs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SEPARATOR = "-" * 36  # 36 ASCII dashes — matches CatalogWriter.write_section()
NONE_FOUND_SENTINEL = "  (none found)"  # exactly two leading spaces (format.py:56)

DEGRADATION_LINES: frozenset[str] = frozenset(
    {
        "Homebrew is not installed.",
        "mas (Mac App Store CLI) is not installed.",
        "Install it with Homebrew: brew install mas",
        "Could not retrieve App Store list.",
        "Setapp is not installed or detected.",
    }
)

# Markdown format sentinel for empty/degraded sections — NO leading spaces.
# Distinct from NONE_FOUND_SENTINEL (two leading spaces, legacy format).
MD_NONE_FOUND = "(none found)"

# Right-anchored alternation regex that inverts all six emit_item output shapes.
# Three branches with distinct named groups across alternation (Python re forbids
# duplicate group names in alternation — Pitfall 6 in RESEARCH.md).
#   Branch 1: version + id   "name (version) [id]"
#   Branch 2: version only   "name (version)"
#   Branch 3: id only        "name [id]"
# The outer group is optional (?:...)?  so "name only" matches with all groups None.
ITEM_RE = re.compile(
    r"^"
    r"(?P<name>.+?)"  # non-greedy name
    r"(?:"
    r"\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"  # branch 1: version + id
    r"|"
    r"\s+\((?P<version2>[^)]+)\)"  # branch 2: version only
    r"|"
    r"\s+\[(?P<id2>[^\]]+)\]"  # branch 3: id only
    r")?"
    r"\s*"  # WR-04: tolerate trailing whitespace on hand-edited/external lines
    r"$"
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ParsedItem:
    """A single software item parsed from a catalog line."""

    name: str
    version: str | None
    id: str | None  # noqa: A003 (shadows builtin; acceptable for domain clarity)
    raw_line: str


@dataclass
class ParsedSection:
    """A named section from a catalog file with its parsed items."""

    title: str
    items: list[ParsedItem] = field(default_factory=list)
    degraded: bool = False  # True if a known degradation message was found


@dataclass
class ParsedCatalog:
    """A fully parsed catalog file with all its sections."""

    sections: list[ParsedSection] = field(default_factory=list)
    path: str = ""  # source file path as string (str not Path — serialization-friendly)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_item_line(raw_line: str) -> ParsedItem:
    """Apply ITEM_RE to a single catalog item line. Falls back to name-only on no-match.

    Never raises. Unparseable lines are returned as name-only ParsedItems with
    raw_line preserved.
    """
    m = ITEM_RE.match(raw_line)
    if not m:
        return ParsedItem(name=raw_line, version=None, id=None, raw_line=raw_line)
    return ParsedItem(
        name=m.group("name"),
        version=m.group("version") or m.group("version2"),
        id=m.group("id") or m.group("id2"),
        raw_line=raw_line,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_catalog(path: Path) -> ParsedCatalog:
    """Read a catalog file and return typed structured items.

    Inverts all four emit_item() line shapes and their degradations.
    Encoding: UTF-8 (matches CatalogWriter which writes with encoding='utf-8').

    State machine states:
      SEEKING_TITLE     — scanning for a section title line
      SEEKING_SEPARATOR — found a title candidate, waiting for the 36-dash separator
      COLLECTING        — inside a section, accumulating item lines

    EOF flush rule: if the file ends without a trailing blank line (the last
    write_lines call ends with a newline but no additional blank), the in-progress
    section is flushed after the loop (Pitfall 5 in RESEARCH.md).

    Header-section contract (WR-05): real catalogs (see cli.py) begin with
    write_section("Installed Mac Software List") immediately followed by the next
    collector's write_section — a title + separator with ZERO content lines. The
    state machine emits this as a leading ParsedSection(title="Installed Mac
    Software List", items=[], degraded=False). This is intentional and locked by
    test_real_header_layout_yields_leading_empty_header_section: parse_catalog
    does NOT filter it, so downstream (Phase 25) consumers must skip empty,
    non-degraded sections themselves. Note an empty header is indistinguishable
    here from a section that legitimately produced no item lines, which is why
    filtering is left to the consumer rather than applied in the parser.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    catalog = ParsedCatalog(path=str(path))

    state = "SEEKING_TITLE"
    current_title: str | None = None
    current_items: list[ParsedItem] = []
    current_degraded: bool = False

    for line in lines:
        if state == "SEEKING_TITLE":
            if line == "":
                # blank line — stay in SEEKING_TITLE
                pass
            elif line == SEPARATOR:
                # separator without a preceding title — ignore, stay SEEKING_TITLE
                pass
            else:
                # non-blank, non-separator: treat as title candidate
                current_title = line
                state = "SEEKING_SEPARATOR"

        elif state == "SEEKING_SEPARATOR":
            if line == SEPARATOR:
                # found the separator — enter COLLECTING
                current_items = []
                current_degraded = False
                state = "COLLECTING"
            elif line == "":
                # blank between title candidate and separator — stay
                pass
            else:
                # something else: discard the title candidate, back to SEEKING_TITLE
                current_title = None
                state = "SEEKING_TITLE"

        elif state == "COLLECTING":
            if line == "":
                # blank line marks end of section — flush
                if current_title is not None:
                    catalog.sections.append(
                        ParsedSection(
                            title=current_title,
                            items=current_items,
                            degraded=current_degraded,
                        )
                    )
                current_title = None
                current_items = []
                current_degraded = False
                state = "SEEKING_TITLE"
            else:
                # non-blank line inside COLLECTING
                if line == NONE_FOUND_SENTINEL:
                    # sentinel: empty section (not degraded, just empty)
                    pass  # leave current_items empty, current_degraded False
                elif line in DEGRADATION_LINES:
                    # known degradation message: mark section degraded
                    current_degraded = True
                else:
                    current_items.append(_parse_item_line(line))

    # EOF flush: if we ended in COLLECTING without a trailing blank line
    if state == "COLLECTING" and current_title is not None:
        catalog.sections.append(
            ParsedSection(
                title=current_title,
                items=current_items,
                degraded=current_degraded,
            )
        )

    return catalog


# ---------------------------------------------------------------------------
# Markdown catalog parser — inverts render_markdown_catalog() from
# catalog/markdown.py. Added in Phase 31; legacy parse_catalog above is
# retained unchanged for Phase 32 convert.
# ---------------------------------------------------------------------------


def _unescape_cell(value: str) -> str:
    """Inverse of catalog/markdown.py::_escape_cell. Strip whitespace, then unescape.

    _escape_cell escapes in order: backslash first (\\), then pipe (|).
    The inverse unescaping can be applied in either order; by convention this
    function unescapes pipe first (\\| → |), then backslash (\\\\ → \\).
    Both orders are mathematically correct for this escape scheme.

    Never raises.
    """
    s = value.strip()
    # Unescape \\| → | first, then \\\\ → \\.
    return s.replace("\\|", "|").replace("\\\\", "\\")


def _parse_markdown_row(row: str) -> ParsedItem | None:
    """Parse a markdown table data row into a ParsedItem. Never raises.

    Expects a row of the form '| name | ver | id |' where the row already
    satisfies row.startswith('| ') and row.endswith(' |').

    On structural mismatch (not exactly 3 columns after splitting the inner
    content on ' | '), returns a name-only ParsedItem with raw_line preserved.
    """
    # Strip leading '| ' (2 chars) and trailing ' |' (2 chars)
    inner = row[2:-2]
    cols = inner.split(" | ")
    if len(cols) != 3:
        # Structural mismatch: name-only fallback, raw_line preserved
        name = _unescape_cell(inner)
        return ParsedItem(name=name or row, version=None, id=None, raw_line=row)
    name = _unescape_cell(cols[0])
    version = _unescape_cell(cols[1]) or None  # empty cell → '' → None
    id_ = _unescape_cell(cols[2]) or None
    if not name:
        # Completely empty name: lenient fallback
        return ParsedItem(name=row, version=None, id=None, raw_line=row)
    return ParsedItem(name=name, version=version, id=id_, raw_line=row)


def parse_markdown_catalog(path: Path) -> ParsedCatalog:
    """Parse a .md catalog file into ParsedCatalog. Raises ValueError for non-markdown input.

    Inverts render_markdown_catalog() from catalog/markdown.py. Reads the YAML
    frontmatter fences (validate + skip), iterates ## section headings, and
    converts | Name | Version | ID | table rows into ParsedItems.

    State machine states (implicit):
      IN_FRONTMATTER  — scanning lines[1:] for the closing '---' fence
      BODY            — iterating lines after the frontmatter for sections + rows

    Raises:
        ValueError: If path does not have .md extension (extension check), or
                    if the file lacks a valid opening '---' frontmatter fence
                    (content-sniff check for renamed legacy catalogs), or
                    if the frontmatter block is not closed with '---'.
                    All ValueError messages contain 'maccat convert --from'.
        OSError: If the file cannot be read (propagated from Path.read_text).
    """
    path = Path(path)

    if path.suffix != ".md":
        raise ValueError(
            f"{path} is not a markdown catalog (.md extension required). "
            f"Convert it first with: maccat convert --from {path}"
        )

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Validate opening frontmatter fence.
    # text.split("\n") always yields a non-empty list (even "" -> [""]), so an
    # empty-file guard is unnecessary — lines[0] is always safe to index here.
    if lines[0] != "---":
        raise ValueError(
            f"{path} is missing valid YAML frontmatter (no opening '---' fence). "
            f"It may be a legacy .txt catalog renamed to .md. "
            f"Convert it first with: maccat convert --from {path}"
        )

    # Find the closing '---' fence (first occurrence after line 0)
    fm_close = -1
    for i, line in enumerate(lines[1:], 1):
        if line == "---":
            fm_close = i
            break
    if fm_close == -1:
        raise ValueError(
            f"{path}: frontmatter block is not closed with '---'. "
            f"Convert it first with: maccat convert --from {path}"
        )

    catalog = ParsedCatalog(path=str(path))
    current_section: ParsedSection | None = None

    for line in lines[fm_close + 1 :]:
        if line.startswith("## "):
            # Flush the in-progress section before starting a new one
            if current_section is not None:
                catalog.sections.append(current_section)
            current_section = ParsedSection(title=line[3:])
        elif line == MD_NONE_FOUND:
            # Empty/degraded section sentinel — items=[] and degraded=False already set.
            # NOTE: the markdown emitter renders BOTH empty and degraded sections as
            # "(none found)", so the degraded flag is not recoverable from the markdown
            # round-trip (unlike the legacy plain-text parser, which preserves it). This
            # is lossless for the reinstall emitter — _should_skip() drops a section when
            # items == [] regardless of the degraded flag — but downstream consumers that
            # need degraded must not rely on it being set here.
            pass
        elif line.startswith("| ") and line.endswith(" |"):
            # Skip header row and separator row; parse all other table rows
            if line in ("| Name | Version | ID |", "| --- | --- | --- |"):
                continue
            if current_section is not None:
                item = _parse_markdown_row(line)
                if item is not None:
                    current_section.items.append(item)
        # blank lines, H1 title line, other unrecognized lines: skip

    # EOF flush: append the last in-progress section
    if current_section is not None:
        catalog.sections.append(current_section)

    return catalog
