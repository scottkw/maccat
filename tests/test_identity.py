"""Tests for src/maccat/identity.py.

Covers: validate_computer_name, validate_computer_name_quiet,
resolve_computer_selection, discover_computer_folders,
select_computer (non-TTY, EOF, saved-folder Enter),
rename_machine (refuse-clobber, same-name, folder-not-found),
upsert_machine_label (creates with header, appends, updates, preserves
comments/blank lines, atomic tmp file gone after write).
"""
from __future__ import annotations

import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from maccat.identity import (
    _iter_tsv_entries,
    discover_computer_folders,
    rename_machine,
    resolve_computer_selection,
    select_computer,
    upsert_machine_label,
    validate_computer_name,
    validate_computer_name_quiet,
)
from maccat.naming import make_catalog_filename

# ---------------------------------------------------------------------------
# TestValidateComputerName
# ---------------------------------------------------------------------------


class TestValidateComputerName:
    def test_valid_name_no_raise(self) -> None:
        validate_computer_name("My Laptop")  # should not raise

    def test_empty_raises_systemexit(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("")

    def test_leading_whitespace_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name(" Laptop")

    def test_trailing_whitespace_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("Laptop ")

    def test_slash_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("bad/name")

    def test_open_bracket_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("bad[name")

    def test_close_bracket_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("bad]name")

    def test_tab_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("bad\tname")

    def test_newline_raises(self) -> None:
        with pytest.raises(SystemExit):
            validate_computer_name("bad\nname")

    def test_valid_name_quiet_no_error(self) -> None:
        assert validate_computer_name_quiet("GoodName") is None

    def test_empty_quiet_returns_string(self) -> None:
        result = validate_computer_name_quiet("")
        assert result is not None
        assert "empty" in result.lower()

    def test_slash_quiet_returns_string(self) -> None:
        result = validate_computer_name_quiet("bad/name")
        assert result is not None
        assert "/" in result

    def test_tab_quiet_returns_string(self) -> None:
        result = validate_computer_name_quiet("bad\tname")
        assert result is not None
        assert "tab" in result.lower()


# ---------------------------------------------------------------------------
# TestResolveComputerSelection  (SC3 — pure, no argparse, no TTY needed)
# ---------------------------------------------------------------------------


class TestResolveComputerSelection:
    def test_none_returns_none(self) -> None:
        result = resolve_computer_selection(computer=None)
        assert result is None

    def test_computer_resolves(self) -> None:
        result = resolve_computer_selection(computer="Laptop")
        assert result == "Laptop"

    def test_invalid_computer_name_raises(self) -> None:
        # validate_computer_name rejects slashes
        with pytest.raises(SystemExit):
            resolve_computer_selection(computer="bad/name")

    def test_empty_string_computer_treated_as_none(self) -> None:
        # Empty string is treated as "not set" — same as None
        result = resolve_computer_selection(computer="")
        assert result is None

    def test_valid_name_returned_unchanged(self) -> None:
        result = resolve_computer_selection(computer="WorkLaptop")
        assert result == "WorkLaptop"

    def test_name_with_spaces_is_valid(self) -> None:
        result = resolve_computer_selection(computer="My Mac")
        assert result == "My Mac"

    def test_none_returns_none_for_interactive_fallback(self) -> None:
        result = resolve_computer_selection(computer=None)
        assert result is None


# ---------------------------------------------------------------------------
# TestSelectComputer
# ---------------------------------------------------------------------------


class TestSelectComputer:
    def test_non_tty_exits_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stdin not a TTY → immediate SystemExit with actionable message. No hang."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit) as exc_info:
            select_computer(tmp_path)
        msg = str(exc_info.value)
        assert "TTY" in msg or "tty" in msg.lower() or "--computer" in msg

    def test_ctrl_d_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EOF (Ctrl-D) on first input → returns None, no traceback, no infinite loop."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with patch("builtins.input", side_effect=EOFError):
            result = select_computer(tmp_path)
        assert result is None

    def test_enter_with_saved_folder_returns_saved(
        self, catalog_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty input when saved_folder matches hostname → returns saved_folder."""
        import sys

        current_host = socket.gethostname()
        # Write the TSV so this host maps to "personal"
        map_file = catalog_repo / "machine-labels.tsv"
        map_file.write_text(
            "# Mac Software List — hostname to computer-folder map\n"
            f"{current_host}\tpersonal\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # First input = "" (Enter → saved default), second input = unused
        with patch("builtins.input", side_effect=["", EOFError]):
            result = select_computer(catalog_repo)
        assert result == "personal"

    def test_flag_path_creates_folder_and_returns_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """computer_name kwarg bypasses menu entirely: mkdir, upsert, return name."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)  # TTY guard not hit in flag path
        result = select_computer(tmp_path, computer_name="WorkMachine")
        assert result == "WorkMachine"
        assert (tmp_path / "WorkMachine").is_dir()
        # TSV should have an entry for this host
        map_file = tmp_path / "machine-labels.tsv"
        assert map_file.exists()
        content = map_file.read_text(encoding="utf-8")
        assert "WorkMachine" in content

    def test_quit_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Selecting Quit option → returns None, no SystemExit."""
        import sys

        # Create one folder so there's a menu entry
        computer_dir = tmp_path / "personal"
        computer_dir.mkdir()
        (computer_dir / make_catalog_filename("personal", "20260614120000")).write_text(
            "x", encoding="utf-8"
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # quit_idx = len(computers) + 2 = 1 + 2 = 3
        with patch("builtins.input", return_value="3"):
            result = select_computer(tmp_path)
        assert result is None

    def test_q_quits(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Entering 'q' → quit, returns None."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # No folders — menu has only Create new (1) and Quit (2)
        with patch("builtins.input", return_value="q"):
            result = select_computer(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# TestRenameMachine
# ---------------------------------------------------------------------------


class TestRenameMachine:
    def test_refuse_clobber_exits_nonzero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Renaming to an existing folder → SystemExit; both folders still intact."""
        import sys

        old_dir = tmp_path / "OldName"
        old_dir.mkdir()
        (old_dir / make_catalog_filename("OldName", "20260614120000")).write_text(
            "x", encoding="utf-8"
        )
        new_dir = tmp_path / "NewName"
        new_dir.mkdir()  # Already exists → refuse-clobber

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # Menu: 1) OldName, 2) NewName, 3) Quit → pick 1, then enter "NewName"
        with patch("builtins.input", side_effect=["1", "NewName"]):
            with pytest.raises(SystemExit):
                rename_machine(tmp_path)
        # Both folders must still exist
        assert old_dir.is_dir()
        assert new_dir.is_dir()

    def test_noop_on_same_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """new == old → WARNING printed, function returns (no SystemExit)."""
        import sys

        old_dir = tmp_path / "MyComputer"
        old_dir.mkdir()
        (old_dir / make_catalog_filename("MyComputer", "20260614120000")).write_text(
            "x", encoding="utf-8"
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # Pick 1 → "MyComputer" (same as old_name)
        with patch("builtins.input", side_effect=["1", "MyComputer"]):
            result = rename_machine(tmp_path)
        assert result is None
        assert old_dir.is_dir()  # folder unchanged

    def test_folder_not_found_warns_and_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """old_name exists in TSV but not on disk → WARNING, returns without SystemExit."""
        import sys

        # TSV has an entry but the folder doesn't exist on disk
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# header\n"
            "ghost-host\tGhostComputer\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # Menu: 1) GhostComputer, 2) Quit → pick 1 → enter "AnotherName"
        with patch("builtins.input", side_effect=["1", "AnotherName"]):
            result = rename_machine(tmp_path)
        assert result is None

    def test_non_tty_exits_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stdin not a TTY → immediate SystemExit (rename requires interactive terminal)."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with pytest.raises(SystemExit) as exc_info:
            rename_machine(tmp_path)
        assert "TTY" in str(exc_info.value) or "tty" in str(exc_info.value).lower()

    def test_out_of_range_numeric_choice_reprompts_with_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Out-of-range numeric choice (e.g. '0') prints the invalid-choice error
        and re-prompts; a subsequent valid choice then proceeds.

        Regression for WR-01 (iteration 2): the old loop silently swallowed
        out-of-range numeric input instead of printing the zsh-parity error
        ``ERROR: Invalid choice '0'. Please enter 1-N.``.
        """
        import sys

        old_dir = tmp_path / "OnlyComputer"
        old_dir.mkdir()
        (old_dir / make_catalog_filename("OnlyComputer", "20260614120000")).write_text(
            "x", encoding="utf-8"
        )
        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # Menu: 1) OnlyComputer, 2) Quit → quit_idx == 2.
        # First "0" is out of range (must print error + re-prompt), then "3" is
        # also out of range (> quit_idx, another error + re-prompt), then "1"
        # is accepted → name prompt → "OnlyComputer" (no-op same-name guard).
        with patch("builtins.input", side_effect=["0", "3", "1", "OnlyComputer"]):
            result = rename_machine(tmp_path)

        out = capsys.readouterr().out
        assert "ERROR: Invalid choice '0'. Please enter 1-2." in out
        assert "ERROR: Invalid choice '3'. Please enter 1-2." in out
        # The valid choice proceeded into the rename flow (same-name no-op here)
        assert result is None
        assert old_dir.is_dir()

    def test_successful_rename(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Happy path: folder moves, filename rewritten, TSV updated."""
        import sys

        old_dir = tmp_path / "OldMachine"
        old_dir.mkdir()
        old_file = old_dir / make_catalog_filename("OldMachine", "20260614120000")
        old_file.write_text("catalog", encoding="utf-8")

        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# header\n"
            "some-host\tOldMachine\n",
            encoding="utf-8",
        )

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        # Pick 1 (OldMachine) → "NewMachine" → "y" (rewrite filenames)
        with patch("builtins.input", side_effect=["1", "NewMachine", "y"]):
            rename_machine(tmp_path)

        new_dir = tmp_path / "NewMachine"
        assert new_dir.is_dir()
        assert not (tmp_path / "OldMachine").exists()
        # Filename should be rewritten
        new_file = new_dir / make_catalog_filename("NewMachine", "20260614120000")
        assert new_file.exists()
        # TSV updated
        content = map_file.read_text(encoding="utf-8")
        assert "NewMachine" in content
        assert "OldMachine" not in content or content.count("OldMachine") == 0


# ---------------------------------------------------------------------------
# TestUpsertMachineLabel
# ---------------------------------------------------------------------------


class TestUpsertMachineLabel:
    def test_creates_file_with_header_if_absent(self, tmp_path: Path) -> None:
        upsert_machine_label(tmp_path, "personal")
        map_file = tmp_path / "machine-labels.tsv"
        assert map_file.exists()
        content = map_file.read_text(encoding="utf-8")
        assert content.startswith("#")
        assert "hostname" in content.lower() or "format" in content.lower()

    def test_appends_new_host(self, tmp_path: Path) -> None:
        upsert_machine_label(tmp_path, "personal")
        map_file = tmp_path / "machine-labels.tsv"
        content = map_file.read_text(encoding="utf-8")
        hostname = socket.gethostname()
        assert hostname in content
        assert "personal" in content

    def test_updates_existing_host(self, tmp_path: Path) -> None:
        upsert_machine_label(tmp_path, "personal")
        upsert_machine_label(tmp_path, "office")
        map_file = tmp_path / "machine-labels.tsv"
        content = map_file.read_text(encoding="utf-8")
        hostname = socket.gethostname()
        # Should appear exactly once
        lines = [
            line for line in content.splitlines() if line.startswith(hostname + "\t")
        ]
        assert len(lines) == 1
        assert lines[0].endswith("office")

    def test_preserves_comments_and_blank_lines(self, tmp_path: Path) -> None:
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# This is a comment\n"
            "\n"
            "other-host\tother-folder\n",
            encoding="utf-8",
        )
        upsert_machine_label(tmp_path, "personal")
        content = map_file.read_text(encoding="utf-8")
        assert "# This is a comment" in content
        # The blank line should be preserved (at least one blank line)
        assert "\n\n" in content or content.count("\n") >= 3
        assert "other-host\tother-folder" in content

    def test_atomic_write_tmp_gone_after(self, tmp_path: Path) -> None:
        upsert_machine_label(tmp_path, "personal")
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_no_separate_header_write_on_creation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CR-01: creating the TSV from scratch must be ONE atomic write.

        The old code wrote the header with write_text and then read it back —
        a non-atomic header write plus a TOCTOU read-after-write. Assert that
        Path.write_text is never called during creation (the only writer is the
        atomic mkstemp+rename helper).
        """
        import maccat.identity as identity

        original_write_text = Path.write_text
        calls: list[str] = []

        def tracking_write_text(self: Path, *args: object, **kwargs: object) -> int:
            calls.append(self.name)
            return original_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "write_text", tracking_write_text)
        identity.upsert_machine_label(tmp_path, "personal")

        assert "machine-labels.tsv" not in calls, (
            "machine-labels.tsv must not be created via a separate write_text — "
            "the full file (header + entries) is built once and renamed atomically"
        )
        # File still correct
        content = (tmp_path / "machine-labels.tsv").read_text(encoding="utf-8")
        assert content.startswith("#")
        assert socket.gethostname() in content

    def test_atomic_write_cleans_tmp_on_rename_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CR-01: if the final rename fails, the temp file must be removed (no
        stray .tmp left behind) and the original map_file must be untouched.

        Simulates a partial write by forcing Path.rename to raise mid-operation.
        """
        # Pre-existing valid map file
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# header\nother-host\tother-folder\n", encoding="utf-8"
        )
        original = map_file.read_text(encoding="utf-8")

        def boom(self: Path, *args: object, **kwargs: object) -> None:
            raise OSError("simulated rename failure")

        monkeypatch.setattr(Path, "rename", boom)
        with pytest.raises(OSError):
            upsert_machine_label(tmp_path, "personal")

        # No stray temp file
        assert list(tmp_path.glob("*.tmp")) == [], "temp file must be cleaned up on failure"
        # Original file untouched (atomic guarantee)
        assert map_file.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# TestIterTsvEntries  (WR-03 — single shared TSV reader)
# ---------------------------------------------------------------------------


class TestIterTsvEntries:
    def test_skips_comments_blanks_and_no_tab(self, tmp_path: Path) -> None:
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# a comment\n"
            "\n"
            "no-tab-line\n"
            "host-a\tfolder-a\n"
            "host-b\tfolder-b\n",
            encoding="utf-8",
        )
        assert _iter_tsv_entries(map_file) == [
            ("host-a", "folder-a"),
            ("host-b", "folder-b"),
        ]

    def test_skips_empty_host_or_label(self, tmp_path: Path) -> None:
        """zsh parity (update-list.sh:376): rows with an empty host OR label column skip."""
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "\tfolder-only\n"      # empty host
            "host-only\t\n"        # empty label
            "good-host\tgood\n",
            encoding="utf-8",
        )
        assert _iter_tsv_entries(map_file) == [("good-host", "good")]

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert _iter_tsv_entries(tmp_path / "does-not-exist.tsv") == []

    def test_discover_uses_shared_parser_skips_empty_label(self, tmp_path: Path) -> None:
        """discover_computer_folders must drop empty-label TSV rows (via _iter_tsv_entries)."""
        map_file = tmp_path / "machine-labels.tsv"
        map_file.write_text(
            "# header\n"
            "host-x\t\n"           # empty label — must NOT become a folder
            "host-y\tRealFolder\n",
            encoding="utf-8",
        )
        assert discover_computer_folders(tmp_path) == ["RealFolder"]


# ---------------------------------------------------------------------------
# TestSelectComputerEofMessage  (WR-02)
# ---------------------------------------------------------------------------


class TestSelectComputerEofMessage:
    def test_eof_prints_no_catalog_written(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """WR-02: EOF on the main menu routes through Quit → prints
        'No catalog written.' (zsh parity) and returns None."""
        import sys

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
        with patch("builtins.input", side_effect=EOFError):
            result = select_computer(tmp_path)
        assert result is None
        out = capsys.readouterr().out
        assert "No catalog written." in out, (
            "EOF must print 'No catalog written.' like the explicit Quit branch"
        )


# ---------------------------------------------------------------------------
# TestRenameMachineFolderMoveGuard  (WR-04)
# ---------------------------------------------------------------------------


class TestRenameMachineFolderMoveGuard:
    def test_rename_oserror_exits_with_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WR-04: an OSError from the folder move (e.g. EXDEV) must raise a clean
        SystemExit with an actionable message, not surface a traceback."""
        import sys

        old_dir = tmp_path / "OldMachine"
        old_dir.mkdir()
        (old_dir / make_catalog_filename("OldMachine", "20260614120000")).write_text(
            "catalog", encoding="utf-8"
        )

        monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

        real_rename = Path.rename

        def boom(self: Path, target: object, *args: object, **kwargs: object) -> Path:
            # Only the folder move (old_dir → new_dir) should explode; let any
            # other rename (none expected before the move) pass through.
            if self.name == "OldMachine":
                raise OSError("Invalid cross-device link")
            return real_rename(self, target)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "rename", boom)
        with patch("builtins.input", side_effect=["1", "NewMachine"]):
            with pytest.raises(SystemExit) as exc_info:
                rename_machine(tmp_path)

        msg = str(exc_info.value)
        assert "Could not rename folder" in msg
        assert "Nothing renamed" in msg
        # Old folder still present, new folder not created
        assert old_dir.is_dir(), "folder must remain on a failed move"
        assert not (tmp_path / "NewMachine").exists()
