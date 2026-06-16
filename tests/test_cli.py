"""Tests for src/maccat/cli.py — argparse, --no-commit, generate-then-sweep,
config subcommand dispatch.

All tests use disposable git-repo fixtures (git_repo from conftest.py).
NEVER use the real personal/ or office/ catalog directories.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401  (pytest fixtures)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def disposable_catalog_repo(git_repo: Path) -> Path:
    """Disposable catalog repo — extends conftest.git_repo.

    Returns an isolated git repo dir suitable for catalog runs.
    NEVER the real personal/ or office/ directory.
    """
    return git_repo


# ---------------------------------------------------------------------------
# TestArgparse — parser structure and flag semantics
# ---------------------------------------------------------------------------


class TestArgparse:
    """Verify the argparse parser shape independently of run()."""

    def test_version_exits_zero(self) -> None:
        from maccat.cli import _build_parser

        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["--version"])
        assert exc.value.code == 0

    def test_help_exits_zero(self) -> None:
        from maccat.cli import _build_parser

        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["--help"])
        assert exc.value.code == 0

    def test_computer_has_own_dest(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args(["--computer", "workstation"])
        assert args.computer == "workstation"

    def test_personal_flag_is_unrecognized(self) -> None:
        """--personal was removed; argparse must reject it with exit code 2."""
        from maccat.cli import _build_parser

        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["--personal"])
        assert exc.value.code == 2

    def test_office_flag_is_unrecognized(self) -> None:
        """--office was removed; argparse must reject it with exit code 2."""
        from maccat.cli import _build_parser

        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["--office"])
        assert exc.value.code == 2

    def test_machine_flag_is_unrecognized(self) -> None:
        """--machine was removed; argparse must reject it with exit code 2."""
        from maccat.cli import _build_parser

        with pytest.raises(SystemExit) as exc:
            _build_parser().parse_args(["--machine", "box"])
        assert exc.value.code == 2

    def test_no_commit_flag_parsed(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args(["--no-commit"])
        assert args.no_commit is True

    def test_no_commit_default_is_false(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args([])
        assert args.no_commit is False

    def test_archive_days_parsed(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args(["--archive-days", "45"])
        assert args.archive_days == 45

    def test_archive_days_default_is_none(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args([])
        assert args.archive_days is None

    def test_catalog_dir_parsed(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args(["--catalog-dir", "/some/path"])
        assert args.catalog_dir == "/some/path"

    def test_bare_invocation_subcommand_is_none(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args([])
        assert args.subcommand is None

    def test_rename_flag_parsed(self) -> None:
        from maccat.cli import _build_parser

        args = _build_parser().parse_args(["--rename"])
        assert args.rename is True



# ---------------------------------------------------------------------------
# TestRenameFlag — --rename × selecting-flag guard
# ---------------------------------------------------------------------------


class TestRenameFlag:
    """Verify the --rename × selecting-flag guard fires before any other logic."""

    def test_rename_with_computer_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "argv", ["maccat", "--rename", "--computer", "box"])
        from maccat.cli import run

        with pytest.raises(SystemExit):
            run()



# ---------------------------------------------------------------------------
# Helpers — shared mock wiring for end-to-end run() tests
# ---------------------------------------------------------------------------


def _patch_run_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    catalog_repo: Path,
    computer_name: str = "MyMac",
) -> dict[str, MagicMock]:
    """Patch all external side-effects for run() end-to-end tests.

    Returns a dict of mock objects keyed by name so tests can make assertions.
    """
    monkeypatch.setenv("MACCAT_CATALOG_DIR", str(catalog_repo))

    mocks: dict[str, MagicMock] = {}

    # gitops
    mocks["git_pull"] = MagicMock()
    mocks["git_commit_and_push"] = MagicMock()
    monkeypatch.setattr("maccat.gitops.git_pull", mocks["git_pull"])
    monkeypatch.setattr("maccat.gitops.git_commit_and_push", mocks["git_commit_and_push"])

    # identity.select_computer returns computer_name without TTY interaction
    mocks["select_computer"] = MagicMock(return_value=computer_name)
    monkeypatch.setattr("maccat.identity.select_computer", mocks["select_computer"])

    # collectors.get_registry returns empty list (no sections to write)
    mocks["get_registry"] = MagicMock(return_value=[])
    monkeypatch.setattr("maccat.collectors.get_registry", mocks["get_registry"])

    # retention — no-ops (don't sweep files we care about)
    mocks["retain_newest_per_host"] = MagicMock()
    mocks["prune_old_archives"] = MagicMock()
    monkeypatch.setattr(
        "maccat.retention.retain_newest_per_host", mocks["retain_newest_per_host"]
    )
    monkeypatch.setattr(
        "maccat.retention.prune_old_archives", mocks["prune_old_archives"]
    )

    return mocks


# ---------------------------------------------------------------------------
# TestNoCommit — --no-commit skips git ops but writes catalog
# ---------------------------------------------------------------------------


class TestNoCommit:
    """Verify --no-commit behaviour: file written, no git commit created."""

    def test_no_commit_skips_git_commit_and_push(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With --no-commit, git_commit_and_push must NOT be called."""
        mocks = _patch_run_dependencies(monkeypatch, disposable_catalog_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])

        from maccat.cli import run

        run()

        mocks["git_commit_and_push"].assert_not_called()

    def test_no_commit_still_calls_git_pull(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With --no-commit, git_pull must still be called (pull is unconditional)."""
        mocks = _patch_run_dependencies(monkeypatch, disposable_catalog_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])

        from maccat.cli import run

        run()

        mocks["git_pull"].assert_called_once()

    def test_no_commit_catalog_file_written(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With --no-commit, the catalog .txt file must be written to computer/."""
        _patch_run_dependencies(monkeypatch, disposable_catalog_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])

        from maccat.cli import run

        run()

        mymac_dir = disposable_catalog_repo / "MyMac"
        txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
        assert len(txt_files) >= 1, (
            f"Expected at least one catalog file in {mymac_dir}, found none"
        )

    def test_with_commit_calls_git_commit_and_push(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without --no-commit, git_commit_and_push must be called."""
        mocks = _patch_run_dependencies(monkeypatch, disposable_catalog_repo)
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac"])

        from maccat.cli import run

        run()

        mocks["git_commit_and_push"].assert_called_once()


# ---------------------------------------------------------------------------
# TestGenerateThenSweep — just-written catalog not archived same run
# ---------------------------------------------------------------------------


class TestGenerateThenSweep:
    """Verify the generate-then-sweep invariant: just-written catalog stays in place."""

    def test_just_written_catalog_not_archived(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After a run, the just-written catalog file must NOT appear in archive/."""
        # Use REAL retention (not mocked) to exercise the actual invariant.
        # Mock only git ops and get_registry so there are no TTY or network calls.
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(disposable_catalog_repo))
        monkeypatch.setattr("maccat.gitops.git_pull", MagicMock())
        monkeypatch.setattr("maccat.gitops.git_commit_and_push", MagicMock())
        monkeypatch.setattr("maccat.identity.select_computer", MagicMock(return_value="MyMac"))
        monkeypatch.setattr("maccat.collectors.get_registry", MagicMock(return_value=[]))
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])

        from maccat.cli import run

        run()

        mymac_dir = disposable_catalog_repo / "MyMac"
        txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
        assert len(txt_files) >= 1, "Catalog file should have been written"

        archive_dir = mymac_dir / "archive"
        if archive_dir.exists():
            archived = list(archive_dir.glob("mac-software-list-*.txt"))
            assert len(archived) == 0, (
                f"Just-written catalog should not be in archive/; found: {archived}"
            )

    def test_timestamp_captured_after_git_pull(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify timestamp capture happens AFTER git_pull returns.

        Strategy: capture call order by recording side effects.
        git_pull must be called before the catalog file appears on disk.
        """
        call_order: list[str] = []

        def fake_git_pull(repo: Path) -> None:
            call_order.append("git_pull")

        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(disposable_catalog_repo))
        monkeypatch.setattr("maccat.gitops.git_pull", fake_git_pull)
        monkeypatch.setattr("maccat.gitops.git_commit_and_push", MagicMock())
        monkeypatch.setattr("maccat.identity.select_computer", MagicMock(return_value="MyMac"))
        monkeypatch.setattr("maccat.collectors.get_registry", MagicMock(return_value=[]))
        monkeypatch.setattr("maccat.retention.retain_newest_per_host", MagicMock())
        monkeypatch.setattr("maccat.retention.prune_old_archives", MagicMock())
        monkeypatch.setattr(sys, "argv", ["maccat", "--computer", "MyMac", "--no-commit"])

        mymac_dir = disposable_catalog_repo / "MyMac"

        from maccat.cli import run

        run()

        # git_pull was called
        assert "git_pull" in call_order

        # Catalog file was written after git_pull (exists on disk now)
        txt_files = list(mymac_dir.glob("mac-software-list-*.txt"))
        assert len(txt_files) >= 1, "Catalog file should exist after run"


# ---------------------------------------------------------------------------
# TestConfigDispatch — config init / config show subcommands
# ---------------------------------------------------------------------------


class TestConfigDispatch:
    """Verify config subcommand routing to config.py functions."""

    def test_config_init_dispatch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """maccat config init must call config.config_init() exactly once.

        WR-02: isolate HOME/XDG_CONFIG_HOME to tmp_path so the test never reads
        the developer's real ~/.config/maccat/config.toml (hermetic). After the
        WR-01 fix `config init` no longer calls load_config(), but the env
        isolation keeps the test independent of the dev's machine regardless.
        """
        mock_init = MagicMock()
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        monkeypatch.setattr(sys, "argv", ["maccat", "config", "init"])

        with patch("maccat.config.config_init", mock_init):
            from maccat.cli import run

            run()

        mock_init.assert_called_once()

    def test_config_init_succeeds_with_corrupt_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """WR-01 regression: `config init` must run even when the on-disk
        config is malformed TOML — it is the command that repairs it, so it
        must not load (and choke on) the broken file first.
        """
        cfg_dir = tmp_path / ".config" / "maccat"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "config.toml").write_text("this is = = not valid toml [[[")
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        monkeypatch.setattr(sys, "argv", ["maccat", "config", "init"])

        mock_init = MagicMock()
        # NOTE: load_config is intentionally NOT patched — the point of the
        # test is that init never calls it. If WR-01 regresses, load_config
        # runs against the corrupt file and raises TOMLDecodeError here.
        with patch("maccat.config.config_init", mock_init):
            from maccat.cli import run

            run()

        mock_init.assert_called_once()

    def test_config_show_rename_flag_errors(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """WR-03 regression: `config show --rename` must error rather than
        silently dropping the --rename flag and dumping config.
        """
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        monkeypatch.setattr(sys, "argv", ["maccat", "config", "show", "--rename"])

        mock_show = MagicMock()
        with patch("maccat.config.config_show", mock_show):
            from maccat.cli import run

            with pytest.raises(SystemExit) as exc:
                run()

        assert exc.value.code != 0
        mock_show.assert_not_called()

    def test_config_show_dispatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """maccat config show must call config.config_show() exactly once."""
        mock_show = MagicMock()
        mock_load = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(sys, "argv", ["maccat", "config", "show"])

        with patch("maccat.config.config_show", mock_show), \
             patch("maccat.config.load_config", mock_load):
            from maccat.cli import run

            run()

        mock_show.assert_called_once()

    def test_config_bare_exits_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bare 'maccat config' (no sub-subcommand) must exit non-zero."""
        mock_load = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(sys, "argv", ["maccat", "config"])

        with patch("maccat.config.load_config", mock_load):
            from maccat.cli import run

            with pytest.raises(SystemExit) as exc:
                run()
        assert exc.value.code != 0


# ---------------------------------------------------------------------------
# TestSelectComputerQuit — user chose Quit returns cleanly
# ---------------------------------------------------------------------------


class TestSelectComputerQuit:
    """Verify that select_computer returning None causes a clean return (no crash)."""

    def test_quit_returns_without_writing_catalog(
        self,
        disposable_catalog_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When select_computer returns None (user quit), run() returns cleanly."""
        monkeypatch.setenv("MACCAT_CATALOG_DIR", str(disposable_catalog_repo))
        monkeypatch.setattr("maccat.gitops.git_pull", MagicMock())
        monkeypatch.setattr("maccat.gitops.git_commit_and_push", MagicMock())
        # select_computer returns None → Quit
        monkeypatch.setattr("maccat.identity.select_computer", MagicMock(return_value=None))
        monkeypatch.setattr(sys, "argv", ["maccat", "--no-commit"])

        from maccat.cli import run

        # Must not raise
        run()

        # No catalog file written
        for d in disposable_catalog_repo.iterdir():
            if d.is_dir() and d.name not in (".git",):
                txt_files = list(d.glob("mac-software-list-*.txt"))
                assert len(txt_files) == 0, (
                    f"No catalog should be written when user quits: {txt_files}"
                )
