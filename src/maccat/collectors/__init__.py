"""Collector registry — ordered list matching generate_catalog section order.

update-list.sh:2220 (generate_catalog).
"""
from __future__ import annotations

from maccat.collectors.base import Collector, CollectorResult, Section

__all__ = ["REGISTRY", "Collector", "CollectorResult", "Section", "get_registry"]


def get_registry() -> list[Collector]:
    """Return the ordered list of Collector instances matching generate_catalog section order.

    Import order: update-list.sh lines 2220-2313 (generate_catalog section call order).
    Imports are deferred inside this function so that importing maccat.collectors (or
    maccat.collectors.base) is always safe even when collector modules do not yet exist.
    This enables incremental per-plan development: each collector module can be imported
    and unit-tested independently without all 12 siblings being present.

    Section order (21 sections from 15 collectors):
      1.  Homebrew Packages             (raw)
      2.  App Store Applications        (raw)
      3.  Setapp Applications            (raw)
      4.  Web-installed Applications     (raw)
      5.  Claude Code Plugins
      6.  Claude Code MCP Servers
      7.  Claude Code Skills & Agents
      8.  Codex MCP Servers
      9.  Codex Plugins
      10. OpenCode Plugins
      11. OpenCode MCP Servers
      12. OpenCode Agents
      13. Gemini CLI Extensions
      14. Gemini CLI MCP Servers
      15. VS Code Extensions
      16. Cursor Extensions
      17. Zed Extensions
      18. Google Chrome Extensions
      19. Microsoft Edge Extensions
      20. Brave Browser Extensions
      21. Firefox Extensions
    """
    # Imports are inside the function body — safe to call get_registry() only when
    # all 15 collector modules exist (Phase 16 + beyond).
    from maccat.collectors.brave import BraveCollector
    from maccat.collectors.chrome import ChromeCollector
    from maccat.collectors.claude import ClaudeCollector
    from maccat.collectors.codex import CodexCollector
    from maccat.collectors.cursor import CursorCollector
    from maccat.collectors.edge import EdgeCollector
    from maccat.collectors.firefox import FirefoxCollector
    from maccat.collectors.gemini import GeminiCollector
    from maccat.collectors.homebrew import HomebrewCollector
    from maccat.collectors.mas import MasCollector
    from maccat.collectors.opencode import OpenCodeCollector
    from maccat.collectors.setapp import SetappCollector
    from maccat.collectors.vscode import VSCodeCollector
    from maccat.collectors.webapps import WebAppsCollector
    from maccat.collectors.zed import ZedCollector

    # Return list MUST preserve section order from generate_catalog lines 2220-2313.
    # Do NOT re-sort alphabetically — order is semantically significant.
    return [
        HomebrewCollector(),
        MasCollector(),
        SetappCollector(),
        WebAppsCollector(),
        ClaudeCollector(),      # yields 3 sections: Plugins, MCP Servers, Skills & Agents
        CodexCollector(),       # yields 2 sections: MCP Servers, Plugins
        OpenCodeCollector(),    # yields 3 sections: Plugins, MCP Servers, Agents
        GeminiCollector(),      # yields 2 sections: Extensions, MCP Servers
        VSCodeCollector(),
        CursorCollector(),
        ZedCollector(),         # yields 1 section: Zed Extensions
        ChromeCollector(),
        EdgeCollector(),        # NEW — BRW-01
        BraveCollector(),       # NEW — BRW-02
        FirefoxCollector(),
    ]
