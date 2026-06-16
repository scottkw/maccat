"""Tests for maccat.collectors.homebrew and maccat.collectors.mas.

Behavioral spec: brew list --versions versioned output (VER-01 / VER-02).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from maccat.collectors.homebrew import HomebrewCollector
from maccat.collectors.mas import MasCollector

# ---------------------------------------------------------------------------
# HomebrewCollector
# ---------------------------------------------------------------------------


class TestHomebrewCollector:
    def test_homebrew_collect_formulae_and_casks(self) -> None:
        """brew available — formulae+cask lines emitted as 'name (version)', raw=True."""
        mock_formula = MagicMock()
        mock_formula.returncode = 0
        mock_formula.stdout = "git 2.44.0\nnode 18.0.0\n"

        mock_cask = MagicMock()
        mock_cask.returncode = 0
        mock_cask.stdout = "docker 4.30.0\n"

        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch("subprocess.run", side_effect=[mock_formula, mock_cask]),
        ):
            result = HomebrewCollector().collect()

        section = result.sections[0]
        assert section.items == ["git (2.44.0)", "node (18.0.0)", "docker (4.30.0)"]
        assert section.raw is True

    def test_homebrew_absent_returns_fallback(self) -> None:
        """brew not found — returns exact zsh fallback message, raw=True (CAT-06)."""
        with patch("shutil.which", return_value=None):
            result = HomebrewCollector().collect()

        section = result.sections[0]
        assert section.items == ["Homebrew is not installed."]
        assert section.raw is True

    def test_homebrew_nonzero_exit_returns_empty_lines(self) -> None:
        """brew returns non-zero exit — _run returns []; section items is empty list, raw=True."""
        mock_fail = MagicMock()
        mock_fail.returncode = 1
        mock_fail.stdout = ""

        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch("subprocess.run", return_value=mock_fail),
        ):
            result = HomebrewCollector().collect()

        section = result.sections[0]
        assert section.items == []
        assert section.raw is True

    def test_homebrew_section_title(self) -> None:
        """Section title must be exactly 'Homebrew Packages'."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = ""

        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = HomebrewCollector().collect()

        assert result.sections[0].title == "Homebrew Packages"


class TestHomebrewVersionParsing:
    """Unit tests for HomebrewCollector._parse_brew_versions_line (VER-01/VER-02)."""

    def test_single_version(self) -> None:
        """Single version token: 'git 2.44.0' → 'git (2.44.0)'."""
        collector = HomebrewCollector()
        assert collector._parse_brew_versions_line("git 2.44.0") == "git (2.44.0)"

    def test_multi_version(self) -> None:
        """Multiple version tokens: 'python@3.11 3.11.1 3.11.2' → 'python@3.11 (3.11.1 3.11.2)'."""
        collector = HomebrewCollector()
        result = collector._parse_brew_versions_line("python@3.11 3.11.1 3.11.2")
        assert result == "python@3.11 (3.11.1 3.11.2)"

    def test_name_only_degrades_gracefully(self) -> None:
        """Name-only line (no version token) → bare name, no crash."""
        collector = HomebrewCollector()
        assert collector._parse_brew_versions_line("git") == "git"

    def test_empty_line_returns_empty(self) -> None:
        """Empty string → empty string (filtered out upstream)."""
        collector = HomebrewCollector()
        assert collector._parse_brew_versions_line("") == ""

    def test_determinism(self) -> None:
        """Two calls with identical input return identical output."""
        collector = HomebrewCollector()
        first = collector._parse_brew_versions_line("node 18.0.0")
        second = collector._parse_brew_versions_line("node 18.0.0")
        assert first == second == "node (18.0.0)"


# ---------------------------------------------------------------------------
# MasCollector
# ---------------------------------------------------------------------------


class TestMasCollector:
    def test_mas_collect_parses_output(self) -> None:
        """mas available — output parsed, id preserved in [id] bracket, raw=True."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "1234567890  Safari (15.0)\n9876543210  Xcode (14.0)"

        with (
            patch("shutil.which", return_value="/usr/local/bin/mas"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = MasCollector().collect()

        section = result.sections[0]
        assert section.items == ["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]
        assert section.raw is True

    def test_mas_absent_returns_two_line_fallback(self) -> None:
        """mas not found — returns exact two-line zsh fallback, raw=True (CAT-06)."""
        with patch("shutil.which", return_value=None):
            result = MasCollector().collect()

        section = result.sections[0]
        assert section.items == [
            "mas (Mac App Store CLI) is not installed.",
            "Install it with Homebrew: brew install mas",
        ]
        assert section.raw is True

    def test_mas_nonzero_exit_returns_error_message(self) -> None:
        """mas returns non-zero exit — returns exact error message, raw=True."""
        mock_r = MagicMock()
        mock_r.returncode = 1
        mock_r.stdout = ""

        with (
            patch("shutil.which", return_value="/usr/local/bin/mas"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = MasCollector().collect()

        section = result.sections[0]
        assert section.items == ["Could not retrieve App Store list."]
        assert section.raw is True

    def test_mas_section_title(self) -> None:
        """Section title must be exactly 'App Store Applications'."""
        with patch("shutil.which", return_value=None):
            result = MasCollector().collect()

        assert result.sections[0].title == "App Store Applications"

    def test_mas_two_field_line_degrades_to_name_id(self) -> None:
        """2-field line ('123  OnlyTwo') — no version; emits 'OnlyTwo [123]' via emit_item."""
        mas = MasCollector()
        result = mas._parse_mas_output("123  OnlyTwo\n456  Safari (15.0)")
        assert result == ["OnlyTwo [123]", "Safari (15.0) [456]"]

    def test_mas_single_field_line_skipped(self) -> None:
        """A 1-field line has no $2; awk would print a leading-space blank, but our
        parser only emits for >=2 fields (no AppName to report). One field → skipped."""
        mas = MasCollector()
        result = mas._parse_mas_output("123\n")
        assert result == []
