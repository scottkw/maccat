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


def _brew_mocks(
    formulae: str, leaves: str, casks: str, leaves_rc: int = 0
) -> list[MagicMock]:
    """Three subprocess.run results in collect()'s fixed call order.

    Order: ``brew list --formula --versions``, ``brew leaves``,
    ``brew list --cask --versions``.
    """
    mocks = []
    for stdout, returncode in ((formulae, 0), (leaves, leaves_rc), (casks, 0)):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = stdout
        mocks.append(mock)
    return mocks


class TestHomebrewCollector:
    def test_homebrew_collect_formulae_and_casks(self) -> None:
        """brew available — formulae+cask lines emitted as 'name (version)', raw=True."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch(
                "subprocess.run",
                side_effect=_brew_mocks(
                    "git 2.44.0\nnode 18.0.0\n", "git\nnode\n", "docker 4.30.0\n"
                ),
            ),
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


class TestHomebrewLeavesFilter:
    """Formulae are intersected with ``brew leaves`` (top-level only); casks are not."""

    def _collect(
        self, formulae: str, leaves: str, casks: str, leaves_rc: int = 0
    ) -> list[str]:
        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch(
                "subprocess.run",
                side_effect=_brew_mocks(formulae, leaves, casks, leaves_rc),
            ),
        ):
            result = HomebrewCollector().collect()
        section = result.sections[0]
        assert section.raw is True
        return section.items

    def test_dependency_formulae_are_dropped(self) -> None:
        """A formula absent from ``brew leaves`` (libgit2) is excluded."""
        items = self._collect(
            "git 2.44.0\nnode 18.0.0\nlibgit2 1.7.2\n",
            "git\nnode\n",
            "docker 4.30.0\n",
        )
        assert items == ["git (2.44.0)", "node (18.0.0)", "docker (4.30.0)"]

    def test_multi_version_leaf_keeps_every_version(self) -> None:
        """Filtering does not disturb the multi-version 'name (v1 v2)' shape (VER-02)."""
        items = self._collect("python@3.11 3.11.1 3.11.2\n", "python@3.11\n", "")
        assert items == ["python@3.11 (3.11.1 3.11.2)"]

    def test_order_follows_brew_list_not_brew_leaves(self) -> None:
        """Output order is ``brew list --formula --versions`` order (VER-06)."""
        items = self._collect("aaa 1.0\nbbb 2.0\nccc 3.0\n", "ccc\nbbb\naaa\n", "")
        assert items == ["aaa (1.0)", "bbb (2.0)", "ccc (3.0)"]

    def test_casks_are_never_filtered_by_the_leaf_set(self) -> None:
        """``brew leaves`` covers formulae only — casks pass through untouched."""
        items = self._collect("", "", "docker 4.30.0\niterm2 3.5.0\n")
        assert items == ["docker (4.30.0)", "iterm2 (3.5.0)"]

    def test_subprocess_call_sequence_contract(self) -> None:
        """collect() issues exactly these three commands, in this order."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/brew"),
            patch(
                "subprocess.run", side_effect=_brew_mocks("git 2.44.0\n", "git\n", "")
            ) as mock_run,
        ):
            HomebrewCollector().collect()

        assert [call.args[0] for call in mock_run.call_args_list] == [
            ["brew", "list", "--formula", "--versions"],
            ["brew", "leaves"],
            ["brew", "list", "--cask", "--versions"],
        ]


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
