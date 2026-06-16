"""Tests for maccat.collectors.opencode.

Behavioral spec: update-list.sh lines 1802–1953.
  collect_opencode_plugins  lines 1802–1847
  collect_opencode_mcp      lines 1861–1917  (CAT-05 boundary)
  collect_opencode_agents   lines 1930–1953
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import maccat.collectors.opencode as oc_mod
from maccat.collectors.opencode import OpenCodeCollector

# ---------------------------------------------------------------------------
# Module-level constant used by ALL CAT-05 secret-grep assertions
# ---------------------------------------------------------------------------

SECRET_PATTERN = re.compile(r"token|Bearer|sk-|ghp_|key=|Authorization", re.IGNORECASE)


# ===========================================================================
# Plugins sub-collector
# ===========================================================================


class TestOpenCodePlugins:
    """Tests for OpenCodeCollector._collect_plugins()."""

    def test_plugins_collect(self, tmp_path: Path) -> None:
        """Config with ``plugin: [myplugin@npm]`` → section items contains 'myplugin'."""
        config = tmp_path / "opencode.json"
        config.write_text(json.dumps({"plugin": ["myplugin@npm"]}), encoding="utf-8")
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        items = result.sections[0].items
        assert any("myplugin" in item for item in items)
        # The @npm suffix must not appear in the name
        assert not any("@npm" in item for item in items)

    def test_plugins_path_url_guard(self, tmp_path: Path, capsys: object) -> None:  # type: ignore[type-arg]
        """Entry without '@' that contains '/' → warn to stderr and skip."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"plugin": ["some/local/path"]}), encoding="utf-8"
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        # The path entry must NOT appear in items
        items = result.sections[0].items
        assert not any("some/local/path" in item for item in items)
        assert items == []

    def test_plugins_config_absent_returns_empty(self, tmp_path: Path) -> None:
        """Config file absent → plugins section items == []."""
        missing = tmp_path / "opencode.json"
        with patch.object(oc_mod, "_CONFIG_PATH", missing):
            result = OpenCodeCollector().collect()
        assert result.sections[0].items == []

    def test_plugins_null_plugin_field_returns_empty(self, tmp_path: Path) -> None:
        """Config with no 'plugin' key → items == []."""
        config = tmp_path / "opencode.json"
        config.write_text(json.dumps({"mcp": {}}), encoding="utf-8")
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        assert result.sections[0].items == []

    def test_plugins_multiple_entries(self, tmp_path: Path) -> None:
        """Multiple plugins → all names appear in items."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"plugin": ["alpha@npm", "beta@src", "gamma@registry"]}),
            encoding="utf-8",
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        full_output = "\n".join(result.sections[0].items)
        assert "alpha" in full_output
        assert "beta" in full_output
        assert "gamma" in full_output

    def test_plugins_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'OpenCode Plugins'."""
        missing = tmp_path / "opencode.json"
        with patch.object(oc_mod, "_CONFIG_PATH", missing):
            result = OpenCodeCollector().collect()
        assert result.sections[0].title == "OpenCode Plugins"

    # --- CAT-06 shape-guard regression (WR-04) ---

    def test_plugins_non_string_entry_degrades(self, tmp_path: Path) -> None:
        """A non-string plugin entry (number/object/null) is skipped, not raised."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"plugin": [123, {"x": 1}, None, "good@npm"]}),
            encoding="utf-8",
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()  # must not raise
        full_output = "\n".join(result.sections[0].items)
        assert "good" in full_output
        assert len(result.sections[0].items) == 1


# ===========================================================================
# MCP sub-collector (CAT-05)
# ===========================================================================


class TestOpenCodeMCP:
    """Tests for OpenCodeCollector._collect_mcp() — CAT-05 safety boundary."""

    def test_mcp_never_emits_secrets(self, tmp_path: Path) -> None:
        """CAT-05: MCP section emits name + transport only — zero secret fields.

        Config contains command, env with secrets, args, url, headers.
        None of these must appear in the section output.
        """
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({
                "mcp": {
                    "my-server": {
                        "type": "stdio",
                        "command": "/secret/srv",
                        "args": ["--token", "sk-secret-token-12345"],
                        "env": {
                            "TOKEN": "sk-123",
                            "Authorization": "Bearer ghp_faketoken",
                        },
                        "url": "https://api.example.com/secret",
                        "headers": {"x-api-key": "key=abc123"},
                    }
                }
            }),
            encoding="utf-8",
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        mcp_section = result.sections[1]
        full_output = "\n".join(mcp_section.items)
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
        )
        # Server name and transport MUST be present
        assert "my-server" in full_output
        assert "stdio" in full_output

    def test_mcp_transport_clamped(self, tmp_path: Path) -> None:
        """Server with unknown transport type → clamped to 'stdio'."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"mcp": {"srv": {"type": "bad"}}}), encoding="utf-8"
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        full_output = "\n".join(result.sections[1].items)
        assert "stdio" in full_output
        assert "bad" not in full_output

    def test_mcp_null_mcp_field_returns_empty(self, tmp_path: Path) -> None:
        """Config with ``"mcp": null`` → mcp section items == []."""
        config = tmp_path / "opencode.json"
        config.write_text(json.dumps({"mcp": None}), encoding="utf-8")
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        assert result.sections[1].items == []

    def test_mcp_absent_mcp_key_returns_empty(self, tmp_path: Path) -> None:
        """Config with no 'mcp' key → mcp section items == []."""
        config = tmp_path / "opencode.json"
        config.write_text(json.dumps({"plugin": []}), encoding="utf-8")
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        assert result.sections[1].items == []

    # --- CAT-06 shape-guard regressions (CR-01 / WR-06) ---

    def test_mcp_populated_non_dict_mcp_degrades(self, tmp_path: Path) -> None:
        """A populated non-object .mcp (array) degrades to empty, not .items() crash."""
        config = tmp_path / "opencode.json"
        config.write_text(json.dumps({"mcp": ["x", "y"]}), encoding="utf-8")
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()  # must not raise
        assert result.sections[1].items == []

    def test_mcp_non_dict_server_value_degrades(self, tmp_path: Path) -> None:
        """A non-dict server value is skipped, not raised (CAT-06)."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"mcp": {"bad": "stdio", "good": {"type": "http"}}}),
            encoding="utf-8",
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()  # must not raise
        full_output = "\n".join(result.sections[1].items)
        assert "good" in full_output
        assert len(result.sections[1].items) == 1

    def test_mcp_missing_type_defaults_to_stdio(self, tmp_path: Path) -> None:
        """MCP server without 'type' key → defaults to 'stdio'."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"mcp": {"no-type-server": {"command": "something"}}}),
            encoding="utf-8",
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        full_output = "\n".join(result.sections[1].items)
        assert "no-type-server" in full_output
        assert "stdio" in full_output
        # command must NOT appear — CAT-05
        assert "command" not in full_output
        assert "something" not in full_output

    def test_mcp_http_transport_preserved(self, tmp_path: Path) -> None:
        """Server with type='http' → 'http' is in whitelist, preserved."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({"mcp": {"http-server": {"type": "http"}}}), encoding="utf-8"
        )
        with patch.object(oc_mod, "_CONFIG_PATH", config):
            result = OpenCodeCollector().collect()
        full_output = "\n".join(result.sections[1].items)
        assert "http" in full_output

    def test_mcp_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'OpenCode MCP Servers'."""
        missing = tmp_path / "opencode.json"
        with patch.object(oc_mod, "_CONFIG_PATH", missing):
            result = OpenCodeCollector().collect()
        assert result.sections[1].title == "OpenCode MCP Servers"


# ===========================================================================
# Agents sub-collector
# ===========================================================================


class TestOpenCodeAgents:
    """Tests for OpenCodeCollector._collect_agents()."""

    def test_agents_collect(self, tmp_path: Path) -> None:
        """Agent .md with 'name: MyAgent' → section items contains 'MyAgent'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent.md").write_text("name: MyAgent\n", encoding="utf-8")
        with patch.object(oc_mod, "_AGENTS_DIR", agents_dir):
            result = OpenCodeCollector().collect()
        items = result.sections[2].items
        assert any("MyAgent" in item for item in items)

    def test_agents_fallback_to_stem(self, tmp_path: Path) -> None:
        """Agent .md with no 'name:' line → items contains the filename stem."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-nameless-agent.md").write_text(
            "# Just a header\n", encoding="utf-8"
        )
        with patch.object(oc_mod, "_AGENTS_DIR", agents_dir):
            result = OpenCodeCollector().collect()
        items = result.sections[2].items
        assert any("my-nameless-agent" in item for item in items)

    def test_agents_dir_absent_returns_empty(self, tmp_path: Path) -> None:
        """Absent agents dir → agents section items == []."""
        missing_dir = tmp_path / "agents"
        with patch.object(oc_mod, "_AGENTS_DIR", missing_dir):
            result = OpenCodeCollector().collect()
        assert result.sections[2].items == []

    def test_agents_multiple_files_sorted(self, tmp_path: Path) -> None:
        """Multiple agents → all appear in output (sorted order)."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "zebra.md").write_text("name: Zebra\n", encoding="utf-8")
        (agents_dir / "alpha.md").write_text("name: Alpha\n", encoding="utf-8")
        with patch.object(oc_mod, "_AGENTS_DIR", agents_dir):
            result = OpenCodeCollector().collect()
        full_output = "\n".join(result.sections[2].items)
        assert "Zebra" in full_output
        assert "Alpha" in full_output

    def test_agents_section_title(self, tmp_path: Path) -> None:
        """Section title is exactly 'OpenCode Agents'."""
        missing_dir = tmp_path / "agents"
        with patch.object(oc_mod, "_AGENTS_DIR", missing_dir):
            result = OpenCodeCollector().collect()
        assert result.sections[2].title == "OpenCode Agents"


# ===========================================================================
# Integration: collect() returns exactly 3 sections in correct order
# ===========================================================================


class TestOpenCodeCollectorIntegration:
    """Integration tests for OpenCodeCollector.collect()."""

    def test_collect_returns_three_sections_in_order(self, tmp_path: Path) -> None:
        """collect() returns exactly 3 sections with correct titles in fixed order."""
        missing_config = tmp_path / "opencode.json"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(oc_mod, "_CONFIG_PATH", missing_config),
            patch.object(oc_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = OpenCodeCollector().collect()
        assert len(result.sections) == 3
        assert result.sections[0].title == "OpenCode Plugins"
        assert result.sections[1].title == "OpenCode MCP Servers"
        assert result.sections[2].title == "OpenCode Agents"

    def test_all_sections_have_raw_false(self, tmp_path: Path) -> None:
        """All three OpenCode sections must have raw=False."""
        missing_config = tmp_path / "opencode.json"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(oc_mod, "_CONFIG_PATH", missing_config),
            patch.object(oc_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = OpenCodeCollector().collect()
        for section in result.sections:
            assert section.raw is False, (
                f"Section '{section.title}' must have raw=False"
            )

    def test_collect_no_exception_on_all_sources_absent(self, tmp_path: Path) -> None:
        """collect() must not raise even when all source files/dirs are absent."""
        missing_config = tmp_path / "opencode.json"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(oc_mod, "_CONFIG_PATH", missing_config),
            patch.object(oc_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = OpenCodeCollector().collect()  # must not raise
        assert len(result.sections) == 3

    def test_cat05_secret_grep_full_mcp_config(self, tmp_path: Path) -> None:
        """CAT-05 integration: full config with secrets → zero hits in full MCP output."""
        config = tmp_path / "opencode.json"
        config.write_text(
            json.dumps({
                "mcp": {
                    "server-a": {
                        "type": "stdio",
                        "command": "/path/to/server",
                        "args": ["--api-key=sk-supersecret"],
                        "env": {
                            "TOKEN": "ghp_mytoken",
                            "Authorization": "Bearer xyz",
                        },
                        "url": "https://api.example.com/secret-endpoint",
                        "headers": {"x-api-key": "key=abc123"},
                    },
                    "server-b": {
                        "type": "http",
                    },
                }
            }),
            encoding="utf-8",
        )
        missing_agents = tmp_path / "agents"
        with (
            patch.object(oc_mod, "_CONFIG_PATH", config),
            patch.object(oc_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = OpenCodeCollector().collect()
        mcp_section = result.sections[1]
        full_output = "\n".join(mcp_section.items)
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
        )
        assert "server-a" in full_output
        assert "server-b" in full_output
        assert "stdio" in full_output
        assert "http" in full_output
