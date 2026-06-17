"""Tests for maccat.collectors.codex.

Behavioral spec: update-list.sh lines 1748–1790 (collect_codex_mcp).
CAT-05: Pitfall G TOML text-grep verification — no tomllib import, no value lines read.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import maccat.collectors.codex as codex_mod
from maccat.collectors.codex import CodexCollector

# ---------------------------------------------------------------------------
# Module-level constant used by ALL CAT-05 secret-grep assertions
# ---------------------------------------------------------------------------

SECRET_PATTERN = re.compile(r"token|Bearer|sk-|ghp_|key=|Authorization", re.IGNORECASE)


# ===========================================================================
# CLI path sub-collector
# ===========================================================================


class TestCodexCLIPath:
    """Tests for CodexCollector._collect_via_cli() — CLI primary path."""

    def test_cli_path_collects_servers(self) -> None:
        """CLI returns JSON with one entry → section items contains name and transport."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps([{"name": "s1", "type": "stdio"}])
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = CodexCollector().collect()
        section = result.sections[0]
        full_output = "\n".join(section.items)
        assert "s1" in full_output
        assert "stdio" in full_output

    def test_cli_empty_array_falls_through_to_toml(self, tmp_path: Path) -> None:
        """CLI returns '[]' → falls through to TOML fallback."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "[]"
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[mcp_servers.fallback-srv]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        full_output = "\n".join(result.sections[0].items)
        assert "fallback-srv" in full_output

    def test_cli_transport_clamped(self) -> None:
        """CLI entry with type='unknown' → clamped to 'stdio' via whitelist."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps([{"name": "srv", "type": "unknown"}])
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = CodexCollector().collect()
        full_output = "\n".join(result.sections[0].items)
        assert "stdio" in full_output
        assert "unknown" not in full_output

    def test_cli_nonzero_exit_returns_empty_items(self, tmp_path: Path) -> None:
        """CLI non-zero exit → _collect_via_cli returns []; no TOML fallback if absent."""
        mock_r = MagicMock()
        mock_r.returncode = 1
        mock_r.stdout = ""
        missing_toml = tmp_path / "config.toml"  # does not exist
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].items == []

    def test_cli_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        """CLI returns malformed JSON → items == [] (graceful degradation)."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = "{not: json}"
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].items == []

    def test_cli_non_dict_array_element_degrades(self, tmp_path: Path) -> None:
        """A non-dict array element (string/number/null) is skipped, not raised (CR-01)."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps(
            ["just-a-string", 42, None, {"name": "good", "type": "sse"}]
        )
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()  # must not raise
        full_output = "\n".join(result.sections[0].items)
        assert "good" in full_output
        assert len(result.sections[0].items) == 1


# ===========================================================================
# TOML fallback sub-collector (CAT-05 + Pitfall G)
# ===========================================================================


class TestCodexTOMLFallback:
    """Tests for CodexCollector._collect_via_toml() — text-grep fallback."""

    def test_toml_fallback_reads_only_section_headers(self, tmp_path: Path) -> None:
        """CAT-05 + Pitfall G: TOML fallback extracts names from section headers only.

        Config contains secret-bearing value lines — none may appear in output.
        """
        config_toml = tmp_path / "config.toml"
        config_toml.write_text(
            "[mcp_servers.my-server]\n"
            'command = "/usr/local/bin/server"\n'
            'env = {ANTHROPIC_API_KEY = "sk-ant-secret"}\n'
            "[mcp_servers.other]\n"
            'command = "other"\n',
            encoding="utf-8",
        )
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        section = result.sections[0]
        full_output = "\n".join(section.items)
        assert "my-server" in full_output
        assert "other" in full_output
        # CAT-05: value lines must NOT appear
        assert "sk-ant-secret" not in full_output
        assert "command" not in full_output
        # Secret grep regression
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in TOML output: {full_output!r}"
        )

    def test_toml_skips_non_mcp_sections(self, tmp_path: Path) -> None:
        """TOML sections that don't match [mcp_servers.*] are not collected."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text(
            "[other_section]\n"
            "key = value\n"
            "[mcp_servers.real-server]\n",
            encoding="utf-8",
        )
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        full_output = "\n".join(result.sections[0].items)
        assert "real-server" in full_output
        assert "other_section" not in full_output

    def test_toml_absent_returns_empty(self, tmp_path: Path) -> None:
        """TOML file absent → items == [] (graceful degradation)."""
        missing = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].items == []

    def test_toml_quoted_server_name_stripped(self, tmp_path: Path) -> None:
        """TOML entry [mcp_servers.\"quoted-name\"] → name is 'quoted-name' (quotes stripped)."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text('[mcp_servers."quoted-name"]\n', encoding="utf-8")
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        full_output = "\n".join(result.sections[0].items)
        assert "quoted-name" in full_output
        # Literal quotes must not appear in items
        assert '"' not in full_output


# ===========================================================================
# Degradation
# ===========================================================================


class TestCodexDegradation:
    """Tests for graceful degradation when CLI and TOML are both absent."""

    def test_codex_and_toml_both_absent_returns_empty(self, tmp_path: Path) -> None:
        """No codex CLI and no TOML file → items == []."""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].items == []

    def test_cli_oserror_falls_through_to_toml(self, tmp_path: Path) -> None:
        """WR-01: subprocess.run raising OSError (TOCTOU/exec failure) does not crash;
        MCP collector degrades to the TOML fallback path."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[mcp_servers.toml-srv]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", side_effect=OSError("exec failed")),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()  # must not raise
        assert len(result.sections) == 2
        full_output = "\n".join(result.sections[0].items)
        assert "toml-srv" in full_output

    def test_plugins_cli_oserror_falls_through_to_toml(self, tmp_path: Path) -> None:
        """WR-01: subprocess.run raising OSError does not crash the plugins path;
        it degrades to the [plugins.*] TOML fallback."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[plugins.toml-plug]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", side_effect=OSError("exec failed")),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()  # must not raise
        assert len(result.sections) == 2
        plugins_output = "\n".join(result.sections[1].items)
        assert "toml-plug" in plugins_output

    def test_codex_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'Codex MCP Servers'."""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].title == "Codex MCP Servers"

    def test_codex_raw_is_false(self, tmp_path: Path) -> None:
        """Section raw flag is False — output goes through flush_section."""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[0].raw is False

    def test_collect_returns_exactly_one_section(self, tmp_path: Path) -> None:
        """collect() always returns exactly 2 sections (MCP + Plugins)."""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert len(result.sections) == 2


# ===========================================================================
# Plugins section (CDX-02)
# ===========================================================================


class TestCodexPluginsSection:
    """Tests for CodexCollector._collect_plugins() — second section (CDX-02).

    On Codex v0.46.0 (no plugin system) items == [] is expected, not an error.
    """

    def test_plugins_absent_both_paths_items_empty(self, tmp_path: Path) -> None:
        """No CLI and no [plugins.*] headers in TOML → plugins section items == []."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[mcp_servers.some-srv]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        assert len(result.sections) == 2
        plugins_section = result.sections[1]
        assert plugins_section.title == "Codex Plugins"
        assert plugins_section.items == []

    def test_plugins_toml_quoted_id_extracted(self, tmp_path: Path) -> None:
        """TOML [plugins."myplug@npm"] header → item contains 'myplug' and 'myplug@npm'."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text(
            '[plugins."myplug@npm"]\n'
            'command = "secret-value"\n',
            encoding="utf-8",
        )
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        plugins_items = result.sections[1].items
        assert any("myplug" in item for item in plugins_items), (
            f"Expected 'myplug' in items, got: {plugins_items}"
        )
        assert any("myplug@npm" in item for item in plugins_items), (
            f"Expected 'myplug@npm' in items, got: {plugins_items}"
        )

    def test_plugins_toml_quoted_id_no_value_lines(self, tmp_path: Path) -> None:
        """CAT-05 regression: value line text (command=...) NEVER appears in plugins items."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text(
            '[plugins."plug@npm"]\n'
            'command = "secret-value"\n'
            'env = {API_KEY = "sk-supersecret"}\n',
            encoding="utf-8",
        )
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        plugins_section = result.sections[1]
        full_output = "\n".join(plugins_section.items)
        assert "secret-value" not in full_output
        assert "sk-supersecret" not in full_output
        assert "command" not in full_output
        # SECRET_PATTERN regression
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in plugins output: {full_output!r}"
        )

    def test_plugins_toml_unquoted_barename(self, tmp_path: Path) -> None:
        """TOML [plugins.barename] header (unquoted) → item contains 'barename'."""
        config_toml = tmp_path / "config.toml"
        config_toml.write_text("[plugins.barename]\n", encoding="utf-8")
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", config_toml),
        ):
            result = CodexCollector().collect()
        plugins_items = result.sections[1].items
        assert any("barename" in item for item in plugins_items), (
            f"Expected 'barename' in items, got: {plugins_items}"
        )

    def test_plugins_section_title_is_constant(self, tmp_path: Path) -> None:
        """sections[1].title is exactly _PLUGINS_TITLE == 'Codex Plugins'."""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value=None),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert result.sections[1].title == codex_mod._PLUGINS_TITLE
        assert codex_mod._PLUGINS_TITLE == "Codex Plugins"

    def test_collect_two_sections_stable_when_cli_nonzero(self, tmp_path: Path) -> None:
        """collect() returns 2 sections even when codex CLI is present but returns non-zero."""
        mock_r = MagicMock()
        mock_r.returncode = 1
        mock_r.stdout = ""
        missing_toml = tmp_path / "config.toml"
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
            patch.object(codex_mod, "_TOML_PATH", missing_toml),
        ):
            result = CodexCollector().collect()
        assert len(result.sections) == 2
        assert result.sections[0].title == "Codex MCP Servers"
        assert result.sections[1].title == "Codex Plugins"

    def test_plugins_cli_path_parsed_correctly(self) -> None:
        """Plugins CLI returns JSON with pluginId → item contains name and id."""
        mock_r = MagicMock()
        mock_r.returncode = 0
        mock_r.stdout = json.dumps([{"name": "myplugin", "pluginId": "myplugin@npm"}])
        with (
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("subprocess.run", return_value=mock_r),
        ):
            result = CodexCollector().collect()
        plugins_items = result.sections[1].items
        full_output = "\n".join(plugins_items)
        assert "myplugin" in full_output
        assert "myplugin@npm" in full_output
