"""Unit tests for reinstall/picker.py and reinstall/cli.py (TDD RED phase).

These tests define the expected behaviour of:
  - _find_newest_catalog: lexicographic timestamp selection
  - resolve_catalog_path: --from branch and picker-quit guard
  - run_reinstall: full pipeline, mode 0o644, absolute path print
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helper: build a minimal Namespace the way argparse would
# ---------------------------------------------------------------------------

def _make_args(
    from_path: str | None = None,
    computer: str | None = None,
    rename: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        from_path=from_path,
        computer=computer,
        rename=rename,
    )


# ---------------------------------------------------------------------------
# _find_newest_catalog — direct unit tests
# ---------------------------------------------------------------------------


class TestFindNewestCatalog:
    """Unit tests for the private _find_newest_catalog helper in picker.py."""

    def test_returns_none_for_empty_folder(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import _find_newest_catalog  # type: ignore[attr-defined]

        assert _find_newest_catalog(tmp_path) is None

    def test_returns_path_for_single_valid_file(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import _find_newest_catalog  # type: ignore[attr-defined]

        f = tmp_path / "mac-software-list-[TestMac]-20260601120000.txt"
        f.write_text("content", encoding="utf-8")
        result = _find_newest_catalog(tmp_path)
        assert result == f

    def test_returns_newest_by_timestamp(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import _find_newest_catalog  # type: ignore[attr-defined]

        older = tmp_path / "mac-software-list-[TestMac]-20260601120000.txt"
        newer = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
        older.write_text("old", encoding="utf-8")
        newer.write_text("new", encoding="utf-8")
        result = _find_newest_catalog(tmp_path)
        assert result == newer

    def test_skips_non_matching_filenames(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import _find_newest_catalog  # type: ignore[attr-defined]

        bad = tmp_path / "not-a-catalog.txt"
        bad.write_text("content", encoding="utf-8")
        assert _find_newest_catalog(tmp_path) is None

    def test_skips_directories_matching_glob(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import _find_newest_catalog  # type: ignore[attr-defined]

        # A directory that matches the glob pattern should be skipped
        d = tmp_path / "mac-software-list-[TestMac]-20260601120000.txt"
        d.mkdir()
        assert _find_newest_catalog(tmp_path) is None


# ---------------------------------------------------------------------------
# resolve_catalog_path — --from branch
# ---------------------------------------------------------------------------


class TestResolveCatalogPathFromBranch:
    """resolve_catalog_path when args.from_path is set."""

    def test_returns_resolved_path(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import resolve_catalog_path

        f = tmp_path / "catalog.txt"
        f.write_text("x", encoding="utf-8")
        args = _make_args(from_path=str(f))
        result = resolve_catalog_path(args)
        assert result == f.resolve()

    def test_exits_on_missing_file(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import resolve_catalog_path

        args = _make_args(from_path=str(tmp_path / "nonexistent.txt"))
        with pytest.raises(SystemExit) as exc:
            resolve_catalog_path(args)
        assert exc.value.code != 0

    def test_exits_on_directory_not_file(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import resolve_catalog_path

        args = _make_args(from_path=str(tmp_path))
        with pytest.raises(SystemExit) as exc:
            resolve_catalog_path(args)
        assert exc.value.code != 0

    @pytest.mark.skipif(
        os.geteuid() == 0,
        reason="root bypasses file permission checks; 0o000 is still readable",
    )
    def test_exits_cleanly_on_unreadable_file(self, tmp_path: Path) -> None:
        """WR-01: an existing-but-unreadable --from file fails with a clean
        SystemExit (ERROR: ...), not an uncaught PermissionError traceback."""
        from maccat.reinstall.picker import resolve_catalog_path

        f = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
        f.write_text("x", encoding="utf-8")
        os.chmod(f, 0o000)
        try:
            args = _make_args(from_path=str(f))
            with pytest.raises(SystemExit) as exc:
                resolve_catalog_path(args)
            assert exc.value.code != 0
            assert "not readable" in str(exc.value)
        finally:
            # Restore mode so tmp_path teardown can remove the file.
            os.chmod(f, 0o644)


# ---------------------------------------------------------------------------
# resolve_catalog_path — picker-quit guard
# ---------------------------------------------------------------------------


class TestResolveCatalogPathPickerQuit:
    """resolve_catalog_path returns None when picker returns None (user quit)."""

    def test_returns_none_on_picker_quit(self, tmp_path: Path) -> None:
        from maccat.reinstall.picker import resolve_catalog_path

        args = _make_args()  # no from_path → picker branch
        # select_computer returns None → user quit
        with (
            patch("maccat.identity.resolve_computer_selection", return_value=None),
            patch("maccat.identity.select_computer", return_value=None),
        ):
            result = resolve_catalog_path(args, catalog_repo=tmp_path)
        assert result is None

    def test_exits_when_no_catalog_repo_for_picker(self) -> None:
        from maccat.reinstall.picker import resolve_catalog_path

        args = _make_args()  # no from_path, no catalog_repo
        with pytest.raises(SystemExit) as exc:
            resolve_catalog_path(args, catalog_repo=None)
        assert exc.value.code != 0


# ---------------------------------------------------------------------------
# run_reinstall — pipeline, mode, path print
# ---------------------------------------------------------------------------


class TestRunReinstall:
    """Integration-style unit tests for run_reinstall orchestration."""

    @pytest.fixture()
    def fixture_catalog(self, tmp_path: Path) -> Path:
        """Minimal valid catalog file in tmp_path."""
        content = (
            "Installed Mac Software List\n"
            "------------------------------------\n"
            "\n"
            "Homebrew Packages\n"
            "------------------------------------\n"
            "wget (1.21.3)\n"
            "\n"
        )
        catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
        catalog.write_text(content, encoding="utf-8")
        return catalog

    def test_writes_reinstall_sh(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args(from_path=str(fixture_catalog))
        run_reinstall(args)
        output = tmp_path / "reinstall.sh"
        assert output.exists()

    def test_file_mode_is_0o644(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args(from_path=str(fixture_catalog))
        run_reinstall(args)
        output = tmp_path / "reinstall.sh"
        assert oct(output.stat().st_mode & 0o777) == "0o644"

    def test_shebang_is_present(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args(from_path=str(fixture_catalog))
        run_reinstall(args)
        output = tmp_path / "reinstall.sh"
        text = output.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash")

    def test_provenance_header_contains_source_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args(from_path=str(fixture_catalog))
        run_reinstall(args)
        output = tmp_path / "reinstall.sh"
        text = output.read_text(encoding="utf-8")
        assert fixture_catalog.name in text

    def test_prints_absolute_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args(from_path=str(fixture_catalog))
        run_reinstall(args)
        captured = capsys.readouterr()
        assert captured.out.strip() == str((tmp_path / "reinstall.sh").resolve())

    def test_returns_cleanly_on_picker_quit(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """run_reinstall should return (not raise) when picker returns None."""
        from maccat.reinstall.cli import run_reinstall

        monkeypatch.chdir(tmp_path)
        args = _make_args()  # no from_path → picker branch
        with (
            patch("maccat.identity.resolve_computer_selection", return_value=None),
            patch("maccat.identity.select_computer", return_value=None),
        ):
            # Should NOT raise SystemExit — clean return
            run_reinstall(args, catalog_repo=tmp_path)
        # No reinstall.sh should have been written
        assert not (tmp_path / "reinstall.sh").exists()
