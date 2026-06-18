"""Catalog filename parse and generate utilities.

Filename convention: mac-software-list-[{machine}]-{timestamp}.md
  - machine: the computer-folder label (no brackets, no /, no tab/newline)
  - timestamp: 14-digit YYYYMMDDHHMMSS string

The regex is the exact Python equivalent of the zsh parameter expansion used
in update-list.sh lines 964–965 and 982–983 to extract host and timestamp:
    local tmp="${filename#*[}"
    local host="${tmp%]-*}"
    local ts=$(echo "$filename" | grep -oE '[0-9]{14}\\.md$' | cut -c1-14)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.md$"
)


@dataclass(frozen=True)
class CatalogFilename:
    """Parsed components of a catalog filename. Immutable and hashable."""

    machine: str
    """Computer-folder label extracted from between [ and ]."""
    timestamp: str
    """14-digit YYYYMMDDHHMMSS string."""
    filename: str
    """Full original filename."""


def parse_catalog_filename(filename: str) -> CatalogFilename | None:
    """Parse a catalog filename into its components.

    Returns None (never raises) for any non-matching filename — mirrors the
    zsh warn-and-continue policy in retain_newest_per_host and prune_old_archives.

    Args:
        filename: The bare filename (not a full path).

    Returns:
        CatalogFilename if the filename matches the convention, None otherwise.
    """
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    return CatalogFilename(
        machine=m.group("machine"),
        timestamp=m.group("ts"),
        filename=filename,
    )


def make_catalog_filename(machine: str, timestamp: str) -> str:
    """Produce a catalog filename from a machine label and 14-digit timestamp.

    No validation is performed here — validation belongs in validate_computer_name
    (caller's responsibility). The output is guaranteed to round-trip through
    parse_catalog_filename when the inputs are valid.

    Args:
        machine: Computer-folder label (must not contain [, ], or /).
        timestamp: 14-digit YYYYMMDDHHMMSS string.

    Returns:
        Catalog filename string, e.g. 'mac-software-list-[MyMac]-20260614120000.md'.
    """
    return f"mac-software-list-[{machine}]-{timestamp}.md"
