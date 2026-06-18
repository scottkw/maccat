"""Explicit safety-invariant suite (TEST-03).

Co-locates the three destructive-op invariants. No new logic — extracted from
test_retention.py and test_identity.py. Invariants:
  (a) prune_old_archives NEVER deletes files with unparseable timestamps;
  (b) retain_newest_per_host keeps ALL tied-newest files;
  (c) rename_machine HARD refuses to clobber an existing folder.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.identity import rename_machine
from maccat.naming import make_catalog_filename
from maccat.retention import prune_old_archives, retain_newest_per_host

pytestmark = pytest.mark.safety_invariant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _touch_catalog(directory: Path, machine: str, timestamp: str) -> Path:
    """Create a catalog file with the canonical naming convention and return its path."""
    p = directory / make_catalog_filename(machine, timestamp)
    p.write_text("", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Safety invariants
# ---------------------------------------------------------------------------


def test_prune_skips_unparseable_filename(tmp_path: Path) -> None:
    """INVARIANT (a): prune_old_archives NEVER deletes files with unparseable timestamps.

    WR-03: the filename MUST match the ``mac-software-list-*.md`` glob
    (retention.py:118) but fail ``parse_catalog_filename`` so the ``cf is None``
    safety-skip branch (retention.py:122-125) actually runs. The previous fixture
    name ``old-notes.txt`` did not match the glob at all, so it survived because it
    was invisible to prune — NOT because the safety skip fired. That made the
    invariant assertion vacuous.

    ``mac-software-list-[alpha]-2026.md`` matches the glob (prefix + ``.md``)
    but its timestamp is only 4 digits, so the 14-digit-timestamp regex in
    parse_catalog_filename returns None — exercising the real skip branch.

    Source: test_retention.py::TestPruneOldArchives::test_unparseable_filename_never_deleted
    """
    archive = tmp_path / "archive"
    archive.mkdir()
    # Matches the prune glob but has an unparseable (non-14-digit) timestamp.
    weird = archive / "mac-software-list-[alpha]-2026.md"
    weird.write_text("important notes", encoding="utf-8")

    with patch("maccat.retention.cutoff_yyyymmdd", return_value="20260601"):
        prune_old_archives(archive, archive_days=0)

    assert weird.exists(), (
        "glob-matching but unparseable file must never be deleted (cf is None skip)"
    )


def test_retain_keeps_all_tied_newest(tmp_path: Path) -> None:
    """INVARIANT (b): retain_newest_per_host keeps ALL files with the max timestamp.

    Uses two different host names with identical timestamps to cover the two-pass
    independence. Source:
    test_retention.py::TestRetainNewestPerHost::test_tied_newest_two_hosts_tied
    """
    ts = "20260614120000"
    f_alpha = _touch_catalog(tmp_path, "alpha", ts)
    f_beta = _touch_catalog(tmp_path, "beta", ts)

    retain_newest_per_host(tmp_path)

    assert f_alpha.exists(), "alpha tied-newest must be kept in main folder"
    assert f_beta.exists(), "beta tied-newest must be kept in main folder"
    archive_dir = tmp_path / "archive"
    assert not archive_dir.exists() or list(archive_dir.iterdir()) == [], (
        "archive must be empty"
    )


def test_rename_hard_refuses_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INVARIANT (c): rename_machine raises SystemExit when destination folder exists.

    Source: test_identity.py::TestRenameMachine::test_refuse_clobber_exits_nonzero
    """
    old_dir = tmp_path / "OldName"
    old_dir.mkdir()
    (old_dir / make_catalog_filename("OldName", "20260614120000")).write_text(
        "x", encoding="utf-8"
    )
    new_dir = tmp_path / "NewName"
    new_dir.mkdir()  # Already exists → refuse-clobber

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    with patch("builtins.input", side_effect=["1", "NewName"]):
        with pytest.raises(SystemExit):
            rename_machine(tmp_path)

    assert old_dir.is_dir(), "old folder untouched after refused rename"
    assert new_dir.is_dir(), "destination folder untouched after refused rename"
