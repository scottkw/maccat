---
phase: 17-parity-safety-tests
plan: "01"
subsystem: test-infrastructure
tags: [golden-fixtures, normalization, pytest, zsh-parity, fake-home]
dependency_graph:
  requires: []
  provides:
    - tests/golden/normalize.py (normalize_catalog_body, extract_section_body, SEPARATOR_LINE)
    - tests/golden/generate.py (capture_zsh_section zsh-subprocess harness)
    - tests/golden/fixtures/fake_home/ (synthetic HOME tree)
    - tests/golden/*.golden.txt (17 committed reviewed golden artifacts)
    - tests/conftest.py --update-golden addoption
  affects:
    - Wave 2 (17-02): parity assertion tests read these golden files
tech_stack:
  added: []
  patterns:
    - "zsh subprocess with HOME in script body (not env=) for collector isolation"
    - "section-level golden fixtures — one .golden.txt per section (not full-catalog)"
    - "normalize_catalog_body: two regexes (timestamp + [label]) for byte-stable comparison"
    - "generate.py lazy-import guard: never imported on normal pytest run"
key_files:
  created:
    - tests/golden/__init__.py
    - tests/golden/normalize.py
    - tests/golden/generate.py
    - tests/golden/fixtures/fake_home/ (17 fixture files)
    - tests/golden/fixtures/fake_applications/ (2 stubs)
    - tests/golden/*.golden.txt (17 golden files)
  modified:
    - tests/conftest.py
decisions:
  - "set -e removed from zsh capture script: grep exits 1 on no-match (codex TOML fallback), causing false failure — removed, confirmed codex/opencode collectors pass rc=0 without it"
  - "codex TOML format uses [mcp_servers.NAME] with underscores (not camelCase) — fixes mismatch between plan's [mcpServers] and collector's regex"
  - "opencode.json format: mcp is a direct server-name dict (not nested under 'servers' key) — fixes mismatch with collector's to_entries iteration"
  - "normalize replaces ALL [brackets] including [stdio]/[http] transport labels with [MACHINE] — spec-correct by design"
metrics:
  duration_minutes: 8
  tasks_completed: 2
  files_created: 35
  completed_date: "2026-06-15"
---

# Phase 17 Plan 01: Golden Fixture Harness Summary

Golden-fixture harness foundation: normalize utility, zsh-subprocess capture, --update-golden addoption, synthetic fake_home, and 17 committed section-level golden fixtures with verified zsh-Python byte parity.

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | normalize.py, generate.py, --update-golden conftest extension | be78dd6 | Done |
| 2 | synthetic fake_home + 17 golden files + zsh parity verification | f494cb2 | Done |

## What Was Built

### tests/golden/normalize.py
Pure-function normalization module with no maccat imports:
- `normalize_catalog_body(text)`: two regexes in exact order — `\d{14}` → `TIMESTAMP`, then `\[[^\]]+\]` → `[MACHINE]`
- `SEPARATOR_LINE = "-" * 36`
- `extract_section_body(catalog_text, section_title)`: splits on `\n{SEPARATOR_LINE}\n`, returns body chunk

### tests/golden/generate.py
Zsh-subprocess golden capture harness:
- `capture_zsh_section(collector_fn, fake_home)`: sources `update-list.sh`, calls one collector, reads OUTPUT_FILE
- HOME set in zsh script body (not `env=`) — RESEARCH.md Pitfall 1 guard
- One collector per subprocess call — RESEARCH.md Pitfall 3 guard
- Reads OUTPUT_FILE (temp file), never stdout — RESEARCH.md Pitfall 2 guard
- `set -e` deliberately absent: grep exits 1 on no-match (see Deviations)

### tests/conftest.py extension
Added after existing `catalog_repo` fixture:
- `pytest_addoption`: registers `--update-golden` flag, `action="store_true"`, `default=False`
- `update_golden` fixture: returns `request.config.getoption("--update-golden")` — bool False on normal runs

### tests/golden/fixtures/fake_home/
Minimal synthetic HOME tree covering all 17 sections:
- `.claude/plugins/installed_plugins.json` — 1 plugin entry (test-plugin@registry v1.0.0)
- `.claude.json` — 1 MCP server entry (my-server, type=stdio; command field ignored per CAT-05)
- `.claude/skills/`, `.claude/agents/` — empty dirs (produce "(none found)" in golden)
- `.codex/config.toml` — `[mcp_servers.my-codex-server]` section header (underscore format)
- `.config/opencode/opencode.json` — `{"mcp": {"oc-server": {"type": "stdio"}}}` (direct server dict)
- `.config/opencode/agents/` — empty dir
- `.gemini/extensions/my-gemini-ext/gemini-extension.json` — name + version
- `.gemini/config/mcp_config.json` — 1 MCP server (g-server)
- `.vscode/extensions/extensions.json`, `.cursor/extensions/extensions.json` — 1 ext each
- `Library/Application Support/Google/Chrome/Default/Extensions/abcdefghijklmnop/1.0_0/manifest.json`
- `Library/Application Support/Firefox/profiles.ini` + `Profiles/test.default/extensions.json`

### 17 Golden Files
All committed as reviewed artifacts; strategy per section:

| Section | Strategy | Notes |
|---------|----------|-------|
| Homebrew Packages | not-installed fallback | stable — "Homebrew is not installed." |
| App Store Applications | not-installed fallback | stable — mas "not installed" 2-line message |
| Setapp Applications | not-installed fallback | stable — "Setapp is not installed or detected." |
| Web-installed Applications | Python synthetic only | annotated `# [ASSUMED]` — zsh hardcodes /Applications |
| Claude Code Plugins | synthetic fake_home | zsh parity verified |
| Claude Code MCP Servers | synthetic fake_home | zsh parity verified |
| Claude Code Skills & Agents | empty dirs → (none found) | zsh parity verified |
| Codex MCP Servers | TOML grep fallback | zsh parity verified |
| OpenCode Plugins | no plugin key → (none found) | zsh parity verified |
| OpenCode MCP Servers | synthetic fake_home | zsh parity verified |
| OpenCode Agents | empty dir → (none found) | zsh parity verified |
| Gemini CLI Extensions | synthetic fake_home | zsh parity verified |
| Gemini CLI MCP Servers | synthetic fake_home | zsh parity verified |
| VS Code Extensions | file fallback (CLI mocked absent) | zsh parity verified |
| Cursor Extensions | file fallback (CLI mocked absent) | zsh parity verified |
| Google Chrome Extensions | synthetic fake_home | zsh parity verified |
| Firefox Extensions | synthetic fake_home | zsh parity verified |

Parity verified for 7 sections (Claude plugins, Gemini extensions, VS Code, Codex, OpenCode MCP, Firefox, Chrome) — all passed `normalize(zsh_output) == normalize(python_output)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed `set -e` from zsh capture script**
- **Found during:** Task 2, zsh parity verification for Codex MCP Servers
- **Issue:** `set -e` in the `capture_zsh_section` zsh script body caused rc=1 for codex collector. The `collect_codex_mcp` function uses `grep` which exits 1 when no match is found (this is the expected "no CLI available" fallback path). With `set -e`, this caused the entire subprocess to exit with rc=1, raising RuntimeError.
- **Fix:** Removed `set -e` from generate.py's zsh script. The RESEARCH.md recipe (Pattern 1 / Code Examples) does not include `set -e` — it was added unnecessarily. Verified: codex collector works correctly without it.
- **Files modified:** tests/golden/generate.py
- **Commit:** f494cb2

**2. [Rule 1 - Bug] Fixed codex TOML fixture format**
- **Found during:** Task 2, codex golden generation
- **Issue:** Plan specified `[mcpServers]` (camelCase) in fake TOML but `CodexCollector._collect_via_toml()` uses regex `r"^\[mcp_servers\.(.*)\]$"` (underscore). The camelCase TOML produced empty items.
- **Fix:** Changed fake_home TOML to use `[mcp_servers.my-codex-server]` format matching the collector's regex.
- **Files modified:** tests/golden/fixtures/fake_home/.codex/config.toml

**3. [Rule 1 - Bug] Fixed opencode JSON fixture format**
- **Found during:** Task 2, opencode MCP golden generation
- **Issue:** Plan specified `{"mcp": {"servers": {"oc-server": ...}}}` (nested under `servers`) but `OpenCodeCollector._collect_mcp()` iterates `mcp.items()` directly. The nested format produced `servers [MACHINE]` instead of `oc-server [MACHINE]`.
- **Fix:** Changed fake_home opencode.json to `{"mcp": {"oc-server": {"type": "stdio"}}}` (direct server-name dict at top level of `mcp` key).
- **Files modified:** tests/golden/fixtures/fake_home/.config/opencode/opencode.json

## HARD SAFETY Compliance

- `update-list.sh` byte-unmodified: `git diff HEAD -- update-list.sh` produces empty diff
- HOME set in zsh script body (not `env=` dict) in all capture_zsh_section calls
- Never ran main block of update-list.sh (source-guard verified by RESEARCH.md)
- No live personal/ or office/ directories touched
- Synthetic fixtures contain no real secrets (only transport types and stub names)
- generate.py never imported on normal pytest run (import is conditional on usage)
- A normal `pytest` run does NOT modify any .golden.txt mtime (verified)

## Known Stubs

None — all 17 golden files contain actual normalized output text from synthetic fixtures. No placeholders or "coming soon" text.

## Self-Check: PASSED

- tests/golden/__init__.py: FOUND
- tests/golden/normalize.py: FOUND
- tests/golden/generate.py: FOUND
- tests/conftest.py: FOUND (modified)
- tests/golden/fixtures/fake_home/.gitkeep: FOUND
- 17 *.golden.txt files: FOUND (count verified)
- Task 1 commit be78dd6: FOUND
- Task 2 commit f494cb2: FOUND
- Full pytest suite (400 tests): PASSED
- ruff check src tests: PASSED
- mypy --strict src/maccat: PASSED
- update-list.sh unmodified: VERIFIED
