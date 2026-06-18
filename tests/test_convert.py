"""Tests for the convert subcommand — Phase 32 plan 02.

Covers:
  Test 1  (happy path via CLI)      maccat convert --from ... writes .md, removes .txt, exits 0
  Test 2  (--no-commit)             run_convert writes .md, removes .txt, no git_commit_convert call
  Test 3  (missing file)            run_convert exits non-zero when --from path does not exist
  Test 4  (bad filename)            run_convert exits non-zero when filename doesn't match regex
  Test 5  (no-clobber)              run_convert exits non-zero when .md already exists; .txt stays
  Test 6  (unreadable file)         run_convert exits non-zero when os.R_OK fails; skipif root
  Test 7  (git staging)             git_commit_convert called with correct (repo, md, txt) args
  Test 8  (round-trip full-chain)   convert .txt -> parse_markdown_catalog: parses cleanly,
                                    single H1, no spurious ## heading, expected section titles
  Test 9  (degraded/empty section)  section with only NONE_FOUND_SENTINEL renders as '(none found)'
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Module-level fixture content
# ---------------------------------------------------------------------------

_MINIMAL_TXT_CATALOG = (
    "Installed Mac Software List\n"
    "------------------------------------\n"
    "\n"
    "Homebrew Packages\n"
    "------------------------------------\n"
    "wget (1.21.3)\n"
    "git (2.44.0)\n"
    "\n"
    "App Store Applications\n"
    "------------------------------------\n"
    "Final Cut Pro (10.7.1) [424389933]\n"
    "\n"
    "Setapp Applications\n"
    "------------------------------------\n"
    "  (none found)\n"
)

# ---------------------------------------------------------------------------
# Helper: build a minimal Namespace the way argparse would for run_convert
# ---------------------------------------------------------------------------


def _make_convert_args(
    from_path: str | None = None,
    no_commit: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(from_path=from_path, no_commit=no_commit)


# ---------------------------------------------------------------------------
# TestConvertHappyPath — CLI integration + file ops happy paths
# ---------------------------------------------------------------------------


class TestConvertHappyPath:
    """Integration and happy-path unit tests for the convert subcommand."""

    @pytest.fixture()
    def fixture_txt_catalog(self, tmp_path: Path) -> Path:
        """Minimal valid legacy .txt catalog in tmp_path.

        Filename follows mac-software-list-[machine]-timestamp.txt convention
        so _TXT_FILENAME_RE can parse it.
        """
        catalog = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        catalog.write_text(_MINIMAL_TXT_CATALOG, encoding="utf-8")
        return catalog

    # ------------------------------------------------------------------
    # Test 1: happy path via CLI
    # ------------------------------------------------------------------

    def test_convert_writes_md_removes_txt_via_cli(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        fixture_txt_catalog: Path,
    ) -> None:
        """maccat convert --from ... writes .md, removes .txt, exits 0 via CLI."""
        monkeypatch.setattr(
            sys,
            "argv",
            ["maccat", "convert", "--from", str(fixture_txt_catalog)],
        )
        # Patch git_commit_convert so no real git ops run
        monkeypatch.setattr("maccat.gitops.git_commit_convert", MagicMock())

        from maccat.cli import run

        run()  # must not raise SystemExit

        md = fixture_txt_catalog.with_suffix(".md")
        assert md.exists(), ".md must be written"
        assert not fixture_txt_catalog.exists(), ".txt must be removed"

    # ------------------------------------------------------------------
    # Test 2: --no-commit skips git_commit_convert
    # ------------------------------------------------------------------

    def test_no_commit_skips_git(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fixture_txt_catalog: Path,
    ) -> None:
        """run_convert with no_commit=True writes .md, removes .txt, does NOT call git."""
        mock_commit = MagicMock()
        monkeypatch.setattr("maccat.gitops.git_commit_convert", mock_commit)

        from maccat.convert import run_convert

        args = _make_convert_args(
            from_path=str(fixture_txt_catalog), no_commit=True
        )
        run_convert(args)

        md = fixture_txt_catalog.with_suffix(".md")
        assert md.exists(), ".md must be written"
        assert not fixture_txt_catalog.exists(), ".txt must be removed"
        mock_commit.assert_not_called()


# ---------------------------------------------------------------------------
# TestConvertErrorPaths — all non-zero exit cases
# ---------------------------------------------------------------------------


class TestConvertErrorPaths:
    """Tests for error paths that must exit non-zero."""

    @pytest.fixture()
    def fixture_txt_catalog(self, tmp_path: Path) -> Path:
        catalog = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        catalog.write_text(_MINIMAL_TXT_CATALOG, encoding="utf-8")
        return catalog

    # ------------------------------------------------------------------
    # Test 3: missing file exits non-zero
    # ------------------------------------------------------------------

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        """run_convert exits non-zero when --from path does not exist."""
        from maccat.convert import run_convert

        args = _make_convert_args(
            from_path=str(tmp_path / "nonexistent.txt")
        )
        with pytest.raises(SystemExit) as exc:
            run_convert(args)
        assert exc.value.code != 0

    # ------------------------------------------------------------------
    # Test 4: bad filename exits non-zero
    # ------------------------------------------------------------------

    def test_bad_filename_exits_nonzero(self, tmp_path: Path) -> None:
        """run_convert exits non-zero when filename doesn't match _TXT_FILENAME_RE."""
        from maccat.convert import run_convert

        bad = tmp_path / "badly-named-file.txt"
        bad.write_text("x", encoding="utf-8")
        args = _make_convert_args(from_path=str(bad))
        with pytest.raises(SystemExit) as exc:
            run_convert(args)
        assert exc.value.code != 0

    # ------------------------------------------------------------------
    # Test 5: no-clobber — target .md already exists
    # ------------------------------------------------------------------

    def test_no_clobber_exits_nonzero_and_txt_stays(
        self, fixture_txt_catalog: Path
    ) -> None:
        """run_convert exits non-zero when .md already exists; .txt is NOT removed."""
        from maccat.convert import run_convert

        # Pre-create the target .md
        md_path = fixture_txt_catalog.with_suffix(".md")
        md_path.write_text("already here\n", encoding="utf-8")
        original_md_content = md_path.read_text(encoding="utf-8")

        args = _make_convert_args(from_path=str(fixture_txt_catalog))
        with pytest.raises(SystemExit) as exc:
            run_convert(args)
        assert exc.value.code != 0

        # .txt must still exist (not touched on failure)
        assert fixture_txt_catalog.exists(), ".txt must still be present after no-clobber exit"
        # .md must be unchanged
        assert md_path.read_text(encoding="utf-8") == original_md_content

    # ------------------------------------------------------------------
    # Test 6: unreadable file exits non-zero (skipif root)
    # ------------------------------------------------------------------

    @pytest.mark.skipif(
        os.geteuid() == 0,
        reason="root bypasses file permission checks; 0o000 is still readable",
    )
    def test_unreadable_file_exits_nonzero(self, tmp_path: Path) -> None:
        """run_convert exits non-zero when file exists but os.R_OK fails."""
        from maccat.convert import run_convert

        f = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        f.write_text("x", encoding="utf-8")
        os.chmod(f, 0o000)
        try:
            args = _make_convert_args(from_path=str(f))
            with pytest.raises(SystemExit) as exc:
                run_convert(args)
            assert exc.value.code != 0
        finally:
            os.chmod(f, 0o644)

    def test_non_utf8_file_exits_nonzero(self, tmp_path: Path) -> None:
        """WR-01: a non-UTF-8 legacy .txt exits cleanly, not via raw traceback."""
        from maccat.convert import run_convert

        f = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        # 0xFF is never valid UTF-8 — read_text(encoding="utf-8") raises UnicodeDecodeError
        f.write_bytes(b"Homebrew Packages\n----\ngit (\xff)\n")
        args = _make_convert_args(from_path=str(f))
        with pytest.raises(SystemExit) as exc:
            run_convert(args)
        assert exc.value.code != 0
        assert "UTF-8" in str(exc.value.code)
        # The .txt must NOT be deleted on this abort path
        assert f.exists()

    def test_unlink_failure_exits_nonzero_after_md_written(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """WR-02: if unlink fails after a successful .md write, exit cleanly and keep the .md."""
        from maccat import convert as convert_mod

        f = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        f.write_text(
            "Homebrew Packages\n------------------------------------\ngit (2.44.0)\n",
            encoding="utf-8",
        )

        orig_unlink = Path.unlink

        def boom(self: Path, *a: object, **k: object) -> None:
            if self.suffix == ".txt":
                raise OSError("read-only filesystem")
            orig_unlink(self, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "unlink", boom)
        args = _make_convert_args(from_path=str(f), no_commit=True)
        with pytest.raises(SystemExit) as exc:
            convert_mod.run_convert(args)
        assert exc.value.code != 0
        # .md was written before the failed unlink — must still exist
        assert f.with_suffix(".md").exists()

    def test_rename_flag_rejected_for_convert(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """WR-03: --rename combined with the convert subcommand is rejected."""
        f = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        f.write_text(
            "Homebrew Packages\n------------------------------------\ngit (2.44.0)\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            sys, "argv", ["maccat", "--rename", "convert", "--from", str(f)]
        )
        from maccat.cli import run

        with pytest.raises(SystemExit) as exc:
            run()
        assert exc.value.code != 0
        # convert must NOT have run — .txt untouched, no .md produced
        assert f.exists()
        assert not f.with_suffix(".md").exists()


# ---------------------------------------------------------------------------
# TestConvertGitStaging — git_commit_convert called with correct args
# ---------------------------------------------------------------------------


class TestConvertGitStaging:
    """Tests that git_commit_convert is called with the correct three arguments."""

    # ------------------------------------------------------------------
    # Test 7: git staging called with (catalog_repo, md_path, txt_path)
    # ------------------------------------------------------------------

    def test_git_commit_convert_called_with_correct_args(
        self,
        monkeypatch: pytest.MonkeyPatch,
        git_repo: Path,
    ) -> None:
        """git_commit_convert is called once with (repo, md_path, txt_path).

        The .txt lives at <git_repo>/<computer>/filename so that
        txt_path.parent.parent == git_repo — the heuristic in run_convert.
        """
        from maccat.convert import run_convert

        # Place .txt inside git_repo/TestMac/ so relative_to succeeds
        computer_dir = git_repo / "TestMac"
        computer_dir.mkdir()
        txt_path = computer_dir / "mac-software-list-[TestMac]-20260101120000.txt"
        txt_path.write_text(_MINIMAL_TXT_CATALOG, encoding="utf-8")

        mock_commit = MagicMock()
        monkeypatch.setattr("maccat.gitops.git_commit_convert", mock_commit)

        args = _make_convert_args(from_path=str(txt_path), no_commit=False)
        run_convert(args)

        md_path = txt_path.with_suffix(".md")
        mock_commit.assert_called_once_with(git_repo, md_path, txt_path)


# ---------------------------------------------------------------------------
# TestConvertRoundTrip — full-chain: convert .txt -> parse_markdown_catalog
# ---------------------------------------------------------------------------


class TestConvertRoundTrip:
    """Full round-trip tests: convert a .txt fixture then verify the .md output."""

    @pytest.fixture()
    def fixture_txt_catalog(self, tmp_path: Path) -> Path:
        catalog = tmp_path / "mac-software-list-[TestMac]-20260101120000.txt"
        catalog.write_text(_MINIMAL_TXT_CATALOG, encoding="utf-8")
        return catalog

    # ------------------------------------------------------------------
    # Test 8: round-trip full-chain
    # ------------------------------------------------------------------

    def test_round_trip_convert_then_parse_markdown(
        self, fixture_txt_catalog: Path
    ) -> None:
        """Convert a .txt fixture, then parse the .md with parse_markdown_catalog.

        Asserts:
        - .md exists and .txt is gone
        - parse_markdown_catalog does not raise
        - produced .md has sections: Homebrew Packages, App Store Applications,
          Setapp Applications (NOT 'Installed Mac Software List' — header skipped)
        - exactly one '# Installed Mac Software List' H1 in the .md text
        - no '## Installed Mac Software List' spurious heading in the .md text
        """
        from maccat.convert import run_convert
        from maccat.reinstall.parser import parse_markdown_catalog

        args = _make_convert_args(
            from_path=str(fixture_txt_catalog), no_commit=True
        )
        run_convert(args)

        md_path = fixture_txt_catalog.with_suffix(".md")
        assert md_path.exists(), ".md must be written"
        assert not fixture_txt_catalog.exists(), ".txt must be removed"

        # Must parse without raising
        parsed = parse_markdown_catalog(md_path)

        # Section titles must match the non-header sections from the fixture
        section_titles = [s.title for s in parsed.sections]
        assert "Homebrew Packages" in section_titles
        assert "App Store Applications" in section_titles
        assert "Setapp Applications" in section_titles
        # The header section must NOT appear as a ParsedSection (bridge filters it)
        assert "Installed Mac Software List" not in section_titles

        # Exactly one H1 '# Installed Mac Software List' in .md text
        md_text = md_path.read_text(encoding="utf-8")
        assert md_text.count("# Installed Mac Software List") == 1, (
            "Expected exactly one '# Installed Mac Software List' H1 in .md"
        )
        # No spurious ## heading for the catalog title
        assert "## Installed Mac Software List" not in md_text, (
            "Spurious '## Installed Mac Software List' found in .md"
        )

    # ------------------------------------------------------------------
    # Test 9: degraded/empty section renders as '(none found)'
    # ------------------------------------------------------------------

    def test_empty_section_renders_none_found(self, tmp_path: Path) -> None:
        """Section containing only NONE_FOUND_SENTINEL renders as '(none found)' in .md."""
        from maccat.convert import run_convert
        from maccat.reinstall.parser import MD_NONE_FOUND, parse_markdown_catalog

        # .txt with a section that is empty (only sentinel)
        txt_content = (
            "Installed Mac Software List\n"
            "------------------------------------\n"
            "\n"
            "Setapp Applications\n"
            "------------------------------------\n"
            "  (none found)\n"
        )
        txt_path = tmp_path / "mac-software-list-[TestMac]-20260202120000.txt"
        txt_path.write_text(txt_content, encoding="utf-8")

        args = _make_convert_args(from_path=str(txt_path), no_commit=True)
        run_convert(args)

        md_path = txt_path.with_suffix(".md")
        assert md_path.exists()

        # parse_markdown_catalog must handle it cleanly
        parsed = parse_markdown_catalog(md_path)
        section_titles = [s.title for s in parsed.sections]
        assert "Setapp Applications" in section_titles

        # The .md text must contain the MD_NONE_FOUND sentinel for this section
        md_text = md_path.read_text(encoding="utf-8")
        assert MD_NONE_FOUND in md_text, (
            f"Expected '{MD_NONE_FOUND}' in .md for empty section"
        )
