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
