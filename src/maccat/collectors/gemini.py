"""GeminiCollector — 2-section collector at byte-parity with update-list.sh:1970/2016.

Zsh analogs:
  collect_gemini_extensions  lines 1970–1996
  collect_gemini_mcp         lines 2016–2059  (CAT-05 boundary + Pitfall B empty-file guard)

CAT-05: MCP section emits server name + transport TYPE ONLY.
Pitfall B: mcp_config.json may be 0 bytes; use [[ -s ]] equivalent:
  path.is_file() AND path.stat().st_size > 0.
"""
from __future__ import annotations

import json
from pathlib import Path

from maccat.catalog.format import emit_item
from maccat.collectors.base import Collector, CollectorResult, Section
from maccat.helpers.json_io import json_get

# ---------------------------------------------------------------------------
# Module-level path constants — NOT inside class so tests can monkeypatch via
# patch.object(gemini_mod, "_EXT_DIR", ...) without class-attribute lookup.
# ---------------------------------------------------------------------------

_EXT_DIR = Path.home() / ".gemini/extensions"
_MCP_PATH = Path.home() / ".gemini/config/mcp_config.json"

_EXT_TITLE = "Gemini CLI Extensions"
_MCP_TITLE = "Gemini CLI MCP Servers"

# CAT-05: clamped transport whitelist — any value not in this set becomes "stdio"
_TRANSPORT_WHITELIST: frozenset[str] = frozenset({"stdio", "http", "sse"})


class GeminiCollector(Collector):
    """2-section collector for Gemini CLI extensions and MCP servers.

    Sections returned by collect() in fixed order:
      1. Gemini CLI Extensions
      2. Gemini CLI MCP Servers   (CAT-05: name + transport only; Pitfall B: size guard)
    All sections have raw=False (output goes through flush_section).
    """

    # ------------------------------------------------------------------
    # Sub-collectors
    # ------------------------------------------------------------------

    def _collect_extensions(self) -> Section:
        """Collect Gemini CLI extensions from ~/.gemini/extensions/*/gemini-extension.json.

        Name extracted via json_get; falls back to ext_dir.name if name absent/empty.
        Version extracted via json_get; empty string if absent.
        emit_item(name, version, "") → "name (version)"
        """
        if not _EXT_DIR.is_dir():
            return Section(title=_EXT_TITLE, items=[])
        items: list[str] = []
        for ext_dir in sorted(_EXT_DIR.iterdir()):
            if not ext_dir.is_dir():
                continue
            manifest = ext_dir / "gemini-extension.json"
            if not manifest.is_file():
                continue
            name = json_get(manifest, "name") or ext_dir.name  # fallback to basename if empty
            version = json_get(manifest, "version")
            line = emit_item(name, version, "")
            if line:
                items.append(line)
        return Section(title=_EXT_TITLE, items=items)

    def _collect_mcp(self) -> Section:
        """Collect Gemini CLI MCP server names + transport types from mcp_config.json.

        CAT-05 SAFETY INVARIANT: reads ONLY cfg.get("type", "stdio").
        NEVER reads .command, .env, .args, .url, or .headers.

        Pitfall B GUARD: the file may exist but be 0 bytes ([[ -s ]] equivalent).
        A plain is_file() check returns True for 0-byte files; json.loads("") raises
        JSONDecodeError. We use is_file() AND stat().st_size > 0.

        emit_item(name, "", transport) → "name [transport]"
        """
        # Pitfall B: use [[ -s ]] equivalent — is_file() AND stat().st_size > 0
        if not _MCP_PATH.is_file() or _MCP_PATH.stat().st_size == 0:
            return Section(title=_MCP_TITLE, items=[])
        try:
            data = json.loads(_MCP_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return Section(title=_MCP_TITLE, items=[])
        items: list[str] = []
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            return Section(title=_MCP_TITLE, items=[])
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
        return Section(title=_MCP_TITLE, items=items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self) -> CollectorResult:
        """Return both Gemini sections in fixed order."""
        return CollectorResult(
            sections=[
                self._collect_extensions(),
                self._collect_mcp(),
            ]
        )


__all__ = ["GeminiCollector"]
