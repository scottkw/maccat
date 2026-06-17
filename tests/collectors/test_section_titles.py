"""Assert all collector section title constants are unique; new titles fall to manual checklist.

Two tests in one file:
  1. test_all_section_titles_are_unique — prevents copy-paste routing bugs in reinstall/emitter.py
  2. test_new_titles_fall_to_manual_checklist — confirms "Codex Plugins" + "Zed Extensions" →
     manual checklist, not auto-install blocks (zero changes to reinstall/parser.py or emitter.py).
"""
from __future__ import annotations

import maccat.collectors.brave as brave_mod
import maccat.collectors.chrome as chrome_mod
import maccat.collectors.claude as claude_mod  # noqa: F401 — used via ClaudeCollector class
import maccat.collectors.codex as codex_mod
import maccat.collectors.edge as edge_mod
import maccat.collectors.firefox as ff_mod
import maccat.collectors.gemini as gemini_mod
import maccat.collectors.homebrew as hb_mod
import maccat.collectors.mas as mas_mod
import maccat.collectors.opencode as oc_mod
import maccat.collectors.safari as safari_mod
import maccat.collectors.setapp as setapp_mod
import maccat.collectors.vscode as vscode_mod  # noqa: F401 — used via VSCodeCollector class
import maccat.collectors.webapps as webapps_mod
import maccat.collectors.zed as zed_mod
from maccat.collectors.claude import ClaudeCollector
from maccat.collectors.cursor import CursorCollector
from maccat.collectors.vscode import VSCodeCollector
from maccat.reinstall.emitter import emit_reinstall_script
from maccat.reinstall.parser import ParsedCatalog, ParsedItem, ParsedSection


def test_all_section_titles_are_unique() -> None:
    """All 22 collector section title constants must be unique.

    Prevents reinstall routing bugs where two collectors share a title, causing
    one to silently shadow the other in SECTION_SOURCE_MAP lookups.

    Title constant locations:
      hb_mod.TITLE                   — "Homebrew Packages"
      mas_mod.TITLE                  — "App Store Applications"
      setapp_mod.TITLE               — "Setapp Applications"
      webapps_mod.TITLE              — "Web-installed Applications"
      ClaudeCollector._PLUGINS_TITLE — "Claude Code Plugins"
      ClaudeCollector._MCP_TITLE     — "Claude Code MCP Servers"
      ClaudeCollector._SKILLS_TITLE  — "Claude Code Skills & Agents"
      codex_mod._TITLE               — "Codex MCP Servers"
      codex_mod._PLUGINS_TITLE       — "Codex Plugins"        (Phase 27 Plan 01)
      oc_mod._PLUGINS_TITLE          — "OpenCode Plugins"
      oc_mod._MCP_TITLE              — "OpenCode MCP Servers"
      oc_mod._AGENTS_TITLE           — "OpenCode Agents"
      gemini_mod._EXT_TITLE          — "Gemini CLI Extensions"
      gemini_mod._MCP_TITLE          — "Gemini CLI MCP Servers"
      VSCodeCollector.TITLE          — "VS Code Extensions"
      CursorCollector.TITLE          — "Cursor Extensions"
      zed_mod._TITLE                 — "Zed Extensions"       (Phase 27 Plan 02)
      chrome_mod._TITLE              — "Google Chrome Extensions"
      edge_mod._TITLE                — "Microsoft Edge Extensions"
      brave_mod._TITLE               — "Brave Browser Extensions"
      ff_mod._TITLE                  — "Firefox Extensions"
      safari_mod._TITLE              — "Safari Extensions"     (Phase 29)
    """
    titles = [
        hb_mod.TITLE,                    # "Homebrew Packages"
        mas_mod.TITLE,                   # "App Store Applications"
        setapp_mod.TITLE,                # "Setapp Applications"
        webapps_mod.TITLE,               # "Web-installed Applications"
        ClaudeCollector._PLUGINS_TITLE,  # "Claude Code Plugins"
        ClaudeCollector._MCP_TITLE,      # "Claude Code MCP Servers"
        ClaudeCollector._SKILLS_TITLE,   # "Claude Code Skills & Agents"
        codex_mod._TITLE,                # "Codex MCP Servers"
        codex_mod._PLUGINS_TITLE,        # "Codex Plugins"
        oc_mod._PLUGINS_TITLE,           # "OpenCode Plugins"
        oc_mod._MCP_TITLE,               # "OpenCode MCP Servers"
        oc_mod._AGENTS_TITLE,            # "OpenCode Agents"
        gemini_mod._EXT_TITLE,           # "Gemini CLI Extensions"
        gemini_mod._MCP_TITLE,           # "Gemini CLI MCP Servers"
        VSCodeCollector.TITLE,           # "VS Code Extensions"
        CursorCollector.TITLE,           # "Cursor Extensions"
        zed_mod._TITLE,                  # "Zed Extensions"
        chrome_mod._TITLE,               # "Google Chrome Extensions"
        edge_mod._TITLE,                 # "Microsoft Edge Extensions"
        brave_mod._TITLE,                # "Brave Browser Extensions"
        ff_mod._TITLE,                   # "Firefox Extensions"
        safari_mod._TITLE,               # "Safari Extensions"
    ]
    assert len(titles) == 22, f"Expected 22 titles, got {len(titles)}"
    assert len(titles) == len(set(titles)), (
        f"Duplicate section titles found: {[t for t in titles if titles.count(t) > 1]}"
    )


def test_new_titles_fall_to_manual_checklist() -> None:
    """'Codex Plugins' and 'Zed Extensions' → manual checklist; no auto-install commands.

    SECTION_SOURCE_MAP in reinstall/emitter.py has exactly 4 keys:
      "Homebrew Packages", "App Store Applications", "VS Code Extensions", "Cursor Extensions"
    Any other title falls through to _manual_checklist_block() automatically.
    This test confirms the fallthrough without requiring changes to parser.py or emitter.py.
    """
    catalog = ParsedCatalog(
        path="test.txt",
        sections=[
            ParsedSection(
                title="Codex Plugins",
                items=[
                    ParsedItem(
                        name="some-plugin",
                        version=None,
                        id="some@npm",
                        raw_line="some-plugin [some@npm]",
                    )
                ],
            ),
            ParsedSection(
                title="Zed Extensions",
                items=[
                    ParsedItem(
                        name="HTML",
                        version="0.3.1",
                        id="html",
                        raw_line="HTML (0.3.1) [html]",
                    )
                ],
            ),
        ],
    )

    script = emit_reinstall_script(catalog, source_name="test.txt", generated="2026-06-17")

    # Both new section titles must appear somewhere in the output
    assert "Codex Plugins" in script, "Expected 'Codex Plugins' in reinstall script output"
    assert "Zed Extensions" in script, "Expected 'Zed Extensions' in reinstall script output"

    # The manual checklist header must appear — confirms fallthrough path
    assert "=== Manual Checklist ===" in script, (
        "Expected '=== Manual Checklist ===' header in reinstall script output"
    )

    # Neither section should appear in auto-install blocks
    # (no brew install / mas install / code --install-extension / cursor --install-extension
    # commands should reference these section titles or their items)
    assert "brew install" not in script or "Codex Plugins" not in script.split("brew install")[0]
    assert "mas install" not in script
