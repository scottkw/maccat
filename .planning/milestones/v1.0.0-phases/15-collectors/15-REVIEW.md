---
phase: 15-collectors
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/maccat/collectors/claude.py
  - src/maccat/collectors/codex.py
  - src/maccat/collectors/opencode.py
  - src/maccat/collectors/gemini.py
  - src/maccat/collectors/vscode.py
  - src/maccat/collectors/firefox.py
  - src/maccat/collectors/chrome.py
  - src/maccat/collectors/mas.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 15: Code Review Report (Re-review Iteration 2)

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 8
**Status:** clean

## Summary

Re-review of iteration-2 fixes for the 8 prior findings (1 Critical + 7 Warning).
All 8 fixes verified correct and regression-free against the two highest priorities:

- **CAT-05 (no secret leak): HOLDS.** Traced every guarded path in all four MCP
  collectors (claude, codex, opencode, gemini). No path reads or emits
  `command`, `env`, `args`, `url`, or `headers`. A repo-wide grep confirms those
  field names appear only inside CAT-05 reminder comments — never in executable
  reads. Every MCP path reads server name + `.type` only, and `.type` is clamped
  to the `{stdio, http, sse}` whitelist before emit. The codex TOML fallback
  reads only `[mcp_servers.NAME]` header lines via regex and hardcodes
  `transport="stdio"`. CAT-05 is intact.
- **CAT-06 (complete degradation): COMPLETE.** An adversarial harness fed
  misshaped-but-valid JSON (non-dict `mcpServers` value, list-typed `mcpServers`,
  non-list `plugins`, non-string plugin entries, non-list `.mcp`, non-dict addon,
  non-dict `defaultLocale`, 0-byte gemini file, non-list `extensions.json`,
  unreadable Chrome profile dir) to every flagged collector. All degrade
  (skip/fallback) without raising. No `generate_catalog`-aborting exceptions.

The two narrow divergences-from-zsh raised in iteration 2 (WR-01, WR-02) have been
**reviewed and accepted as intentional, better-than-zsh degradations** and are now
documented inline in the source with `# PARITY DEVIATION (intentional)` comments.
Both occur only on degenerate/misshaped input that never appears in real `mas`
output or real tool configs, so neither affects Phase 17 golden parity (real data).
No open findings remain.

## Resolved / Accepted Findings

### WR-01: MCP/Firefox per-entry shape guard `continue` vs jq stream-abort — ACCEPTED (intentional)

**Status:** resolved (accepted as intentional deviation).
**Rationale:** The per-entry `isinstance(...)` skip is strictly more robust than
zsh's single `jq` invocation, which aborts the whole section on the first non-object
value. It only diverges on malformed configs that never occur in real data, so it
does not affect real-data golden parity. Documented inline at each guard site
(claude.py, opencode.py, gemini.py MCP loops + firefox.py addon loop) via
`# PARITY DEVIATION (intentional, WR-01)`. Commit 6b64d4c.

### WR-02: mas `_parse_mas_output` drops blank/1-field lines vs awk space-only line — ACCEPTED (intentional)

**Status:** resolved (accepted as intentional deviation).
**Rationale:** Dropping a 0/1-field/blank line is preferable to emitting awk's
lone space-only line. Real `mas list` always emits >=3 fields, so this only
diverges on degenerate input and does not affect real-data golden parity.
Documented inline at the line-drop site in mas.py via
`# PARITY DEVIATION (intentional, WR-02)`. Commit 6b64d4c.

---

## Verification notes (fixes confirmed correct, no action needed)

- **CR-01 (shape guards, 4 MCP collectors + codex CLI + firefox):** correct;
  CAT-05 invariant preserved (only name + `.type` read). Verified by grep + path trace.
- **Prior WR-01 (VS Code/Cursor `extensions.json` non-list guard,
  `vscode.py:101`):** correct; non-list top level returns `[]`, and the CLI-path
  metadata loader (`vscode.py:56`) is independently guarded with
  `isinstance(entries, list)` and per-entry `isinstance(entry, dict)`.
- **Prior WR-02 (mas 2-field):** 2-field branch byte-exact; the remaining
  1-field/blank-line gap is accepted as intentional (see WR-02 above).
- **WR-04/05/06 (OpenCode plugin/.mcp guards; firefox):** correct; non-string
  plugin entries skipped, non-dict `.mcp` returns `[]`, path/URL plugin guard
  intact.
- **WR-07 (Chrome profile `iterdir` OSError guard, `chrome.py:54` and `:67`):**
  correct; unreadable profile or version dir is skipped without raising.
- **Happy paths:** claude/gemini MCP emit `name [transport]` with whitelist
  clamping (`weird`->`stdio`, missing->`stdio`); plugins emit `name (version) [key]`;
  mas emits `App 1.0`. All correct.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
