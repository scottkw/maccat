"""Tests for maccat.collectors.homebrew and maccat.collectors.mas.

Behavioral spec: update-list.sh lines 2233-2260.
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
        """brew available — formulae lines followed by cask lines, raw=True."""
        mock_formula = MagicMock()
        mock_formula.returncode = 0
        mock_formula.stdout = "git\nnode\n"

        mock_cask = MagicMock()
        mock_cask.returncode = 0
        mock_cask.stdout = "docker\n"

        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch("subprocess.run", side_effect=[mock_formula, mock_cask]),
        ):
            result = HomebrewCollector().collect()

        section = result.sections[0]
        assert section.items == ["git", "node", "docker"]
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


# ---------------------------------------------------------------------------
# MasCollector
# ---------------------------------------------------------------------------


class TestMasCollector:
    def test_mas_collect_parses_output(self) -> None:
        """mas available — output parsed with awk column 2+3 equivalence, raw=True."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "1234567890  Safari (15.0)\n9876543210  Xcode (14.0)"

        with (
            patch("shutil.which", return_value="/usr/local/bin/mas"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = MasCollector().collect()

        section = result.sections[0]
        assert section.items == ["Safari (15.0)", "Xcode (14.0)"]
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

    def test_mas_two_field_line_emits_trailing_space(self) -> None:
        """awk '{print $2, $3}' emits a row for every line, with empty $3 → trailing space.

        WR-02 byte-parity fix: a 2-field line ("123  OnlyTwo") must produce "OnlyTwo "
        (trailing space, empty $3), NOT be dropped. Verified against real BSD awk:
        `printf '456 OnlyTwo\\n' | awk '{print $2, $3}'` → "OnlyTwo " (trailing space).
        """
        mas = MasCollector()
        output = "123  OnlyTwo\n456  Safari (15.0)\n789  ShortLine"
        result = mas._parse_mas_output(output)
        # "OnlyTwo" — 2 fields → emit "$2 " with empty $3 (trailing space)
        # "Safari (15.0)" — 3 fields → "Safari (15.0)"
        # "ShortLine" — 2 fields → "ShortLine " (trailing space)
        assert result == ["OnlyTwo ", "Safari (15.0)", "ShortLine "]

    def test_mas_single_field_line_skipped(self) -> None:
        """A 1-field line has no $2; awk would print a leading-space blank, but our
        parser only emits for >=2 fields (no AppName to report). One field → skipped."""
        mas = MasCollector()
        result = mas._parse_mas_output("123\n")
        assert result == []
