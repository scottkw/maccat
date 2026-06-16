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
import sys
from pathlib import Path

from maccat.naming import parse_catalog_filename

# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _find_newest_catalog(folder: Path) -> Path | None:
    """Return the catalog file with the greatest filename timestamp, or None.

    Scans *folder* for files matching ``mac-software-list-*.txt``.  Parses
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
    for f in folder.glob("mac-software-list-*.txt"):
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
        Calls ``resolve_computer_selection`` then ``select_computer`` to get
        the chosen computer folder name.  Returns ``None`` if the user quits
        the picker (caller handles this as a clean no-op return).
        Then calls :func:`_find_newest_catalog` on
        ``catalog_repo / computer`` and exits if no catalog is found.

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
        return p

    # ------------------------------------------------------------------
    # Branch 2: interactive picker
    # ------------------------------------------------------------------
    if catalog_repo is None:
        sys.exit("ERROR: catalog_repo is required for picker mode.")

    # Deferred imports per PKG-03 (lazy import pattern)
    from maccat.identity import resolve_computer_selection, select_computer

    computer_pre = resolve_computer_selection(computer=args.computer)
    computer = select_computer(catalog_repo, computer_name=computer_pre)
    if computer is None:
        # User quit the picker — signal caller to return cleanly (no file written)
        return None

    folder = catalog_repo / computer
    catalog_path = _find_newest_catalog(folder)
    if catalog_path is None:
        sys.exit(f"ERROR: No catalog files found in {folder}")
    return catalog_path
