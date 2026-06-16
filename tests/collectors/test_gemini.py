"""Tests for maccat.collectors.gemini.

Behavioral spec: update-list.sh lines 1970–2059
  collect_gemini_extensions  lines 1970–1996
  collect_gemini_mcp         lines 2016–2059  (CAT-05 boundary + Pitfall B empty-file guard)

CAT-05: MCP section must emit name + transport ONLY — zero secret fields.
Pitfall B: 0-byte mcp_config.json must yield empty items, NOT json.JSONDecodeError.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest  # noqa: F401  (used via pytest test runner; required import for CI)

import maccat.collectors.gemini as gemini_mod
from maccat.collectors.gemini import GeminiCollector

# ---------------------------------------------------------------------------
# Module-level constant used by ALL CAT-05 secret-grep assertions
# ---------------------------------------------------------------------------

SECRET_PATTERN = re.compile(r"token|Bearer|sk-|ghp_|key=|Authorization", re.IGNORECASE)


# ===========================================================================
# Extensions sub-collector
# ===========================================================================


class TestGeminiExtensions:
    """Tests for GeminiCollector._collect_extensions()."""

    def test_extensions_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Gemini CLI Extensions'."""
        ext_dir = tmp_path / "extensions"
        ext_dir.mkdir()
        with patch.object(gemini_mod, "_EXT_DIR", ext_dir):
            result = GeminiCollector().collect()
        assert result.sections[0].title == "Gemini CLI Extensions"

    def test_extensions_collect(self, tmp_path: Path) -> None:
        """Extension with gemini-extension.json → item contains name and version."""
        ext_dir = tmp_path / "extensions"
        my_ext = ext_dir / "my-ext"
        my_ext.mkdir(parents=True)
        (my_ext / "gemini-extension.json").write_text(
            json.dumps({"name": "My Extension", "version": "2.0.0"}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_EXT_DIR", ext_dir):
            result = GeminiCollector().collect()
        items = result.sections[0].items
        assert any("My Extension" in item for item in items)
        assert any("2.0.0" in item for item in items)

    def test_extensions_name_fallback_to_dir(self, tmp_path: Path) -> None:
        """Extension with no 'name' field → items contain ext_dir.name as fallback."""
        ext_dir = tmp_path / "extensions"
        my_ext = ext_dir / "fallback-ext"
        my_ext.mkdir(parents=True)
        (my_ext / "gemini-extension.json").write_text(
            json.dumps({"version": "1.0.0"}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_EXT_DIR", ext_dir):
            result = GeminiCollector().collect()
        items = result.sections[0].items
        assert any("fallback-ext" in item for item in items)

    def test_extensions_name_empty_string_fallback_to_dir(self, tmp_path: Path) -> None:
        """Extension with empty 'name' field → items contain ext_dir.name as fallback."""
        ext_dir = tmp_path / "extensions"
        my_ext = ext_dir / "empty-name-ext"
        my_ext.mkdir(parents=True)
        (my_ext / "gemini-extension.json").write_text(
            json.dumps({"name": "", "version": "0.1.0"}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_EXT_DIR", ext_dir):
            result = GeminiCollector().collect()
        items = result.sections[0].items
        assert any("empty-name-ext" in item for item in items)

    def test_extensions_skips_dirs_without_manifest(self, tmp_path: Path) -> None:
        """Extension directory with no gemini-extension.json is not included in output."""
        ext_dir = tmp_path / "extensions"
        no_manifest = ext_dir / "no-manifest-ext"
        no_manifest.mkdir(parents=True)
        # No gemini-extension.json created
        with patch.object(gemini_mod, "_EXT_DIR", ext_dir):
            result = GeminiCollector().collect()
        items = result.sections[0].items
        assert not any("no-manifest-ext" in item for item in items)
        assert items == []

    def test_extensions_dir_absent_returns_empty(self, tmp_path: Path) -> None:
        """Absent ~/.gemini/extensions → items == [] (flush_section will produce (none found))."""
        missing = tmp_path / "nonexistent_extensions"
        with patch.object(gemini_mod, "_EXT_DIR", missing):
            result = GeminiCollector().collect()
        assert result.sections[0].items == []


# ===========================================================================
# MCP sub-collector (CAT-05 + Pitfall B)
# ===========================================================================


class TestGeminiMCP:
    """Tests for GeminiCollector._collect_mcp() — CAT-05 safety boundary + Pitfall B."""

    def test_mcp_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Gemini CLI MCP Servers'."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.title == "Gemini CLI MCP Servers"

    def test_mcp_collect(self, tmp_path: Path) -> None:
        """MCP server with type='sse' → items contain server name and 'sse' transport."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"srv1": {"type": "sse"}}}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "srv1" in full_output
        assert "sse" in full_output

    def test_mcp_empty_file_returns_none_found(self, tmp_path: Path) -> None:
        """Pitfall B: 0-byte mcp_config.json must NOT trigger json.JSONDecodeError.

        The file exists but is 0 bytes ([[ -s ]] equivalent guard in Python:
        is_file() AND stat().st_size > 0). The collector must return items == [],
        no exception raised.
        """
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_bytes(b"")  # 0 bytes — simulates the Pitfall B case
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []  # flush_section will produce (none found); no exception

    def test_mcp_absent_returns_empty(self, tmp_path: Path) -> None:
        """Absent mcp_config.json → mcp section items == []."""
        missing = tmp_path / "nonexistent_mcp_config.json"
        with patch.object(gemini_mod, "_MCP_PATH", missing):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []

    def test_mcp_never_emits_secrets(self, tmp_path: Path) -> None:
        """CAT-05: collector must emit name + transport only — zero secret fields.

        The config contains command, env with API key, and args with token.
        None of these must appear in the section output. Server name and transport
        must be present.
        """
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps({
                "mcpServers": {
                    "my-server": {
                        "type": "stdio",
                        "command": "/usr/local/bin/secret-server",
                        "args": ["--token", "sk-secret-token-12345"],
                        "env": {
                            "GEMINI_API_KEY": "sk-gem-secret",
                            "Authorization": "Bearer ghp_faketoken",
                        },
                        "url": "https://api.example.com/secret?key=abc123",
                        "headers": {"x-api-key": "key=xyz789"},
                    }
                }
            }),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
        )
        # Server name and transport MUST be present
        assert "my-server" in full_output
        assert "stdio" in full_output

    # --- CAT-06 shape-guard regressions (CR-01) ---

    def test_mcp_non_dict_server_value_degrades(self, tmp_path: Path) -> None:
        """A non-dict server value must skip that entry, not raise (CAT-06)."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps(
                {"mcpServers": {"bad": "stdio", "good": {"type": "sse"}}}
            ),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()  # must not raise
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert len(mcp_section.items) == 1
        assert "good" in "\n".join(mcp_section.items)

    def test_mcp_non_dict_mcpservers_degrades(self, tmp_path: Path) -> None:
        """A non-dict mcpServers top level (list) degrades to empty, not raise."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(json.dumps({"mcpServers": ["x"]}), encoding="utf-8")
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()  # must not raise
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []

    def test_mcp_transport_clamped(self, tmp_path: Path) -> None:
        """Server with unknown transport type → clamped to 'stdio'."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"my-server": {"type": "garbage"}}}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "stdio" in full_output
        assert "garbage" not in full_output

    def test_mcp_http_transport_preserved(self, tmp_path: Path) -> None:
        """Server with type='http' → 'http' is in whitelist, preserved as-is."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"http-server": {"type": "http"}}}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "http" in full_output

    def test_mcp_missing_type_defaults_to_stdio(self, tmp_path: Path) -> None:
        """Server with no 'type' key → defaults to 'stdio'."""
        mcp_path = tmp_path / "mcp_config.json"
        mcp_path.write_text(
            json.dumps({"mcpServers": {"typeless-server": {"command": "something"}}}),
            encoding="utf-8",
        )
        with patch.object(gemini_mod, "_MCP_PATH", mcp_path):
            result = GeminiCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "typeless-server" in full_output
        assert "stdio" in full_output
        # command must not appear — CAT-05
        assert "command" not in full_output
        assert "something" not in full_output


# ===========================================================================
# Integration: collect() returns exactly 2 sections in correct order
# ===========================================================================


class TestGeminiCollectorIntegration:
    """Integration tests for GeminiCollector.collect()."""

    def test_collect_returns_two_sections_in_order(self, tmp_path: Path) -> None:
        """collect() returns exactly 2 sections with correct titles in fixed order.

        When both sources are absent: 2 sections, both items == [].
        """
        missing_ext = tmp_path / "nonexistent_extensions"
        missing_mcp = tmp_path / "nonexistent_mcp_config.json"
        with (
            patch.object(gemini_mod, "_EXT_DIR", missing_ext),
            patch.object(gemini_mod, "_MCP_PATH", missing_mcp),
        ):
            result = GeminiCollector().collect()
        assert len(result.sections) == 2
        assert result.sections[0].title == "Gemini CLI Extensions"
        assert result.sections[1].title == "Gemini CLI MCP Servers"
        assert result.sections[0].items == []
        assert result.sections[1].items == []

    def test_all_sections_have_raw_false(self, tmp_path: Path) -> None:
        """Both Gemini sections must have raw=False (they go through flush_section)."""
        missing_ext = tmp_path / "nonexistent_extensions"
        missing_mcp = tmp_path / "nonexistent_mcp_config.json"
        with (
            patch.object(gemini_mod, "_EXT_DIR", missing_ext),
            patch.object(gemini_mod, "_MCP_PATH", missing_mcp),
        ):
            result = GeminiCollector().collect()
        for section in result.sections:
            assert section.raw is False, (
                f"Section '{section.title}' must have raw=False"
            )

    def test_collect_no_exception_on_all_sources_absent(self, tmp_path: Path) -> None:
        """collect() must not raise even when all source paths are absent."""
        with (
            patch.object(gemini_mod, "_EXT_DIR", tmp_path / "nope_ext"),
            patch.object(gemini_mod, "_MCP_PATH", tmp_path / "nope_mcp.json"),
        ):
            result = GeminiCollector().collect()  # must not raise
        assert len(result.sections) == 2
