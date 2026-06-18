"""Convert subcommand orchestrator.

Provides :func:`run_convert`, which drives the complete pipeline:
  1. Validate the --from file exists and is readable.
  2. Parse the .txt filename for the computer label.
  3. Guard: target .md must not already exist (no-clobber USER OVERRIDE).
  4. parse_catalog() -> ParsedCatalog.
  5. Bridge: ParsedCatalog -> list[Section] (raw=True, skip header section).
  6. Synthesize frontmatter (now(), gethostname(), __version__).
  7. render_markdown_catalog() -> markdown string.
  8. Write .md (atomicity gate).
  9. Unlink .txt (ONLY after .md write succeeded -- CONV-03 invariant).
  10. git_commit_convert() unless --no-commit.

All maccat.* imports are deferred inside :func:`run_convert`'s body per PKG-03.
"""
from __future__ import annotations

import argparse
import os
import re
import socket
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants (no maccat.* imports at module level -- PKG-03)
# ---------------------------------------------------------------------------

# Matches: mac-software-list-[computer]-YYYYMMDDHHMMSS.txt
# Derived from naming.py::_FILENAME_RE which uses \.md$ -- swap to \.txt$
_TXT_FILENAME_RE = re.compile(
    r"^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$"
)

_HEADER_TITLE = "Installed Mac Software List"


def run_convert(args: argparse.Namespace) -> None:
    """Convert a legacy .txt catalog to a .md catalog in-place.

    Validates input, bridges parsed sections, renders markdown, and performs
    an atomic replace (write .md then unlink .txt).  Optionally commits both
    changes in a single git commit via git_commit_convert.

    Args:
        args: Parsed argparse Namespace (must have ``.from_path`` and
              ``.no_commit`` attributes).
    """
    # Deferred imports per PKG-03
    from maccat import __version__
    from maccat.catalog.markdown import render_markdown_catalog
    from maccat.collectors.base import Section
    from maccat.reinstall.parser import parse_catalog

    txt_path = Path(args.from_path).expanduser().resolve()

    # 1. File existence check
    if not txt_path.is_file():
        sys.exit(f"ERROR: Catalog file not found or not a regular file: {txt_path}")

    # 2. Readability check (mirrors reinstall/picker.py WR-01 pattern)
    if not os.access(txt_path, os.R_OK):
        sys.exit(f"ERROR: Catalog file is not readable: {txt_path}")

    # 3. Filename must be a recognizable legacy .txt catalog (derives computer label)
    m = _TXT_FILENAME_RE.match(txt_path.name)
    if not m:
        sys.exit(
            f"ERROR: {txt_path.name!r} is not a recognizable legacy catalog filename. "
            f"Expected: mac-software-list-[computer]-YYYYMMDDHHMMSS.txt"
        )
    computer = m.group("machine")

    # 4. No-clobber guard (USER OVERRIDE -- do NOT remove this check)
    md_path = txt_path.with_suffix(".md")
    if md_path.exists():
        sys.exit(
            f"ERROR: Target already exists: {md_path}\n"
            f"Remove it first, then re-run: maccat convert --from {txt_path}"
        )

    # 5. Parse the legacy .txt (never raises -- CONV-03: graceful degradation)
    parsed = parse_catalog(txt_path)

    # 6. Bridge: ParsedCatalog -> list[Section], skip header section.
    # The emitter writes "# Installed Mac Software List" as its own H1
    # unconditionally; passing this section would produce a spurious ## heading.
    # The `degraded` flag is intentionally not surfaced -- both empty and degraded
    # sections render as "(none found)" in the markdown emitter (by design).
    sections: list[Section] = [
        Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)
        for ps in parsed.sections
        if ps.title != _HEADER_TITLE
    ]

    # 7. Synthesize frontmatter (USER OVERRIDE: "Fill from current machine").
    # computer: from .txt filename (already extracted above).
    # generated: now() -- NOT the original filename timestamp (locked decision).
    # hostname: current machine's gethostname().
    # maccat_version: current maccat.__version__.
    # Output filename preserves the ORIGINAL timestamp from the .txt basename --
    # filename ts intentionally differs from frontmatter generated; do NOT reconcile.
    now = datetime.now()
    generated_iso = now.strftime("%Y-%m-%dT%H:%M:%S")

    # 8. Render markdown
    content = render_markdown_catalog(
        sections,
        computer=computer,
        hostname=socket.gethostname(),
        generated=generated_iso,
        maccat_version=__version__,
    )

    # 9. Write .md -- atomicity gate: .txt is NOT touched until this succeeds
    md_path.write_text(content, encoding="utf-8")

    # 10. Remove .txt (ONLY after .md write succeeded -- CONV-03 invariant)
    txt_path.unlink()

    print(f"Converted: {txt_path.name} -> {md_path.name}")

    # 11. Git commit (unless --no-commit)
    if not args.no_commit:
        from maccat import gitops

        # Heuristic: .txt lives at <repo>/<computer>/filename -> parent.parent = repo.
        # If the heuristic is wrong, git_commit_convert warns-and-continues.
        catalog_repo = txt_path.parent.parent
        gitops.git_commit_convert(catalog_repo, md_path, txt_path)
