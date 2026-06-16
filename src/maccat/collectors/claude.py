"""ClaudeCollector — 3-section collector at byte-parity with update-list.sh:1594/1638/1692.

Zsh analogs:
  collect_claude_plugins      lines 1594–1626
  collect_claude_mcp          lines 1638–1681  (CAT-05 boundary)
  collect_claude_skills_agents lines 1692–1731
"""
from __future__ import annotations

import json
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

# ---------------------------------------------------------------------------
# Module-level path constants — NOT inside class so tests can monkeypatch via
# patch.object(claude_mod, "_PLUGINS_PATH", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_PLUGINS_PATH = Path.home() / ".claude/plugins/installed_plugins.json"
_CLAUDE_JSON = Path.home() / ".claude.json"
_SKILLS_DIR = Path.home() / ".claude/skills"
_AGENTS_DIR = Path.home() / ".claude/agents"

# CAT-05: clamped transport whitelist — any value not in this set becomes "stdio"
_TRANSPORT_WHITELIST: frozenset[str] = frozenset({"stdio", "http", "sse"})


# ---------------------------------------------------------------------------
# Module-level helper — shared by ClaudeCollector and available to later plans
# (OpenCodeCollector, GeminiCollector) that need the same YAML name extraction.
# ---------------------------------------------------------------------------


def _read_yaml_name(path: Path) -> str:
    """Extract 'name:' value from YAML frontmatter — first matching line only.

    Mirrors: grep '^name:' FILE | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"'

    Returns "" on OSError, missing file, or no matching line.
    """
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("name:"):
                return line[len("name:"):].strip().strip('"')
    except OSError:
        pass
    return ""


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class ClaudeCollector(Collector):
    """3-section collector for Claude Code plugins, MCP servers, and skills/agents.

    Sections returned by collect() in fixed order:
      1. Claude Code Plugins
      2. Claude Code MCP Servers   (CAT-05: name + transport only)
      3. Claude Code Skills & Agents
    All sections have raw=False (output goes through flush_section).
    """

    _PLUGINS_TITLE = "Claude Code Plugins"
    _MCP_TITLE = "Claude Code MCP Servers"
    _SKILLS_TITLE = "Claude Code Skills & Agents"

    # ------------------------------------------------------------------
    # Sub-collectors
    # ------------------------------------------------------------------

    def _collect_plugins(self) -> Section:
        """Collect installed Claude Code plugins from installed_plugins.json.

        Schema: {"plugins": {"name@marketplace": [{"version": "1.0.0", ...}], ...}}
        emit_item(name, version, key) → "name (version) [name@marketplace]"
        """
        if not _PLUGINS_PATH.is_file():
            return Section(title=self._PLUGINS_TITLE, items=[])
        try:
            data = json.loads(_PLUGINS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return Section(title=self._PLUGINS_TITLE, items=[])
        items: list[str] = []
        plugins = data.get("plugins")
        if not isinstance(plugins, dict):
            return Section(title=self._PLUGINS_TITLE, items=[])
        for key, versions in plugins.items():
            name = key.split("@", 1)[0]
            # CAT-06: jq `.value[0].version // ""` degrades on non-list/non-dict shapes.
            version = ""
            if isinstance(versions, list) and versions and isinstance(versions[0], dict):
                version = versions[0].get("version", "")
            line = emit_item(name, version, key)
            if line:
                items.append(line)
        return Section(title=self._PLUGINS_TITLE, items=items)

    def _collect_mcp(self) -> Section:
        """Collect Claude Code MCP server names + transport types from ~/.claude.json.

        CAT-05 SAFETY INVARIANT: reads ONLY cfg.get("type", "stdio").
        NEVER reads .command, .env, .args, .url, or .headers.

        emit_item(name, "", transport) → "name [transport]"
        """
        if not _CLAUDE_JSON.is_file():
            return Section(title=self._MCP_TITLE, items=[])
        try:
            data = json.loads(_CLAUDE_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return Section(title=self._MCP_TITLE, items=[])
        items: list[str] = []
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            return Section(title=self._MCP_TITLE, items=[])
        for name, cfg in servers.items():
            # CAT-06: non-dict server value degrades (jq `.value.type // "stdio"`); skip.
            # PARITY DEVIATION (intentional, WR-01): zsh's single `jq` invocation
            # aborts the whole section on the first non-object value; this per-entry
            # skip is more robust (keeps valid neighbours). Only differs on malformed
            # configs that never occur in real data, so golden parity is unaffected.
            if not isinstance(cfg, dict):
                continue
            # CAT-05: ONLY .type — NEVER .command, .env, .args, .url, .headers
            transport = cfg.get("type", "stdio")
            if transport not in _TRANSPORT_WHITELIST:
                transport = "stdio"
            line = emit_item(name, "", transport)
            if line:
                items.append(line)
        return Section(title=self._MCP_TITLE, items=items)

    def _collect_skills_agents(self) -> Section:
        """Collect Claude Code skills and agents into a single combined section.

        Skills:  ~/.claude/skills/ — one subdir per skill; name from SKILL.md frontmatter
        Agents:  ~/.claude/agents/*.md — name from YAML frontmatter 'name:' field
        Both directories are optional; absent → items stays empty.

        emit_item(name, "", "") → bare name (no version, no id)
        """
        items: list[str] = []

        # Skills: one subdirectory per skill
        if _SKILLS_DIR.is_dir():
            for skill_dir in sorted(_SKILLS_DIR.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                name = _read_yaml_name(skill_md) if skill_md.is_file() else ""
                if not name:
                    name = skill_dir.name
                line = emit_item(name, "", "")
                if line:
                    items.append(line)

        # Agents: individual .md files
        if _AGENTS_DIR.is_dir():
            for agent_md in sorted(_AGENTS_DIR.glob("*.md")):
                name = _read_yaml_name(agent_md)
                if not name:
                    name = agent_md.stem
                line = emit_item(name, "", "")
                if line:
                    items.append(line)

        return Section(title=self._SKILLS_TITLE, items=items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> CollectorResult:
        """Return all three Claude sections in fixed order."""
        return CollectorResult(
            sections=[
                self._collect_plugins(),
                self._collect_mcp(),
                self._collect_skills_agents(),
            ]
        )


__all__ = ["ClaudeCollector"]
