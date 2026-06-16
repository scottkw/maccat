"""Output format layer — emit_item, flush_section, version_sort_tail.

Byte-parity contract with update-list.sh functions emit_item (line 1243),
flush_section (line 1290), and the sort -V pattern at line 2121.

CRITICAL: Do NOT use Python built-in sort here — it diverges from LC_ALL=C
sort -f for mixed-case and non-ASCII names. The subprocess calls to the system
sort binary are mandatory for byte-identical output to the zsh reference.
"""
from __future__ import annotations

import os
import subprocess


def emit_item(name: str, version: str, id_: str) -> str | None:
    """FMT-01 degradation rules. Returns None for all-empty input.

    name + version + id  →  "name (version) [id]"
    name + version       →  "name (version)"
    name + id            →  "name [id]"
    name only            →  "name"
    id only (no name)    →  "id"           (id promoted; brackets suppressed)
    id + version         →  "id (version)" (id promoted; brackets suppressed)
    all empty            →  None

    Mirrors update-list.sh:1243–1269 exactly.
    The id-as-name promotion check MUST be first, before format-building conditionals.
    """
    # id-as-name promotion: suppress bracket duplication (avoids "id [id]")
    if not name and id_:
        name, id_ = id_, ""

    # Build line per FMT-01 rules
    if name and version and id_:
        return f"{name} ({version}) [{id_}]"
    elif name and version:
        return f"{name} ({version})"
    elif name and id_:
        return f"{name} [{id_}]"
    elif name:
        return name
    return None


def flush_section(lines: list[str]) -> list[str]:
    """Sort + dedup via LC_ALL=C sort -f -u. Returns ['  (none found)'] if empty.

    Do NOT use Python built-in sort — it diverges from LC_ALL=C sort -f for
    mixed-case and non-ASCII names. The subprocess call is mandatory for byte parity.

    Mirrors update-list.sh:1290–1297 exactly.
    Empty buffer → ["  (none found)"] (exactly two spaces — verified from line 1292).
    """
    if not lines:
        return ["  (none found)"]

    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-f", "-u"],
        input="\n".join(lines) + "\n",  # mirrors: printf "%s\n" "${lines[@]}"
        capture_output=True,
        text=True,
        env=env,
    )
    # WR-03: never write a partial/empty stdout as if it were a complete section.
    # On the Python side the result is materialized before write, so a non-zero
    # sort exit must abort and let CatalogWriter discard the tmp file rather than
    # silently committing a truncated section.
    if result.returncode != 0:
        raise RuntimeError(f"sort -f -u failed (rc={result.returncode}): {result.stderr!r}")
    # rstrip("\n").split("\n") → no trailing empty string; matches zsh output exactly
    return result.stdout.rstrip("\n").split("\n")


def version_sort_tail(candidates: list[str]) -> str | None:
    """Return the highest version string using sort -V (numeric version sort).

    Mirrors update-list.sh:2121: ls -1 | grep -E '^[0-9]' | sort -V | tail -1
    The `^[0-9]` pre-filter is applied here (matching the zsh pipe) so Chrome
    internal entries like `_metadata` and `_crx_invalidation_map` cannot "steal
    the slot" — see the zsh comment at update-list.sh:2119-2120. Only entries
    whose first character is an ASCII digit are considered.

    Python lexicographic sort gets version comparison wrong (9 > 14 lexicographically),
    so the system `sort -V` subprocess is used for numeric version ordering.
    """
    # Pre-filter to version-like entries (zsh: grep -E '^[0-9]'). This drops
    # non-version directories before sort -V so they cannot win tail -1.
    versioned = [c for c in candidates if c[:1].isascii() and c[:1].isdigit()]
    if not versioned:
        return None

    env = {**os.environ, "LC_ALL": "C"}
    result = subprocess.run(
        ["sort", "-V"],
        input="\n".join(versioned) + "\n",
        capture_output=True,
        text=True,
        env=env,
    )
    # WR-03: a non-zero sort exit must abort rather than silently selecting from
    # partial stdout (which could pick the wrong version directory).
    if result.returncode != 0:
        raise RuntimeError(f"sort -V failed (rc={result.returncode}): {result.stderr!r}")
    lines = result.stdout.rstrip("\n").split("\n")
    return lines[-1] if lines and lines[-1] else None
