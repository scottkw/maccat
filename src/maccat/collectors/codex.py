"""CodexCollector — 1-section MCP collector at byte-parity with update-list.sh:1748.

Zsh analog: collect_codex_mcp lines 1748–1790.

CAT-05: CLI path reads .name+.type only; TOML fallback reads section-header lines only.
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
_TOML_PATH = Path.home() / ".codex/config.toml"

# CAT-05: clamped transport whitelist — any value not in this set becomes "stdio"
_TRANSPORT_WHITELIST: frozenset[str] = frozenset({"stdio", "http", "sse"})


class CodexCollector(Collector):
    """1-section collector for Codex MCP servers.

    Primary path: codex CLI (``codex mcp list --json``).
    Fallback path: TOML text-grep of ``~/.codex/config.toml`` section headers only.

    CAT-05 SAFETY INVARIANT: Neither path reads command, env, args, url, or headers.
    TOML fallback reads ONLY ``[mcp_servers.NAME]`` header lines — never tomllib.
    """

    # ------------------------------------------------------------------
    # Sub-collectors
    # ------------------------------------------------------------------

    def _collect_via_cli(self) -> list[str]:
        """Collect via ``codex mcp list --json``.

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
        """Collect via text-grep of TOML section header lines.

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
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> CollectorResult:
        """Return 1 section: 'Codex MCP Servers'.

        CLI path is preferred; TOML grep fallback is used when CLI is absent or
        returns an empty result.
        """
        items: list[str] = []

        if shutil.which("codex"):
            items = self._collect_via_cli()

        if not items and _TOML_PATH.is_file():
            items = self._collect_via_toml()

        return CollectorResult(sections=[Section(title=_TITLE, items=items)])


__all__ = ["CodexCollector"]
