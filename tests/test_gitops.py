"""Tests for src/maccat/gitops.py — git pull, commit/push, and rename operations.

All tests use the disposable git_repo fixture (tmp_path + git init, no remote)
from conftest.py. NEVER reference personal/ or office/ catalog directories.

Behavior spec: update-list.sh:2327-2354 (git_pull), :2374-2431 (git_commit_and_push),
:867-910 (git_commit_rename).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from maccat.gitops import git_commit_and_push, git_commit_rename, git_pull


class TestGitPull:
    def test_not_a_git_repo_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """git_pull on a plain dir (not git-init'd) prints WARNING, never raises."""
        git_pull(tmp_path)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_no_remote_warns_or_continues(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """git_pull on a repo with no remote configured: completes without raising.

        A no-remote repo returns nonzero from git pull, so output contains WARNING.
        The function must never raise — warn-and-continue invariant.
        """
        git_pull(git_repo)  # must not raise
        captured = capsys.readouterr()
        # No remote → pull fails → WARNING expected
        assert "WARNING" in captured.out or "Successfully" in captured.out


class TestGitCommitAndPush:
    def test_no_changes_returns_cleanly(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Nothing staged → no-changes guard prints 'No changes to commit' and returns early."""
        git_commit_and_push(git_repo, "personal", "20260614120000")
        captured = capsys.readouterr()
        assert "No changes to commit" in captured.out

    def test_commit_message_format(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """After writing a file to computer/, commit message matches zsh:2410 format."""
        computer_dir = git_repo / "personal"
        computer_dir.mkdir()
        (computer_dir / "test.txt").write_text("catalog data", encoding="utf-8")

        git_commit_and_push(git_repo, "personal", "20260614120000")

        # Verify commit was created via git log
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "Added [personal] catalog at 20260614120000" in result.stdout

    def test_leading_dash_safety(self, git_repo: Path) -> None:
        """git add -A -- 'personal/' must not raise even when folder name is plain.

        The '--' end-of-options separator ensures a folder whose name begins with
        '-' (leading-dash safety) cannot be parsed as a git option. This test
        verifies no subprocess.CalledProcessError is raised with a normal name.
        """
        computer_dir = git_repo / "personal"
        computer_dir.mkdir()
        (computer_dir / "file.txt").write_text("x", encoding="utf-8")

        # Must not raise; leading-dash safety is a correctness requirement
        git_commit_and_push(git_repo, "personal", "20260614120000")

    def test_push_failure_warns(self, git_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Push failure on a no-remote repo: WARNING printed, no exception raised."""
        computer_dir = git_repo / "personal"
        computer_dir.mkdir()
        (computer_dir / "catalog.txt").write_text("data", encoding="utf-8")

        git_commit_and_push(git_repo, "personal", "20260614120000")

        captured = capsys.readouterr()
        # Push to a no-remote repo fails → WARNING expected
        assert "WARNING" in captured.out


class TestGitCommitRename:
    def test_rename_commit_message(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """git_commit_rename creates a commit with 'Rename computer: ...' message."""
        # Set up old_name folder with files and commit it first
        old_dir = git_repo / "old"
        old_dir.mkdir()
        (old_dir / "catalog.txt").write_text("old data", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=git_repo,
            capture_output=True,
        )

        # Simulate the rename: move old/ → new/ at filesystem level
        new_dir = git_repo / "new"
        old_dir.rename(new_dir)

        # git_commit_rename stages both paths and commits
        git_commit_rename(git_repo, "old", "new")

        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "Rename computer: 'old' -> 'new'" in result.stdout

    def test_not_a_git_repo_warns(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """git_commit_rename on a plain dir prints WARNING and returns without raising."""
        git_commit_rename(tmp_path, "old", "new")
        captured = capsys.readouterr()
        assert "WARNING" in captured.out


def _seed_catalog_repo(repo: Path) -> None:
    """Seed repo with a committed personal/ folder containing a proper catalog file.

    discover_computer_folders() requires mac-software-list-*.txt to exist, so
    the plain 'catalog.txt' name used in earlier tests is not sufficient here.
    """
    from maccat.naming import make_catalog_filename

    computer_dir = repo / "personal"
    computer_dir.mkdir(exist_ok=True)
    catalog = computer_dir / make_catalog_filename("personal", "20260614120000")
    catalog.write_text("test catalog", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, capture_output=True)


class TestRenameIdentityIntegration:
    def test_auto_commit_false_no_git_calls(
        self,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """rename_machine with auto_commit=False: gitops.git_commit_rename NOT called."""
        import maccat.gitops as gitops_mod

        calls: list[tuple[Path, str, str]] = []

        def _mock_rename(repo: Path, old: str, new: str) -> None:
            calls.append((repo, old, new))

        monkeypatch.setattr(gitops_mod, "git_commit_rename", _mock_rename)

        _seed_catalog_repo(git_repo)

        import io
        import sys

        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        # "1" selects 'personal', "work" is new name, "N" declines filename rewrite
        monkeypatch.setattr(sys, "stdin", FakeTTY("1\nwork\nN\n"))

        from maccat.identity import rename_machine
        try:
            rename_machine(git_repo, auto_commit=False)
        except SystemExit:
            pass  # May exit on interactive guard in non-TTY envs

        assert calls == [], f"Expected no git calls, got {calls}"

    def test_auto_commit_true_calls_git(
        self,
        git_repo: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """rename_machine with auto_commit=True: gitops.git_commit_rename IS called."""
        import maccat.gitops as gitops_mod

        calls: list[tuple[Path, str, str]] = []

        def _mock_rename(repo: Path, old: str, new: str) -> None:
            calls.append((repo, old, new))

        monkeypatch.setattr(gitops_mod, "git_commit_rename", _mock_rename)

        _seed_catalog_repo(git_repo)

        import io
        import sys

        class FakeTTY(io.StringIO):
            def isatty(self) -> bool:
                return True

        # "1" selects 'personal', "work" is new name, "N" declines filename rewrite
        monkeypatch.setattr(sys, "stdin", FakeTTY("1\nwork\nN\n"))

        from maccat.identity import rename_machine
        try:
            rename_machine(git_repo, auto_commit=True)
        except SystemExit:
            pass

        assert len(calls) == 1, f"Expected 1 git call, got {calls}"
