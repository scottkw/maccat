"""CodexCollector — 2-section collector (MCP Servers + Plugins) at byte-parity with update-list.sh:1748.

Zsh analog: collect_codex_mcp lines 1748–1790.

CAT-05: CLI paths read identity fields only (.name, .type, .pluginId); TOML fallbacks read
section-header lines only — never tomllib, never value lines, never .mcp.json bundle files.
FMT-03: plugin items are identity-only (name + id); no command/env/args/url/headers ever emitted.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section

# ---------------------------------------------------------------------------
# Module-level constants — NOT inside class so tests can monkeypatch via
# patch.object(codex_mod, "_TOML_PATH", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_TITLE = "Codex MCP Servers"
_PLUGINS_TITLE = "Codex Plugins"
_TOML_PATH = Path.home() / ".codex/config.toml"

# CAT-05: clamped transport whitelist — any value not in this set becomes "stdio"
_TRANSPORT_WHITELIST: frozenset[str] = frozenset({"stdio", "http", "sse"})


class CodexCollector(Collector):
    """2-section collector for Codex MCP servers and Codex Plugins.

    Section 0 — "Codex MCP Servers":
        Primary path: codex CLI (``codex mcp list --json``).
        Fallback path: TOML text-grep of ``~/.codex/config.toml`` section headers only.

    Section 1 — "Codex Plugins":
        Primary path: codex CLI (``codex plugin list --json``) when available.
        Fallback path: TOML text-grep of ``[plugins.*]`` headers in ``~/.codex/config.toml``.
        On Codex v0.46.0 (no plugin system): items == [] — expected, not an error.

    CAT-05 SAFETY INVARIANT: Neither path reads command, env, args, url, or headers.
    TOML fallbacks read ONLY section-header lines — never tomllib.
    FMT-03: plugin entries are identity-only — name and id; no bundle file (.mcp.json) reads.
    """

    # ------------------------------------------------------------------
    # MCP sub-collectors
    # ------------------------------------------------------------------

    def _collect_via_cli(self) -> list[str]:
        """Collect MCP servers via ``codex mcp list --json``.

        CAT-05: reads ONLY .name and .type — never .command, .env, .args, .url, .headers.
        Returns [] on non-zero exit, empty stdout, empty array, or JSON decode error.
        """
        result = subprocess.run(
            ["codex", "mcp", "list", "--json"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        try:
            entries = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        if not isinstance(entries, list) or not entries:
            return []
        items: list[str] = []
        for entry in entries:
            # CAT-06: non-dict array element degrades; skip.
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "")
            # CAT-05: ONLY .type — NEVER .command, .env, .args, .url, .headers
            transport = entry.get("type", "stdio")
            if transport not in _TRANSPORT_WHITELIST:
                transport = "stdio"
            line = emit_item(name, "", transport)
            if line:
                items.append(line)
        return items

    def _collect_via_toml(self) -> list[str]:
        """Collect MCP servers via text-grep of TOML section header lines.

        CAT-05 + Pitfall G: reads ONLY ``[mcp_servers.NAME]`` header lines via regex.
        Value lines (command, env, args, url, headers) are NEVER read — no tomllib.loads().
        Mirrors: grep '^\\[mcp_servers\\.' config.toml | sed ... (update-list.sh:1768)
        """
        try:
            text = _TOML_PATH.read_text(encoding="utf-8")
        except OSError:
            return []
        items: list[str] = []
        for line in text.splitlines():
            m = re.match(r"^\[mcp_servers\.(.*)\]$", line.strip())
            if m:
                name = m.group(1).strip('"')
                transport = "stdio"  # default — value lines are never read (CAT-05)
                item = emit_item(name, "", transport)
                if item:
                    items.append(item)
        return items

    # ------------------------------------------------------------------
    # MCP section
    # ------------------------------------------------------------------

    def _collect_mcp(self) -> Section:
        """Return the 'Codex MCP Servers' section.

        CLI path is preferred; TOML grep fallback is used when CLI is absent or
        returns an empty result.
        """
        items: list[str] = []

        if shutil.which("codex"):
            items = self._collect_via_cli()

        if not items and _TOML_PATH.is_file():
            items = self._collect_via_toml()

        return Section(title=_TITLE, items=items)

    # ------------------------------------------------------------------
    # Plugins sub-collectors
    # ------------------------------------------------------------------

    def _collect_plugins_via_cli(self) -> list[str]:
        """Collect plugins via ``codex plugin list --json``.

        CAT-05 / FMT-03: reads ONLY .name and .pluginId — never .command, .env, .args, .url.
        Returns [] on non-zero exit, empty stdout, empty array, or JSON decode error.
        """
        result = subprocess.run(
            ["codex", "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        try:
            entries = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        if not isinstance(entries, list) or not entries:
            return []
        items: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            # FMT-03 / CDX-02: identity-only — name and pluginId only
            name = entry.get("name", "") or entry.get("pluginId", "")
            id_ = entry.get("pluginId", "") or entry.get("name", "")
            line = emit_item(name, "", id_)
            if line:
                items.append(line)
        return items

    def _collect_plugins_via_toml(self) -> list[str]:
        """Collect plugins via text-grep of TOML ``[plugins.*]`` section header lines.

        CAT-05 / FMT-03: reads ONLY header lines via regex — no tomllib.loads(), no value lines,
        no .mcp.json bundle files. Mirrors _collect_via_toml discipline exactly.

        Header formats handled:
          [plugins."myplug@npm"]  → name="myplug", id_="myplug@npm"
          [plugins.barename]      → name="barename", id_="barename"
        """
        try:
            text = _TOML_PATH.read_text(encoding="utf-8")
        except OSError:
            return []
        items: list[str] = []
        for line in text.splitlines():
            m = re.match(r'^\[plugins\."?([^"\]]+)"?\]$', line.strip())
            if m:
                key = m.group(1)  # e.g. "myplug@npm" or "barename"
                name = key.split("@", 1)[0]
                id_ = key
                item = emit_item(name, "", id_)
                if item:
                    items.append(item)
        return items

    # ------------------------------------------------------------------
    # Plugins section
    # ------------------------------------------------------------------

    def _collect_plugins(self) -> Section:
        """Return the 'Codex Plugins' section.

        CLI path is preferred; TOML grep fallback is used when CLI is absent or empty.
        On Codex v0.46.0 (no plugin system): items == [] — expected, not an error.

        FMT-03: identity-only output (name + id). Never reads .mcp.json bundle files.
        """
        items: list[str] = []

        if shutil.which("codex"):
            items = self._collect_plugins_via_cli()

        if not items and _TOML_PATH.is_file():
            items = self._collect_plugins_via_toml()

        return Section(title=_PLUGINS_TITLE, items=items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> CollectorResult:
        """Return 2 sections: 'Codex MCP Servers' then 'Codex Plugins'.

        MCP section: CLI-then-TOML-header-grep for MCP server entries.
        Plugins section: CLI-then-TOML-header-grep for plugin entries.
        Both sections degrade to items==[] when nothing is found — never raises.
        """
        return CollectorResult(
            sections=[
                self._collect_mcp(),
                self._collect_plugins(),
            ]
        )


__all__ = ["CodexCollector"]
