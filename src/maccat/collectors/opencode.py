"""OpenCodeCollector — 3-section collector at byte-parity with update-list.sh:1802/1861/1930.

Zsh analogs:
  collect_opencode_plugins  lines 1802–1847
  collect_opencode_mcp      lines 1861–1917  (CAT-05 boundary)
  collect_opencode_agents   lines 1930–1953

CAT-05 on MCP section: emits name + transport type only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.collectors.claude import _read_yaml_name

# ---------------------------------------------------------------------------
# Module-level path constants — NOT inside class so tests can monkeypatch via
# patch.object(oc_mod, "_CONFIG_PATH", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path.home() / ".config/opencode/opencode.json"
_AGENTS_DIR = Path.home() / ".config/opencode/agents"

# Section title constants — module-level so tests can import them for the uniqueness guard.
_PLUGINS_TITLE = "OpenCode Plugins"
_MCP_TITLE = "OpenCode MCP Servers"
_AGENTS_TITLE = "OpenCode Agents"

# CAT-05: clamped transport whitelist — any value not in this set becomes "stdio"
_TRANSPORT_WHITELIST: frozenset[str] = frozenset({"stdio", "http", "sse"})


class OpenCodeCollector(Collector):
    """3-section collector for OpenCode plugins, MCP servers, and agents.

    Sections returned by collect() in fixed order:
      1. OpenCode Plugins
      2. OpenCode MCP Servers   (CAT-05: name + transport only)
      3. OpenCode Agents
    All sections have raw=False (output goes through flush_section).
    """

    # ------------------------------------------------------------------
    # Shared config loader
    # ------------------------------------------------------------------

    def _load_config(self) -> dict | None:  # type: ignore[type-arg]
        """Load and parse opencode.json. Returns None on absence or parse error."""
        if not _CONFIG_PATH.is_file():
            return None
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    # Sub-collectors
    # ------------------------------------------------------------------

    def _collect_plugins(self) -> Section:
        """Collect OpenCode plugins from the ``plugin`` array in opencode.json.

        Entry format: ``name@source`` — name is the part before the first ``@``.
        Path/URL guard: entry with no ``@`` that contains ``/`` → warn to stderr, skip.
        emit_item(name, "", "") → bare name.
        """
        title = _PLUGINS_TITLE
        data = self._load_config()
        if data is None:
            return Section(title=title, items=[])
        items: list[str] = []
        for entry in data.get("plugin") or []:
            # CAT-06: non-string plugin entry degrades (jq `.plugin[]?`); skip.
            if not isinstance(entry, str):
                continue
            name = entry.split("@", 1)[0]
            # Path/URL guard: no '@' AND contains '/' → skip with warning
            if name == entry and "/" in entry:
                print(
                    f"  WARNING: skipping OpenCode plugin path/URL: {entry}",
                    file=sys.stderr,
                )
                continue
            if not name:
                continue
            line = emit_item(name, "", "")
            if line:
                items.append(line)
        return Section(title=title, items=items)

    def _collect_mcp(self) -> Section:
        """Collect OpenCode MCP server names + transport types.

        CAT-05 SAFETY INVARIANT: reads ONLY cfg.get("type", "stdio").
        NEVER reads .command, .env, .args, .url, or .headers.

        emit_item(name, "", transport) → "name [transport]"
        """
        title = _MCP_TITLE
        data = self._load_config()
        if data is None:
            return Section(title=title, items=[])
        mcp = data.get("mcp")
        # CAT-06: a populated non-object .mcp (e.g. array) degrades (jq `.mcp | to_entries[]`).
        if not isinstance(mcp, dict) or not mcp:
            return Section(title=title, items=[])
        items: list[str] = []
        for name, cfg in mcp.items():
            # CAT-06: non-dict server value degrades; skip.
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
        return Section(title=title, items=items)

    def _collect_agents(self) -> Section:
        """Collect OpenCode agents from ``~/.config/opencode/agents/*.md``.

        Name extracted from YAML frontmatter ``name:`` field; fallback to stem.
        Same YAML pattern as Claude Code agents (mirrors update-list.sh:1930).
        emit_item(name, "", "") → bare name.
        """
        title = _AGENTS_TITLE
        if not _AGENTS_DIR.is_dir():
            return Section(title=title, items=[])
        items: list[str] = []
        for agent_md in sorted(_AGENTS_DIR.glob("*.md")):
            name = _read_yaml_name(agent_md)
            if not name:
                name = agent_md.stem
            line = emit_item(name, "", "")
            if line:
                items.append(line)
        return Section(title=title, items=items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> CollectorResult:
        """Return all three OpenCode sections in fixed order."""
        return CollectorResult(
            sections=[
                self._collect_plugins(),
                self._collect_mcp(),
                self._collect_agents(),
            ]
        )


__all__ = ["OpenCodeCollector"]
