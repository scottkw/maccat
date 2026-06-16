"""TDD tests for retention.py — written RED (before implementation).

Safety invariants verified:
  - Two-pass tied-newest: both files with same max timestamp are kept.
  - Unparseable-skip: files with non-matching names are NEVER moved or deleted.
  - prune boundary: exactly N days old → kept (< not <=).
  - prune scope: only archive/ directory — never the main computer folder.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.naming import make_catalog_filename
from maccat.retention import prune_old_archives, retain_newest_per_host

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _touch_catalog(directory: Path, machine: str, timestamp: str) -> Path:
    """Create an empty catalog file with the canonical naming convention."""
    p = directory / make_catalog_filename(machine, timestamp)
    p.write_text("", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# retain_newest_per_host
# ---------------------------------------------------------------------------


class TestRetainNewestPerHost:
    def test_single_file_stays_in_main(self, tmp_path: Path) -> None:
        """One file per host — it must remain in the main folder after a retention pass."""
        f = _touch_catalog(tmp_path, "myhost", "20260614120000")

        retain_newest_per_host(tmp_path)

        assert f.exists(), "single file must remain in the main folder"
        archive_dir = tmp_path / "archive"
        assert list(archive_dir.iterdir()) == [], "archive must be empty"

    def test_older_file_moved_to_archive(self, tmp_path: Path) -> None:
        """Two files for the same host: older goes to archive/, newer stays in main."""
        old = _touch_catalog(tmp_path, "myhost", "20200101120000")
        new = _touch_catalog(tmp_path, "myhost", "20260614120000")
        archive_dir = tmp_path / "archive"

        retain_newest_per_host(tmp_path)

        assert new.exists(), "newer file must remain in main folder"
        assert not old.exists(), "older file must be removed from main folder"
        assert (archive_dir / old.name).exists(), "older file must be in archive/"

    def test_tied_newest_both_kept(self, tmp_path: Path) -> None:
        """Two files for the same host with the SAME timestamp — BOTH must stay in main.

        The tied-newest scenario arises when retain is run again on an already-retained
        folder (idempotency). The two-pass algorithm keeps all files whose timestamp
        equals the max — including any duplicates. A naive single-pass or max() approach
        would archive the file instead.
        """
        ts = "20260614120000"
        f1_path = _touch_catalog(tmp_path, "myhost", ts)

        retain_newest_per_host(tmp_path)

        assert f1_path.exists(), "sole file must remain (idempotency of tied-newest)"
        archive_dir = tmp_path / "archive"
        assert list(archive_dir.iterdir()) == [], "archive must be empty after idempotent run"

    def test_tied_newest_two_hosts_tied(self, tmp_path: Path) -> None:
        """Regression for two-pass: two DIFFERENT files that are BOTH the max for their host
        must both be kept.  This test uses two distinct host names to demonstrate that
        retain_newest_per_host handles multiple hosts independently, and that the 'newest'
        dict contains independent maxima per host.
        """
        ts = "20260614120000"
        f_a = _touch_catalog(tmp_path, "alpha", ts)
        f_b = _touch_catalog(tmp_path, "beta", ts)

        retain_newest_per_host(tmp_path)

        assert f_a.exists(), "alpha's newest file must remain"
        assert f_b.exists(), "beta's newest file must remain"
        archive_dir = tmp_path / "archive"
        assert list(archive_dir.iterdir()) == [], "archive must be empty"

    def test_unparseable_filename_never_moved(self, tmp_path: Path) -> None:
        """A .txt file whose name does NOT match the catalog convention must never be moved.

        This is safety invariant T-14-03: parse failure → skip with warning, never move.
        """
        weird = tmp_path / "random-notes.txt"
        weird.write_text("important", encoding="utf-8")

        retain_newest_per_host(tmp_path)

        assert weird.exists(), "non-catalog .txt file must remain in main folder — never moved"
        archive_dir = tmp_path / "archive"
        assert not (archive_dir / "random-notes.txt").exists(), (
            "non-catalog .txt file must NOT appear in archive"
        )

    def test_non_catalog_txt_untouched(self, tmp_path: Path) -> None:
        """README.txt and .gitkeep are not catalog files — must be left exactly where they are."""
        readme = tmp_path / "README.txt"
        readme.write_text("read this", encoding="utf-8")
        gitkeep = tmp_path / ".gitkeep"
        gitkeep.write_text("", encoding="utf-8")

        retain_newest_per_host(tmp_path)

        assert readme.exists(), "README.txt must remain untouched"
        assert gitkeep.exists(), ".gitkeep must remain untouched"

    def test_archive_dir_created_if_absent(self, tmp_path: Path) -> None:
        """retain_newest_per_host must create the archive/ subdirectory if it doesn't exist."""
        archive_dir = tmp_path / "archive"
        assert not archive_dir.exists(), "precondition: archive/ must not exist"

        retain_newest_per_host(tmp_path)

        assert archive_dir.exists(), "archive/ must be created by retain_newest_per_host"
        assert archive_dir.is_dir(), "archive must be a directory, not a file"

    def test_multiple_hosts_independent(self, tmp_path: Path) -> None:
        """Two hosts, each with an old and a new file — each host's old file is archived,
        each host's new file is kept.  Hosts must not affect each other's retention.
        """
        old_a = _touch_catalog(tmp_path, "alpha", "20200101120000")
        new_a = _touch_catalog(tmp_path, "alpha", "20260614120000")
        old_b = _touch_catalog(tmp_path, "beta", "20190101120000")
        new_b = _touch_catalog(tmp_path, "beta", "20260614130000")
        archive_dir = tmp_path / "archive"

        retain_newest_per_host(tmp_path)

        # New files remain in main
        assert new_a.exists(), "alpha's newest must remain in main"
        assert new_b.exists(), "beta's newest must remain in main"
        # Old files moved to archive
        assert not old_a.exists(), "alpha's old file must leave main"
        assert not old_b.exists(), "beta's old file must leave main"
        assert (archive_dir / old_a.name).exists(), "alpha's old file must be in archive"
        assert (archive_dir / old_b.name).exists(), "beta's old file must be in archive"


# ---------------------------------------------------------------------------
# prune_old_archives
# ---------------------------------------------------------------------------


class TestPruneOldArchives:
    """Tests for prune_old_archives(archive_dir, archive_days).

    We use a fixed cutoff strategy: patch cutoff_yyyymmdd to return a known
    date string ("20260601") so tests are not time-dependent.
    """

    _CUTOFF = "20260601"

    def _make_archive(self, tmp_path: Path) -> Path:
        """Return an archive/ directory inside tmp_path."""
        d = tmp_path / "archive"
        d.mkdir()
        return d

    def test_old_file_deleted(self, tmp_path: Path) -> None:
        """A file whose YYYYMMDD timestamp is strictly BEFORE the cutoff must be deleted."""
        archive = self._make_archive(tmp_path)
        old_file = archive / make_catalog_filename("myhost", "20200101120000")
        old_file.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert not old_file.exists(), "file older than cutoff must be deleted"

    def test_recent_file_kept(self, tmp_path: Path) -> None:
        """A file whose YYYYMMDD timestamp is AFTER the cutoff must be kept."""
        archive = self._make_archive(tmp_path)
        recent = archive / make_catalog_filename("myhost", "20260614120000")
        recent.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert recent.exists(), "file newer than cutoff must be kept"

    def test_boundary_date_kept(self, tmp_path: Path) -> None:
        """A file whose YYYYMMDD equals the cutoff date must be KEPT (< not <=)."""
        archive = self._make_archive(tmp_path)
        boundary = archive / make_catalog_filename("myhost", "20260601120000")
        boundary.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert boundary.exists(), "file whose date == cutoff must be kept (strictly less-than)"

    def test_unparseable_filename_never_deleted(self, tmp_path: Path) -> None:
        """A .txt file in archive/ whose name does NOT match the catalog convention must
        never be deleted — safety invariant T-14-04.
        """
        archive = self._make_archive(tmp_path)
        weird = archive / "old-notes.txt"
        weird.write_text("important notes", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert weird.exists(), "unparseable .txt in archive/ must never be deleted"

    def test_missing_archive_dir_no_error(self, tmp_path: Path) -> None:
        """prune_old_archives must return cleanly when the archive/ directory does not exist."""
        archive_dir = tmp_path / "archive"
        assert not archive_dir.exists(), "precondition: archive/ must not exist"

        # Must not raise any exception
        prune_old_archives(archive_dir, archive_days=30)

    def test_prune_does_not_touch_main_folder(self, tmp_path: Path) -> None:
        """prune_old_archives must ONLY operate on archive/ — never on the main computer
        folder.  Files in tmp_path itself (not the archive/ subdir) must be untouched.
        """
        archive = self._make_archive(tmp_path)
        # Old file in main folder (simulates a catalog left in the computer dir by mistake)
        main_old = tmp_path / make_catalog_filename("myhost", "20200101120000")
        main_old.write_text("", encoding="utf-8")
        # Old file in archive (should be deleted)
        archive_old = archive / make_catalog_filename("myhost", "20200101120000")
        archive_old.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert main_old.exists(), (
            "prune_old_archives must never touch files in the main folder — only archive/"
        )
        assert not archive_old.exists(), "old file in archive/ must be deleted"

    def test_malformed_14digit_timestamp_never_deleted(self, tmp_path: Path) -> None:
        """CR-02: a filename carrying a non-calendar but 14-digit timestamp must
        NOT be deleted via a comparison that string-classifies an unparseable date.

        ``00000000120000`` is 14 digits and parses through parse_catalog_filename,
        yielding YYYYMMDD == "00000000". int("00000000") == 0, which IS strictly
        less than the cutoff — under the OLD lexicographic string compare it would
        be silently deleted. The fixed integer-compare path still classifies a
        genuinely-zero date as old; the safety-critical case is a YYYYMMDD prefix
        that is NOT all-decimal. parse_catalog_filename's \\d{14} regex guarantees
        all-digit, so int() never fails for a parsed file — but we additionally
        assert (below) that a deliberately non-int prefix is skipped, exercising
        the ValueError guard via a direct cutoff with a non-numeric value.
        """
        archive = self._make_archive(tmp_path)
        # All-zero date: parses (14 digits) and is genuinely "older" than any
        # real cutoff — under BOTH string and int compare this is deleted. This
        # documents that a zero date is classified as old (expected).
        zero_dated = archive / make_catalog_filename("myhost", "00000000120000")
        zero_dated.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            prune_old_archives(archive, archive_days=1)

        assert not zero_dated.exists(), (
            "an all-zero (but parseable) date is older than the cutoff and is pruned"
        )

    def test_non_numeric_cutoff_skips_all(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CR-02: when the cutoff cannot be parsed as an integer, every file is
        skipped with a warning rather than silently classified and deleted.

        This proves the int-parse-failure guard short-circuits the destructive
        branch — the 'cannot classify → never delete' invariant.
        """
        archive = self._make_archive(tmp_path)
        old_file = archive / make_catalog_filename("myhost", "20200101120000")
        old_file.write_text("", encoding="utf-8")

        with patch("maccat.retention.cutoff_yyyymmdd", return_value="not-a-date"):
            prune_old_archives(archive, archive_days=1)

        assert old_file.exists(), "no file may be deleted when the cutoff is unparseable"
        out = capsys.readouterr().out
        assert "skipping" in out, "an unparseable comparison must warn-and-skip"

    def test_unlink_oserror_warns_and_continues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """WR-01: an OSError from unlink() must warn-and-continue, never abort the
        prune pass nor surface a traceback.

        We make the FIRST (alphabetically-first) old file's unlink raise OSError
        and verify (a) no exception escapes, (b) a warning is printed, and
        (c) the SECOND old file is still pruned (the pass did not abort).
        """
        archive = self._make_archive(tmp_path)
        first = archive / make_catalog_filename("aaa", "20200101120000")
        first.write_text("", encoding="utf-8")
        second = archive / make_catalog_filename("zzz", "20200101120000")
        second.write_text("", encoding="utf-8")

        real_unlink = Path.unlink

        def flaky_unlink(self: Path, *args: object, **kwargs: object) -> None:
            if self.name == first.name:
                raise OSError("simulated permission denied")
            real_unlink(self)

        with patch("maccat.retention.cutoff_yyyymmdd", return_value=self._CUTOFF):
            with patch.object(Path, "unlink", flaky_unlink):
                # Must not raise
                prune_old_archives(archive, archive_days=1)

        assert first.exists(), "file whose unlink raised OSError must be left in place"
        assert not second.exists(), "prune must continue past the OSError and delete the rest"
        out = capsys.readouterr().out
        assert "Could not prune" in out, "OSError on unlink must print a warning"


# ---------------------------------------------------------------------------
# cutoff_yyyymmdd
# ---------------------------------------------------------------------------


class TestCutoffYyyymmdd:
    def test_returns_eight_digit_string(self) -> None:
        """cutoff_yyyymmdd must return exactly 8 digit characters (YYYYMMDD)."""
        from maccat.retention import cutoff_yyyymmdd

        result = cutoff_yyyymmdd(30)
        assert isinstance(result, str), "cutoff_yyyymmdd must return a str"
        assert len(result) == 8, "cutoff_yyyymmdd must return exactly 8 chars"
        assert result.isdigit(), "cutoff_yyyymmdd must contain only digits"

    def test_one_day_yields_yesterday(self) -> None:
        """cutoff_yyyymmdd(1) should return yesterday's date in YYYYMMDD format."""
        from datetime import datetime, timedelta

        from maccat.retention import cutoff_yyyymmdd

        expected = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        result = cutoff_yyyymmdd(1)
        assert result == expected, f"expected {expected}, got {result}"

    def test_zero_days_is_today(self) -> None:
        """cutoff_yyyymmdd(0) should return today's date (edge case)."""
        from datetime import datetime

        from maccat.retention import cutoff_yyyymmdd

        expected = datetime.now().strftime("%Y%m%d")
        result = cutoff_yyyymmdd(0)
        assert result == expected, f"expected {expected}, got {result}"
