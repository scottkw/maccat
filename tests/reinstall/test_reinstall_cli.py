"""Integration tests for `maccat reinstall` subcommand — Phase 26.

Drives cli.run() in-process with patched sys.argv and monkeypatched cwd.
Mirrors the test structure of tests/test_cli.py.

All --from tests do NOT need a git repo — the 4b dispatch fires before
resolve_catalog_repo. The test_non_reinstall_invocation_unchanged test
uses the git_repo fixture from conftest.py.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Minimal valid catalog content (static — shared by all tests in this module)
# ---------------------------------------------------------------------------

_MINIMAL_CATALOG = (
    "Installed Mac Software List\n"
    "------------------------------------\n"
    "\n"
    "Homebrew Packages\n"
    "------------------------------------\n"
    "wget (1.21.3)\n"
    "\n"
)


# ---------------------------------------------------------------------------
# TestReinstallSubcommand
# ---------------------------------------------------------------------------


class TestReinstallSubcommand:
    """Integration tests for the maccat reinstall subcommand."""

    @pytest.fixture()
    def fixture_catalog(self, tmp_path: Path) -> Path:
        """Minimal valid catalog written to tmp_path.

        Filename follows the mac-software-list-[machine]-timestamp.txt
        convention so parse_catalog_filename can parse it if needed.
        Content includes a real Homebrew section so emit_reinstall_script
        produces a non-trivial script.
        """
        catalog = tmp_path / "mac-software-list-[TestMac]-20260616120000.txt"
        catalog.write_text(_MINIMAL_CATALOG, encoding="utf-8")
        return catalog

    # ------------------------------------------------------------------
    # test_from_path_writes_reinstall_sh
    # ------------------------------------------------------------------

    def test_from_path_writes_reinstall_sh(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        """--from PATH writes reinstall.sh to cwd with correct content."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )

        from maccat.cli import run

        run()  # must not raise SystemExit

        output = tmp_path / "reinstall.sh"
        assert output.exists(), "reinstall.sh must be written to cwd"
        assert oct(output.stat().st_mode & 0o777) == "0o644", "mode must be 0o644"
        text = output.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash"), "must start with shebang"
        assert fixture_catalog.name in text, "catalog filename must appear in provenance header"

    # ------------------------------------------------------------------
    # test_reinstall_sh_contains_generated_on_header
    # ------------------------------------------------------------------

    def test_reinstall_sh_contains_generated_on_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        """reinstall.sh must contain the 'Generated on:' provenance line."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )

        from maccat.cli import run

        run()

        text = (tmp_path / "reinstall.sh").read_text(encoding="utf-8")
        assert "Generated on:" in text, "provenance 'Generated on:' line must be present"

    # ------------------------------------------------------------------
    # test_rename_guard_does_not_fire
    # ------------------------------------------------------------------

    def test_rename_guard_does_not_fire(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        """Reinstall returns before git ops — git_pull must NOT be called."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )
        mock_pull = MagicMock()
        monkeypatch.setattr("maccat.gitops.git_pull", mock_pull)

        from maccat.cli import run

        run()

        mock_pull.assert_not_called()

    # ------------------------------------------------------------------
    # test_gen_path_not_triggered_by_reinstall
    # ------------------------------------------------------------------

    def test_gen_path_not_triggered_by_reinstall(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        """Criterion 3: reinstall dispatch returns before catalog generation.

        Write fixture_catalog to tmp_path; change cwd to a separate output
        subdirectory so we can assert no mac-software-list-*.txt was written
        to the output cwd (the fixture file lives in tmp_path, not output/).
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.chdir(output_dir)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(fixture_catalog)]
        )

        from maccat.cli import run

        run()

        txt_files = list(output_dir.glob("mac-software-list-*.txt"))
        assert len(txt_files) == 0, (
            f"No catalog .txt file should be written by reinstall; found: {txt_files}"
        )
        # reinstall.sh should still be there
        assert (output_dir / "reinstall.sh").exists()

    # ------------------------------------------------------------------
    # test_reinstall_rename_mutual_exclusion
    # ------------------------------------------------------------------

    def test_reinstall_rename_mutual_exclusion(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_catalog: Path,
    ) -> None:
        """--rename combined with reinstall subcommand must exit non-zero."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["maccat", "--rename", "reinstall", "--from", str(fixture_catalog)],
        )

        from maccat.cli import run

        with pytest.raises(SystemExit) as exc:
            run()
        assert exc.value.code != 0

    # ------------------------------------------------------------------
    # test_missing_from_path_errors
    # ------------------------------------------------------------------

    def test_missing_from_path_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """--from pointing to a nonexistent file must exit non-zero."""
        monkeypatch.chdir(tmp_path)
        nonexistent = tmp_path / "no-such-file.txt"
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--from", str(nonexistent)]
        )

        from maccat.cli import run

        with pytest.raises(SystemExit) as exc:
            run()
        assert exc.value.code != 0

    # ------------------------------------------------------------------
    # test_non_reinstall_invocation_unchanged
    # ------------------------------------------------------------------

    def test_non_reinstall_invocation_unchanged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """Non-reinstall invocation must still run the gen path (criterion 3 regression).

        Uses the git_repo fixture (a real bare git repo in tmp_path).  All
        side-effectful ops (git_pull, git_commit_and_push, select_computer,
        collectors, retention) are mocked so no real filesystem work happens.
        """
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(git_repo))
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "personal", "--no-commit"])

        mock_pull = MagicMock()
        mock_commit = MagicMock()
        monkeypatch.setattr("maccat.gitops.git_pull", mock_pull)
        monkeypatch.setattr("maccat.gitops.git_commit_and_push", mock_commit)
        monkeypatch.setattr(
            "maccat.identity.select_computer", MagicMock(return_value="personal")
        )
        monkeypatch.setattr("maccat.collectors.get_registry", MagicMock(return_value=[]))
        monkeypatch.setattr("maccat.retention.retain_newest_per_host", MagicMock())
        monkeypatch.setattr("maccat.retention.prune_old_archives", MagicMock())

        from maccat.cli import run

        run()  # must complete normally — no SystemExit

        # git_pull must have been called (gen path reached step 8)
        mock_pull.assert_called_once()
        # no reinstall.sh written to git_repo
        assert not (git_repo / "reinstall.sh").exists()

    # ------------------------------------------------------------------
    # WR-03: --computer accepted both before and after the subcommand
    # ------------------------------------------------------------------

    def test_computer_flag_after_subcommand_parses(self) -> None:
        """`maccat reinstall --computer NAME` must parse (not 'unrecognized')."""
        from maccat.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["reinstall", "--computer", "TestMac"])
        assert args.computer == "TestMac"
        assert args.from_path is None

    def test_computer_flag_before_subcommand_parses(self) -> None:
        """`maccat --computer NAME reinstall` must still parse and survive."""
        from maccat.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--computer", "TestMac", "reinstall"])
        # SUPPRESS on the subparser flag must not clobber the top-level value.
        assert args.computer == "TestMac"

    def test_computer_flag_post_subcommand_takes_precedence(self) -> None:
        """When --computer given on both sides, the post-subcommand value wins."""
        from maccat.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["--computer", "PRE", "reinstall", "--computer", "POST"]
        )
        assert args.computer == "POST"

    def test_computer_flag_forwarded_to_picker(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """`maccat reinstall --computer NAME` reaches the picker with the name.

        Drives run() in picker mode (no --from) with select_computer mocked.
        Asserts the computer name typed AFTER the subcommand is forwarded all
        the way to resolve_computer_selection / select_computer.
        """
        from maccat.naming import make_catalog_filename

        # Pre-populate the catalog folder so _find_newest_catalog succeeds.
        computer_dir = git_repo / "TestMac"
        computer_dir.mkdir()
        catalog = computer_dir / make_catalog_filename("TestMac", "20260616120000")
        catalog.write_text(_MINIMAL_CATALOG, encoding="utf-8")

        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(git_repo))
        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--computer", "TestMac"]
        )

        mock_resolve = MagicMock(return_value="TestMac")
        mock_select = MagicMock(return_value="TestMac")
        monkeypatch.setattr("maccat.identity.resolve_computer_selection", mock_resolve)
        monkeypatch.setattr("maccat.identity.select_computer", mock_select)

        from maccat.cli import run

        run()

        # The post-subcommand --computer value must have reached resolve.
        mock_resolve.assert_called_once_with(computer="TestMac")
        assert (git_repo / "reinstall.sh").exists()

    # ------------------------------------------------------------------
    # WR-02: picker-mode (step 4d) dispatch driven through run()
    # ------------------------------------------------------------------

    def test_picker_mode_writes_reinstall_sh_from_newest(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """WR-02: drive run() in picker mode (no --from) and assert reinstall.sh
        is produced from the NEWEST catalog in the selected folder.

        select_computer is stubbed to return an existing folder containing two
        catalogs; the script's provenance header must name the newer one. This
        locks the 4c (repo resolve/validate) + 4d (run_reinstall threading
        catalog_repo) wiring that --from tests never exercise.
        """
        from maccat.naming import make_catalog_filename

        computer_dir = git_repo / "PickedMac"
        computer_dir.mkdir()
        older = computer_dir / make_catalog_filename("PickedMac", "20260601120000")
        newer = computer_dir / make_catalog_filename("PickedMac", "20260616120000")
        older.write_text(_MINIMAL_CATALOG, encoding="utf-8")
        newer.write_text(_MINIMAL_CATALOG, encoding="utf-8")

        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(git_repo))
        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "reinstall"])
        # Interactive picker → stub select_computer to pick the folder.
        monkeypatch.setattr(
            "maccat.identity.select_computer",
            MagicMock(return_value="PickedMac"),
        )

        from maccat.cli import run

        run()

        output = git_repo / "reinstall.sh"
        assert output.exists(), "picker mode must write reinstall.sh"
        text = output.read_text(encoding="utf-8")
        assert newer.name in text, "provenance header must name the NEWEST catalog"
        assert older.name not in text, "the older catalog must not be selected"

    def test_picker_mode_quit_writes_nothing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """WR-02: picker quit (select_computer -> None) writes no file and
        returns cleanly through run()."""
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(git_repo))
        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "reinstall"])
        monkeypatch.setattr(
            "maccat.identity.select_computer", MagicMock(return_value=None)
        )

        from maccat.cli import run

        run()  # must not raise SystemExit

        assert not (git_repo / "reinstall.sh").exists()

    # ------------------------------------------------------------------
    # WR-04: read-only picker must not mutate the repo on a bad --computer
    # ------------------------------------------------------------------

    def test_unknown_computer_fails_clean_no_stray_dir(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """WR-04: `maccat reinstall --computer UNKNOWN` exits cleanly without
        creating a stray empty folder or rewriting machine-labels.tsv."""
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(git_repo))
        monkeypatch.chdir(git_repo)
        monkeypatch.setattr(
            sys, "argv", ["maccat", "reinstall", "--computer", "GhostMac"]
        )

        from maccat.cli import run

        with pytest.raises(SystemExit) as exc:
            run()
        assert exc.value.code != 0

        # No stray folder and no labels TSV mutation for the read-only op.
        assert not (git_repo / "GhostMac").exists(), "must not create a stray folder"
        assert not (git_repo / "machine-labels.tsv").exists(), (
            "read-only reinstall must not write machine-labels.tsv"
        )
        assert not (git_repo / "reinstall.sh").exists()
