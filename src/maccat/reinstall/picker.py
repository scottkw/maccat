"""Catalog path resolution for the reinstall subcommand.

Provides two functions:
  _find_newest_catalog(folder)        — private helper: pick the catalog file
                                        with the lexicographically greatest
                                        14-digit timestamp in its filename.
  resolve_catalog_path(args, ...)     — public: resolve --from PATH or invoke
                                        the interactive computer picker and
                                        return the newest catalog in that folder.

Identity imports (maccat.identity) are deferred inside the picker branch body
per PKG-03 (lazy import pattern).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from maccat.naming import parse_catalog_filename

# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _find_newest_catalog(folder: Path) -> Path | None:
    """Return the catalog file with the greatest filename timestamp, or None.

    Scans *folder* for files matching ``mac-software-list-*.md``.  Parses
    each filename via :func:`~maccat.naming.parse_catalog_filename` and
    selects the entry whose 14-digit YYYYMMDDHHMMSS timestamp is
    lexicographically greatest.  Lexicographic comparison is correct for this
    format (more-significant digits are always left of less-significant digits).

    Non-file entries (directories, symlinks, etc.) that match the glob are
    silently skipped (null-glob guard).

    Returns:
        The :class:`~pathlib.Path` of the newest catalog, or ``None`` if
        *folder* contains no parseable catalog files.
    """
    best_ts: str | None = None
    best_path: Path | None = None
    for f in folder.glob("mac-software-list-*.md"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue
        if best_ts is None or cf.timestamp > best_ts:
            best_ts = cf.timestamp
            best_path = f
    return best_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_catalog_path(
    args: argparse.Namespace,
    catalog_repo: Path | None = None,
) -> Path | None:
    """Resolve the catalog file to use for reinstall generation.

    Two branches:

    **--from PATH branch** (``args.from_path is not None``):
        Resolves the user-supplied path via
        :meth:`~pathlib.Path.expanduser` and :meth:`~pathlib.Path.resolve`.
        Exits with a descriptive error if the path is not a regular file.
        *catalog_repo* is ignored — ``--from`` mode is repo-agnostic.

    **Picker branch** (``args.from_path is None``):
        Requires *catalog_repo* (caller must pass a validated repo path).
        Reinstall is a **read-only** catalog operation — it must never mutate
        the catalog repo (WR-04).  Two sub-cases:

        - ``--computer NAME`` supplied: the name is validated against the
          *existing* computer folders discovered in the repo.  An unknown name
          fails cleanly with ``ERROR: ...`` and does NOT create a folder or
          rewrite ``machine-labels.tsv`` (the mutating ``select_computer``
          flag path is deliberately bypassed for this read-only operation).
        - no ``--computer``: the interactive ``select_computer`` menu is shown
          (per the locked CONTEXT decision to reuse the existing picker).
          Returns ``None`` if the user quits (caller handles this as a clean
          no-op return).

        In both sub-cases :func:`_find_newest_catalog` is then run on
        ``catalog_repo / computer`` and a missing catalog exits cleanly.

    Args:
        args:         Parsed argparse Namespace.  Must have ``.from_path``
                      and ``.computer`` attributes.
        catalog_repo: Resolved + validated catalog repo path.  Required for
                      the picker branch; may be ``None`` for ``--from`` mode.

    Returns:
        The resolved :class:`~pathlib.Path` to the catalog file, or ``None``
        when the user quit the interactive picker (clean exit, no file written).

    Raises:
        SystemExit: On any fatal resolution failure (missing file, no repo
                    provided for picker mode, no catalog found in folder).
    """
    # ------------------------------------------------------------------
    # Branch 1: explicit --from PATH
    # ------------------------------------------------------------------
    if args.from_path is not None:
        p = Path(args.from_path).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"ERROR: Catalog file not found or not a regular file: {p}")
        # WR-01: Path.is_file() returns True for a file the user cannot read
        # (e.g. mode 0o000). Probe readability here so an unreadable --from
        # path fails with the project's clean ERROR convention instead of an
        # uncaught PermissionError traceback mid-pipeline (parse_catalog ->
        # read_text). os.access uses the real uid/gid, matching the eventual
        # read.
        if not os.access(p, os.R_OK):
            sys.exit(f"ERROR: Catalog file is not readable: {p}")
        return p

    # ------------------------------------------------------------------
    # Branch 2: interactive picker
    # ------------------------------------------------------------------
    if catalog_repo is None:
        sys.exit("ERROR: catalog_repo is required for picker mode.")

    # Deferred imports per PKG-03 (lazy import pattern)
    from maccat.identity import (
        discover_computer_folders,
        resolve_computer_selection,
        select_computer,
    )

    computer: str | None
    computer_pre = resolve_computer_selection(computer=args.computer)
    if computer_pre is not None:
        # --computer NAME path: reinstall is read-only, so resolve the name
        # against EXISTING folders instead of select_computer's flag path
        # (which mkdir+upserts machine-labels.tsv — surprising mutation for a
        # read-only op, and would leave a stray empty dir for an unknown name;
        # WR-04). An unknown name fails cleanly without touching the repo.
        existing = discover_computer_folders(catalog_repo)
        if computer_pre not in existing:
            sys.exit(
                f"ERROR: No catalog folder named {computer_pre!r} in {catalog_repo}. "
                f"Known folders: {', '.join(existing) if existing else '(none)'}"
            )
        computer = computer_pre
    else:
        # Interactive selection — reuse the existing picker per the locked
        # CONTEXT decision. The no-catalog-in-folder case is handled cleanly
        # by _find_newest_catalog below.
        computer = select_computer(catalog_repo, computer_name=None)
        if computer is None:
            # User quit the picker — signal caller to return cleanly (no file written)
            return None

    folder = catalog_repo / computer
    catalog_path = _find_newest_catalog(folder)
    if catalog_path is None:
        sys.exit(f"ERROR: No catalog files found in {folder}")
    return catalog_path
