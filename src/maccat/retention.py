"""Catalog retention and archive prune functions.

Implements two safety-critical operations:
  - retain_newest_per_host: two-pass per-host retention; tied-newest files are
    both kept; unparseable filenames are skipped (never moved).
  - prune_old_archives: N-day cutoff prune operating only on archive/;
    unparseable filenames are skipped (never deleted).

Zsh analogs (update-list.sh):
  - retain_newest_per_host: lines 942–1004
  - prune_old_archives: lines 1022–1064
  - cutoff date: line 1036 (BSD `date -v-Nd +%Y%m%d`)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from maccat.naming import parse_catalog_filename


def cutoff_yyyymmdd(archive_days: int) -> str:
    """Return the prune cutoff date as an 8-char YYYYMMDD string.

    Equivalent to BSD `date -v-{archive_days}d +%Y%m%d` (macOS).
    Uses local time to match the zsh reference implementation.

    Args:
        archive_days: Number of days to subtract from today.

    Returns:
        YYYYMMDD string (e.g. "20260515") parsed to int for numeric comparison.
    """
    return (datetime.now() - timedelta(days=archive_days)).strftime("%Y%m%d")


def retain_newest_per_host(target_dir: Path) -> None:
    """Move all but the newest catalog(s) per host to target_dir/archive/.

    Two-pass algorithm (mirrors update-list.sh lines 942–1004):
      Pass 1: Glob mac-software-list-*.md in target_dir (NOT archive/).
              For each file, parse via parse_catalog_filename.
              Unparseable → print warning and continue (never touch the file).
              Build newest: dict[machine, str] = max timestamp per machine.
      Pass 2: Glob again.
              Unparseable → continue silently (already warned in pass 1).
              cf.timestamp == newest[cf.machine] → keep (handles tied-newest
              correctly: both tied files share the same max timestamp, so both
              pass the equality check and both stay).
              Otherwise → rename to archive_dir / f.name.
              OSError on rename → print warning, leave file in place.

    Creates archive_dir with mkdir(exist_ok=True) unconditionally at the start.

    Args:
        target_dir: The computer folder to sweep (e.g. catalog_repo / "MyMac").
                    The archive/ subdirectory is target_dir / "archive".
    """
    archive_dir = target_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Pass 1: determine newest timestamp per machine label
    newest: dict[str, str] = {}
    for f in target_dir.glob("mac-software-list-*.md"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            print(f"  WARNING: Could not parse hostname/timestamp from: {f.name}")
            continue
        if cf.machine not in newest or cf.timestamp > newest[cf.machine]:
            newest[cf.machine] = cf.timestamp

    # Pass 2: archive non-newest files; keep all tied-newest
    for f in target_dir.glob("mac-software-list-*.md"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            continue  # already warned in pass 1
        if cf.timestamp == newest.get(cf.machine, ""):
            continue  # keep — this correctly handles tied-newest
        try:
            f.rename(archive_dir / f.name)
            print(f"  Archived: {f.name}")
        except OSError:
            print(f"  WARNING: Could not archive: {f.name} — leaving in place")


def prune_old_archives(archive_dir: Path, archive_days: int) -> None:
    """Delete archive files whose YYYYMMDD date is strictly older than the cutoff.

    Prune algorithm (mirrors update-list.sh lines 1022–1064):
      Early return if archive_dir does not exist.
      Cutoff = cutoff_yyyymmdd(archive_days).
      For each mac-software-list-*.md in archive_dir:
        - Parse via parse_catalog_filename.
        - If None: print warning and continue — NEVER delete unparseable files.
        - Extract first 8 chars of timestamp (YYYYMMDD).
        - Integer comparison (matching zsh ``[[ "$timestamp" -lt "$cutoff" ]]``,
          update-list.sh line 1049): parse both operands as int; on int-parse
          failure print a warning and skip — NEVER delete a file we cannot
          confidently classify. If file_date < cutoff_date → unlink + print
          "Pruned:" (wrapped in try/except OSError → warn-and-continue).

    This function operates ONLY on archive_dir — it never touches files in the
    parent computer folder.

    Args:
        archive_dir: Path to the archive/ subdirectory to sweep.
        archive_days: Files older than this many days are deleted.
    """
    if not archive_dir.is_dir():
        return  # normal: no archives yet — not an error condition

    cutoff = cutoff_yyyymmdd(archive_days)
    for f in archive_dir.glob("mac-software-list-*.md"):
        if not f.is_file():
            continue
        cf = parse_catalog_filename(f.name)
        if cf is None:
            # Safety invariant T-14-04: never delete a file we cannot parse
            print(f"  WARNING: Could not parse timestamp from: {f.name} — skipping")
            continue
        file_yyyymmdd = cf.timestamp[:8]  # first 8 chars = YYYYMMDD
        # Compare as INTEGERS to match zsh's `-lt` arithmetic (CR-02). On a
        # value zsh cannot parse as an integer it errors and skips; Python
        # string `<` would silently classify (and potentially delete) it.
        # Skip-on-parse-failure preserves the "cannot classify → never
        # delete" safety invariant on this destructive path.
        try:
            file_date = int(file_yyyymmdd)
            cutoff_date = int(cutoff)
        except ValueError:
            print(f"  WARNING: Could not parse date from: {f.name} — skipping")
            continue
        if file_date < cutoff_date:
            # Guard unlink: a permission error, a file removed by another
            # process between glob and unlink, or a read-only filesystem must
            # warn-and-continue rather than abort the whole prune pass and
            # surface a traceback (zsh parity, WR-01).
            try:
                f.unlink()
                print(f"  Pruned: {f.name}")
            except OSError:
                print(f"  WARNING: Could not prune: {f.name} — leaving in place")
