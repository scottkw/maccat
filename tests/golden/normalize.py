"""Normalization helpers for golden-output parity tests (TEST-02).

Strips volatile fields before byte comparison so stable fields are asserted exactly.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEPARATOR_LINE = "-" * 36

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_catalog_body(text: str) -> str:
    """Strip volatile fields from a SECTION BODY before byte comparison.

    Volatile (replaced):
    - 14-digit timestamps anywhere in text → TIMESTAMP

    Stable (asserted exactly after normalization):
    - Section headers, separator lines, item lines, sort order, (none found),
      AND the ``[id]`` field of every ``name (version) [id]`` item line.

    CR-01: the machine ``[label]`` appears ONLY in the catalog FILENAME / top
    header line, NEVER inside a section body. Inside a body the only ``[...]``
    content is the STABLE ``[id]`` field emitted by emit_item (update-list.sh:1243,
    src/maccat/catalog/format.py:36) — name + version + ID is the milestone's
    required detail level, so the ID MUST be asserted byte-exact. The previous
    ``re.sub(r'\\[[^\\]]+\\]', '[MACHINE]', text)`` collapsed every real ID to the
    literal ``[MACHINE]`` on both sides of the comparison, so ID parity was never
    asserted. That substitution is removed; only the 14-digit timestamp (the one
    genuinely volatile field within a body) is normalized.

    See normalize_catalog_header() for filename/header-line normalization, which
    is a DISTINCT function NOT applied to section bodies.
    """
    return re.sub(r'\d{14}', 'TIMESTAMP', text)


def normalize_catalog_header(text: str) -> str:
    """Strip volatile fields from a catalog FILENAME or top header line.

    This is the ONLY place the machine ``[label]`` substitution belongs — it is
    filename-scoped and must NEVER be applied to a section body (CR-01), because a
    body's ``[...]`` is the stable ID field, not a machine label.

    Volatile (replaced), in order:
    - The catalog filename form ``[label]-<14-digit ts>.txt`` → ``[MACHINE]-TIMESTAMP.txt``
    - Any remaining 14-digit timestamps → TIMESTAMP

    The filename-anchored substitution runs first so the machine label is replaced
    without touching bracketed IDs that may appear elsewhere on the line.
    """
    text = re.sub(r'\[[^\]]+\]-\d{14}\.txt', '[MACHINE]-TIMESTAMP.txt', text)
    text = re.sub(r'\d{14}', 'TIMESTAMP', text)
    return text


def extract_section_body(catalog_text: str, section_title: str) -> str | None:
    """Return the body text for a named section, or None if not found.

    Format from CatalogWriter.write_section: \\n{title}\\n{separator}\\n{body}.
    Split on \\n + separator + \\n; the chunk before each separator ends with
    the title line; the chunk after it is the body (up to the next \\n\\n boundary).

    Validation: a 3-section synthetic string with known bodies returns the
    correct body for each title.
    """
    parts = catalog_text.split("\n" + SEPARATOR_LINE + "\n")
    for i, part in enumerate(parts):
        if part.rstrip("\n").endswith(section_title) and i + 1 < len(parts):
            body_chunk = parts[i + 1]
            # Body ends before the next \n\n<title> boundary
            return body_chunk.split("\n\n")[0]
    return None
