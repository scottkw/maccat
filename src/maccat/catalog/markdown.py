"""Markdown catalog emitter — renders collector Sections into a complete .md catalog string.

This module makes no process calls beyond the flush_section() delegation for non-raw
sections.  It builds the markdown text entirely in Python and returns a str.  The
caller (cli.py) writes the string to disk via CatalogWriter.write_raw().

Format contract:
  ---
  computer: "<computer>"
  hostname: "<hostname>"
  generated: "<generated>"    # double-quoted to prevent YAML 1.1 datetime auto-cast
  maccat_version: "<maccat_version>"
  ---
  # Installed Mac Software List

  ## <Section Title>
  | Name | Version | ID |
  | --- | --- | --- |
  | <name> | <version> | <id> |
  ...
  (or "(none found)" for empty/degraded sections)
"""
from __future__ import annotations

import re

from maccat.catalog.format import flush_section
from maccat.collectors.base import Section

# ---------------------------------------------------------------------------
# Module-level constants
# Duplicated from reinstall/parser.py to avoid coupling to the reinstall module.
# ---------------------------------------------------------------------------

_DEGRADATION_LINES: frozenset[str] = frozenset(
    {
        "Homebrew is not installed.",
        "mas (Mac App Store CLI) is not installed.",
        "Install it with Homebrew: brew install mas",
        "Could not retrieve App Store list.",
        "Setapp is not installed or detected.",
    }
)

# Right-anchored alternation regex — inverts all emit_item() output shapes.
# Duplicated verbatim from reinstall/parser.py ITEM_RE; private prefix to
# signal it is internal to this module.
_ITEM_RE = re.compile(
    r"^"
    r"(?P<name>.+?)"  # non-greedy name
    r"(?:"
    r"\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"  # branch 1: version + id
    r"|"
    r"\s+\((?P<version2>[^)]+)\)"  # branch 2: version only
    r"|"
    r"\s+\[(?P<id2>[^\]]+)\]"  # branch 3: id only
    r")?"
    r"\s*"  # tolerate trailing whitespace on hand-edited/external lines
    r"$"
)

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _yaml_quote(value: str) -> str:
    """Wrap value in double quotes, escaping embedded backslashes and double-quotes.

    Produces a YAML double-quoted scalar that is valid for any string content,
    including values containing colons (which would produce invalid bare scalars).
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _escape_cell(value: str) -> str:
    """Escape literal pipe characters in a table cell value.

    A bare "|" in a cell breaks the markdown table column structure.
    Every "|" is replaced with "\\|" so the table renders correctly.
    """
    return value.replace("|", r"\|")


def _parse_columns(line: str) -> tuple[str, str, str]:
    """Return (name, version, id_) from an emit_item-shaped or Homebrew-shaped line.

    All three values are strings; empty string for missing version/id.
    Never raises — falls back to (line, "", "") on no regex match.
    """
    m = _ITEM_RE.match(line)
    if not m:
        return line, "", ""
    name = m.group("name") or ""
    version = m.group("version") or m.group("version2") or ""
    id_ = m.group("id") or m.group("id2") or ""
    return name, version, id_


def _render_table(items: list[str]) -> str:
    """Render a list of item lines as a 3-column markdown table string.

    items must already be in final order (flush_section applied by caller for
    non-raw sections; raw sections preserve collector-native order).

    Each missing version or id cell renders as a single space " " per the
    CONTEXT.md convention for space-padded empty cells.
    """
    rows: list[str] = [
        "| Name | Version | ID |",
        "| --- | --- | --- |",
    ]
    for line in items:
        name, version, id_ = _parse_columns(line)
        ver_cell = _escape_cell(version) if version else " "
        id_cell = _escape_cell(id_) if id_ else " "
        rows.append(f"| {_escape_cell(name)} | {ver_cell} | {id_cell} |")
    return "\n".join(rows) + "\n"


def render_frontmatter(
    computer: str,
    hostname: str,
    generated: str,
    maccat_version: str,
) -> str:
    """Return the YAML frontmatter block as a string.

    Keys are in fixed order (computer / hostname / generated / maccat_version)
    for byte-deterministic output across repeated runs.

    All scalar values are double-quoted so that colons, special characters, and
    YAML 1.1 datetime-like strings in any value cannot produce structurally invalid
    YAML.  Embedded backslashes and double-quotes within values are escaped per the
    YAML double-quoted scalar rules.
    """
    return (
        "---\n"
        f"computer: {_yaml_quote(computer)}\n"
        f"hostname: {_yaml_quote(hostname)}\n"
        f"generated: {_yaml_quote(generated)}\n"
        f"maccat_version: {_yaml_quote(maccat_version)}\n"
        "---\n"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_markdown_catalog(
    sections: list[Section],
    *,
    computer: str,
    hostname: str,
    generated: str,
    maccat_version: str,
) -> str:
    """Return the complete .md catalog content as a single string.

    Args:
        sections:        Collector sections (from CollectorResult.sections).
        computer:        Computer folder name — embedded in frontmatter.
        hostname:        Machine hostname — embedded in frontmatter.
        generated:       ISO-8601 local timestamp string, e.g. "2026-06-18T12:34:56".
                         Double-quoted in frontmatter output.
        maccat_version:  Version string from maccat.__version__.

    Returns:
        Complete markdown string starting with frontmatter then the catalog title
        and per-section ## headings + tables.  No file I/O is performed.

    Sort contract:
        raw=False sections: items sorted + deduped via flush_section() (LC_ALL=C sort -f -u).
        raw=True sections:  items written in collector-native order — no Python sort.

    Empty / degraded sections:
        Items=[] or items consisting entirely of known degradation lines render as
        "(none found)" plain text under the section heading — no empty table.
    """
    parts: list[str] = [
        render_frontmatter(computer, hostname, generated, maccat_version),
        "# Installed Mac Software List\n",
    ]

    for section in sections:
        parts.append(f"\n## {section.title}\n")

        items = section.items

        if section.raw:
            # Raw path: check for empty or all-degradation items
            if not items or all(line in _DEGRADATION_LINES for line in items):
                parts.append("(none found)\n")
            else:
                parts.append(_render_table(items))
        else:
            # Non-raw path: sort + dedup via flush_section
            sorted_items = flush_section(items)
            # flush_section returns ["  (none found)"] for empty input
            if sorted_items == ["  (none found)"]:
                parts.append("(none found)\n")
            else:
                parts.append(_render_table(sorted_items))

    return "".join(parts)
