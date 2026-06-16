"""Tests for maccat.collectors.claude.

Behavioral spec: update-list.sh lines 1594–1731
  collect_claude_plugins      lines 1594–1626
  collect_claude_mcp          lines 1638–1681  (CAT-05 boundary)
  collect_claude_skills_agents lines 1692–1731
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import maccat.collectors.claude as claude_mod
from maccat.collectors.claude import ClaudeCollector, _read_yaml_name

# ---------------------------------------------------------------------------
# Module-level constant used by ALL CAT-05 secret-grep assertions
# ---------------------------------------------------------------------------

SECRET_PATTERN = re.compile(r"token|Bearer|sk-|ghp_|key=|Authorization", re.IGNORECASE)


# ===========================================================================
# Plugin sub-collector
# ===========================================================================


class TestClaudePlugins:
    """Tests for ClaudeCollector._collect_plugins()."""

    def test_plugins_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Claude Code Plugins'."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(json.dumps({"plugins": {}}), encoding="utf-8")
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()
        assert result.sections[0].title == "Claude Code Plugins"

    def test_plugins_collect(self, tmp_path: Path) -> None:
        """Installed plugin emits name, version, and full key (name@registry)."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(
            json.dumps({"plugins": {"my-plugin@registry": [{"version": "1.2.3"}]}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()
        items = result.sections[0].items
        assert any("my-plugin" in item for item in items)
        assert any("1.2.3" in item for item in items)
        assert any("my-plugin@registry" in item for item in items)

    def test_plugins_absent_returns_empty(self, tmp_path: Path) -> None:
        """Absent plugins file → items == [] (flush_section will produce (none found))."""
        missing = tmp_path / "nonexistent_installed_plugins.json"
        with patch.object(claude_mod, "_PLUGINS_PATH", missing):
            result = ClaudeCollector().collect()
        assert result.sections[0].items == []

    def test_plugins_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        """Malformed JSON in plugins file → items == [] (graceful degradation)."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text("{not: valid json", encoding="utf-8")
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()
        assert result.sections[0].items == []

    def test_plugins_empty_versions_list_uses_empty_version(
        self, tmp_path: Path
    ) -> None:
        """Plugin with empty versions list uses '' for version — no crash."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(
            json.dumps({"plugins": {"no-version@reg": []}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()
        items = result.sections[0].items
        # Item should still appear with name and key, no version brackets
        assert any("no-version" in item for item in items)

    # --- CAT-06 shape-guard regressions (WR-05) ---

    def test_plugins_non_list_versions_degrades(self, tmp_path: Path) -> None:
        """A versions value that is an object (not a list) → no version, no crash."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(
            json.dumps({"plugins": {"obj@reg": {"version": "9.9"}}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()  # must not raise
        items = result.sections[0].items
        assert any("obj" in item for item in items)
        # version not read from a non-list shape
        assert not any("9.9" in item for item in items)

    def test_plugins_list_of_non_dict_degrades(self, tmp_path: Path) -> None:
        """versions[0] being a string (not a dict) → empty version, no crash."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(
            json.dumps({"plugins": {"str@reg": ["1.0.0"]}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()  # must not raise
        items = result.sections[0].items
        assert any("str" in item for item in items)

    def test_plugins_non_dict_top_level_degrades(self, tmp_path: Path) -> None:
        """A non-dict 'plugins' top level (list) degrades to empty, not raise."""
        plugins_json = tmp_path / "installed_plugins.json"
        plugins_json.write_text(json.dumps({"plugins": ["x"]}), encoding="utf-8")
        with patch.object(claude_mod, "_PLUGINS_PATH", plugins_json):
            result = ClaudeCollector().collect()  # must not raise
        assert result.sections[0].items == []


# ===========================================================================
# MCP sub-collector (CAT-05)
# ===========================================================================


class TestClaudeMCP:
    """Tests for ClaudeCollector._collect_mcp() — CAT-05 safety boundary."""

    def test_mcp_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Claude Code MCP Servers'."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.title == "Claude Code MCP Servers"

    def test_mcp_never_emits_secrets(self, tmp_path: Path) -> None:
        """CAT-05: collector must emit name + transport only — zero secret fields.

        The config contains command, args with secret token, and env with API key.
        None of these must appear in the section output.
        """
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({
                "mcpServers": {
                    "my-server": {
                        "type": "stdio",
                        "command": "/usr/local/bin/server",
                        "args": ["--token", "sk-secret-token-12345"],
                        "env": {
                            "ANTHROPIC_API_KEY": "sk-ant-secret",
                            "Authorization": "Bearer ghp_faketoken",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
        )
        # Server name and transport MUST be present
        assert "my-server" in full_output
        assert "stdio" in full_output

    def test_mcp_transport_clamped_to_whitelist(self, tmp_path: Path) -> None:
        """Server with unknown transport type → clamped to 'stdio'."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({"mcpServers": {"my-server": {"type": "unknown-transport"}}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "stdio" in full_output
        assert "unknown-transport" not in full_output

    def test_mcp_http_transport_preserved(self, tmp_path: Path) -> None:
        """Server with type='http' → 'http' is in whitelist, preserved as-is."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({"mcpServers": {"http-server": {"type": "http"}}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "http" in full_output

    def test_mcp_sse_transport_preserved(self, tmp_path: Path) -> None:
        """Server with type='sse' → 'sse' is in whitelist, preserved as-is."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({"mcpServers": {"sse-server": {"type": "sse"}}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "sse" in full_output

    def test_mcp_absent_returns_empty(self, tmp_path: Path) -> None:
        """Absent ~/.claude.json → mcp section items == []."""
        missing = tmp_path / "nonexistent_claude.json"
        with patch.object(claude_mod, "_CLAUDE_JSON", missing):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []

    def test_mcp_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        """Malformed ~/.claude.json → mcp section items == [] (graceful degradation)."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{not valid json", encoding="utf-8")
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []

    def test_mcp_missing_type_defaults_to_stdio(self, tmp_path: Path) -> None:
        """Server with no 'type' key → defaults to 'stdio'."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({"mcpServers": {"typeless-server": {"command": "something"}}}),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "typeless-server" in full_output
        assert "stdio" in full_output
        # command must not appear — CAT-05
        assert "command" not in full_output
        assert "something" not in full_output

    # --- CAT-06 shape-guard regressions (CR-01) ---

    def test_mcp_non_dict_server_value_degrades(self, tmp_path: Path) -> None:
        """A non-dict server value (string) must skip that entry, not raise (CAT-06)."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "bad": "stdio",
                        "alsobad": ["x"],
                        "good": {"type": "http"},
                    }
                }
            ),
            encoding="utf-8",
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()  # must not raise
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        full_output = "\n".join(mcp_section.items)
        assert "good" in full_output
        assert "http" in full_output
        # malformed entries degrade — only the good one survives
        assert len(mcp_section.items) == 1

    def test_mcp_non_dict_mcpservers_degrades(self, tmp_path: Path) -> None:
        """A non-dict mcpServers top level (list) must degrade to empty, not raise."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({"mcpServers": ["x", "y"]}), encoding="utf-8"
        )
        with patch.object(claude_mod, "_CLAUDE_JSON", claude_json):
            result = ClaudeCollector().collect()  # must not raise
        mcp_section = next(s for s in result.sections if "MCP" in s.title)
        assert mcp_section.items == []


# ===========================================================================
# Skills & Agents sub-collector
# ===========================================================================


class TestClaudeSkillsAgents:
    """Tests for ClaudeCollector._collect_skills_agents()."""

    def test_skills_agents_section_title(self, tmp_path: Path) -> None:
        """Section title must be exactly 'Claude Code Skills & Agents'."""
        missing_skills = tmp_path / "skills"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert skills_section.title == "Claude Code Skills & Agents"

    def test_skills_collect(self, tmp_path: Path) -> None:
        """Skill with SKILL.md containing 'name: My Skill' → item contains 'My Skill'."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("name: My Skill\n", encoding="utf-8")
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", skills_dir),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert any("My Skill" in item for item in skills_section.items)

    def test_skills_fallback_to_dirname(self, tmp_path: Path) -> None:
        """Skill dir with no SKILL.md → section items contains the dir basename."""
        skills_dir = tmp_path / "skills"
        skill_dir = skills_dir / "my-nameless-skill"
        skill_dir.mkdir(parents=True)
        # No SKILL.md created
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", skills_dir),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert any("my-nameless-skill" in item for item in skills_section.items)

    def test_agents_collect(self, tmp_path: Path) -> None:
        """Agent .md with 'name: My Agent' → item contains 'My Agent'."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text("name: My Agent\n", encoding="utf-8")
        missing_skills = tmp_path / "skills"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", agents_dir),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert any("My Agent" in item for item in skills_section.items)

    def test_agents_fallback_to_stem(self, tmp_path: Path) -> None:
        """Agent .md with no 'name:' line → section items contains filename stem."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-unnamed-agent.md").write_text(
            "# Just a markdown header\n", encoding="utf-8"
        )
        missing_skills = tmp_path / "skills"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", agents_dir),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert any("my-unnamed-agent" in item for item in skills_section.items)

    def test_skills_agents_both_absent_returns_empty(self, tmp_path: Path) -> None:
        """Neither skills dir nor agents dir exists → items == []."""
        missing_skills = tmp_path / "skills"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert skills_section.items == []

    def test_skills_non_dir_entries_skipped(self, tmp_path: Path) -> None:
        """Files inside skills/ (not subdirs) are skipped — only dirs are skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "not-a-dir.txt").write_text("junk", encoding="utf-8")
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_SKILLS_DIR", skills_dir),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        skills_section = next(s for s in result.sections if "Skills" in s.title)
        assert skills_section.items == []


# ===========================================================================
# _read_yaml_name helper
# ===========================================================================


class TestReadYamlName:
    """Tests for the module-level _read_yaml_name() helper."""

    def test_returns_name_from_first_name_line(self, tmp_path: Path) -> None:
        """Simple 'name: Foo' → returns 'Foo'."""
        f = tmp_path / "SKILL.md"
        f.write_text("name: Foo\n", encoding="utf-8")
        assert _read_yaml_name(f) == "Foo"

    def test_strips_surrounding_double_quotes(self, tmp_path: Path) -> None:
        """'name: \"Quoted Name\"' → returns 'Quoted Name' without quotes."""
        f = tmp_path / "SKILL.md"
        f.write_text('name: "Quoted Name"\n', encoding="utf-8")
        assert _read_yaml_name(f) == "Quoted Name"

    def test_strips_leading_whitespace_after_colon(self, tmp_path: Path) -> None:
        """'name:   Extra Spaces' → returns 'Extra Spaces'."""
        f = tmp_path / "SKILL.md"
        f.write_text("name:   Extra Spaces\n", encoding="utf-8")
        assert _read_yaml_name(f) == "Extra Spaces"

    def test_returns_empty_on_missing_file(self, tmp_path: Path) -> None:
        """Missing file → returns '' (OSError handled)."""
        missing = tmp_path / "nonexistent.md"
        assert _read_yaml_name(missing) == ""

    def test_returns_empty_when_no_name_line(self, tmp_path: Path) -> None:
        """File with no 'name:' line → returns ''."""
        f = tmp_path / "SKILL.md"
        f.write_text("# Just a header\ndescription: Something\n", encoding="utf-8")
        assert _read_yaml_name(f) == ""

    def test_returns_first_name_line_only(self, tmp_path: Path) -> None:
        """Multiple 'name:' lines → returns only the first one."""
        f = tmp_path / "SKILL.md"
        f.write_text("name: First Name\nname: Second Name\n", encoding="utf-8")
        assert _read_yaml_name(f) == "First Name"

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        """Empty file (0 bytes) → returns '' without error."""
        f = tmp_path / "SKILL.md"
        f.write_bytes(b"")
        assert _read_yaml_name(f) == ""


# ===========================================================================
# Integration: collect() returns exactly 3 sections in correct order
# ===========================================================================


class TestClaudeCollectorIntegration:
    """Integration tests for ClaudeCollector.collect()."""

    def test_collect_returns_three_sections_in_order(self, tmp_path: Path) -> None:
        """collect() returns exactly 3 sections with correct titles in fixed order."""
        missing_plugins = tmp_path / "installed_plugins.json"
        missing_claude = tmp_path / ".claude.json"
        missing_skills = tmp_path / "skills"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_PLUGINS_PATH", missing_plugins),
            patch.object(claude_mod, "_CLAUDE_JSON", missing_claude),
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        assert len(result.sections) == 3
        assert result.sections[0].title == "Claude Code Plugins"
        assert result.sections[1].title == "Claude Code MCP Servers"
        assert result.sections[2].title == "Claude Code Skills & Agents"

    def test_all_sections_have_raw_false(self, tmp_path: Path) -> None:
        """All three Claude sections must have raw=False (they go through flush_section)."""
        missing_plugins = tmp_path / "installed_plugins.json"
        missing_claude = tmp_path / ".claude.json"
        missing_skills = tmp_path / "skills"
        missing_agents = tmp_path / "agents"
        with (
            patch.object(claude_mod, "_PLUGINS_PATH", missing_plugins),
            patch.object(claude_mod, "_CLAUDE_JSON", missing_claude),
            patch.object(claude_mod, "_SKILLS_DIR", missing_skills),
            patch.object(claude_mod, "_AGENTS_DIR", missing_agents),
        ):
            result = ClaudeCollector().collect()
        for section in result.sections:
            assert section.raw is False, (
                f"Section '{section.title}' must have raw=False"
            )

    def test_collect_no_exception_on_all_sources_absent(self, tmp_path: Path) -> None:
        """collect() must not raise even when all source files/dirs are absent."""
        with (
            patch.object(claude_mod, "_PLUGINS_PATH", tmp_path / "nope.json"),
            patch.object(claude_mod, "_CLAUDE_JSON", tmp_path / "nope2.json"),
            patch.object(claude_mod, "_SKILLS_DIR", tmp_path / "noskills"),
            patch.object(claude_mod, "_AGENTS_DIR", tmp_path / "noagents"),
        ):
            result = ClaudeCollector().collect()  # must not raise
        assert len(result.sections) == 3

    def test_cat05_secret_grep_on_mcp_with_all_fields(self, tmp_path: Path) -> None:
        """CAT-05 integration: full config with secrets → zero hits in full output."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(
            json.dumps({
                "mcpServers": {
                    "server-a": {
                        "type": "stdio",
                        "command": "/path/to/server",
                        "args": ["--api-key=sk-supersecret"],
                        "env": {"TOKEN": "ghp_mytoken", "Authorization": "Bearer xyz"},
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
        with (
            patch.object(claude_mod, "_CLAUDE_JSON", claude_json),
            patch.object(claude_mod, "_PLUGINS_PATH", tmp_path / "nope.json"),
            patch.object(claude_mod, "_SKILLS_DIR", tmp_path / "noskills"),
            patch.object(claude_mod, "_AGENTS_DIR", tmp_path / "noagents"),
        ):
            result = ClaudeCollector().collect()
        mcp_section = result.sections[1]
        full_output = "\n".join(mcp_section.items)
        assert not SECRET_PATTERN.search(full_output), (
            f"CAT-05 VIOLATION: secret found in MCP output: {full_output!r}"
        )
        assert "server-a" in full_output
        assert "server-b" in full_output
        assert "stdio" in full_output
        assert "http" in full_output
