---
phase: 15-collectors
verified: 2026-06-14T00:00:00Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 15: Collectors — Verification Report

**Phase Goal:** All 12 source collectors are implemented at byte-parity with the zsh script, degrade gracefully when the source is absent, and never emit secrets.
**Verified:** 2026-06-14
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 12 collectors run end-to-end (Homebrew, mas, Setapp, web, Claude Code, Codex, OpenCode, Gemini, VS Code, Cursor, Chrome, Firefox) | VERIFIED | `get_registry()` returns 12 instances; all 157 collector tests pass; `collect()` called on each with no uncaught exceptions |
| 2 | Absent sources degrade gracefully — writes fallback message or empty items, run completes | VERIFIED | Homebrew absent → `['Homebrew is not installed.']`; MAS absent → two-line fallback; Setapp absent → `['Setapp is not installed or detected.']`; Chrome absent → empty items + NOTE to stderr; Firefox absent → empty items + NOTE to stderr; all confirmed by direct invocation and per-collector tests |
| 3 | No catalog output contains secrets — grep for `token/Bearer/sk-/ghp_/key=/Authorization` across MCP output returns zero hits | VERIFIED | Four MCP collectors (Claude, Codex, OpenCode, Gemini) each have dedicated `SECRET_PATTERN` constant and CAT-05 secret-grep assertions in tests; all 157 collector tests pass; MCP collectors read ONLY `.type` — never `.command`, `.env`, `.args`, `.url`, `.headers` (confirmed by code inspection) |
| 4 | Section order in REGISTRY matches zsh `generate_catalog` section order exactly | VERIFIED | `get_registry()` returns 17 sections in exact canonical order; verified by direct Python assertion against canonical list (17 sections, 12 collectors) |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/collectors/base.py` | Collector ABC, Section, CollectorResult | VERIFIED | `Section.raw=False` default confirmed; `degraded_result()` returns empty items; zero maccat-internal imports |
| `src/maccat/collectors/__init__.py` | Ordered REGISTRY via `get_registry()` | VERIFIED | Lazy imports inside function body; 12 collectors in canonical order; 17 sections total |
| `src/maccat/collectors/homebrew.py` | HomebrewCollector, raw=True | VERIFIED | `brew list --formula` + `brew list --cask`; absent → fallback message; Section(raw=True) |
| `src/maccat/collectors/mas.py` | MasCollector, raw=True | VERIFIED | `mas list` + awk-equivalent parser; absent → two-line fallback; PARITY DEVIATION WR-02 documented |
| `src/maccat/collectors/setapp.py` | SetappCollector, raw=True | VERIFIED | `find /Applications/Setapp -maxdepth 1 -type d` equivalent; absent → fallback; Pitfall C handled |
| `src/maccat/collectors/webapps.py` | WebAppsCollector, raw=True | VERIFIED | Scans `/Applications`, excludes `Setapp*` + `*App Store*`; Pitfall C handled |
| `src/maccat/collectors/claude.py` | ClaudeCollector, 3 sections | VERIFIED | Plugins + MCP Servers (CAT-05: type only) + Skills & Agents; PARITY DEVIATION WR-01 documented |
| `src/maccat/collectors/codex.py` | CodexCollector, 1 section | VERIFIED | CLI primary + TOML text-grep fallback; CAT-05 + Pitfall G; both paths read name+type only |
| `src/maccat/collectors/opencode.py` | OpenCodeCollector, 3 sections | VERIFIED | Plugins + MCP Servers (CAT-05) + Agents; reuses `_read_yaml_name` from claude.py |
| `src/maccat/collectors/gemini.py` | GeminiCollector, 2 sections | VERIFIED | Extensions + MCP Servers (CAT-05); Pitfall B (0-byte file guard) implemented |
| `src/maccat/collectors/vscode.py` | VSCodeCollector, 1 section | VERIFIED | CLI `--list-extensions --show-versions` primary + extensions.json fallback; `_collect_editor_extensions` shared helper |
| `src/maccat/collectors/cursor.py` | CursorCollector, 1 section | VERIFIED | Delegates entirely to `_collect_editor_extensions` with `~/.cursor/extensions` and `cursor` CLI |
| `src/maccat/collectors/chrome.py` | ChromeCollector, 1 section | VERIFIED | Multi-profile (Default + sorted Profile*/); component denylist (10 IDs); `version_sort_tail`; absent → empty items |
| `src/maccat/collectors/firefox.py` | FirefoxCollector, 1 section | VERIFIED | `profiles.ini` discovery; location filter `app-profile` only; Pitfall E (CRLF); absent → empty items |
| `tests/collectors/__init__.py` | Empty pytest package marker | VERIFIED | 0-byte file exists |
| `tests/collectors/test_homebrew.py` | Homebrew + MAS tests | VERIFIED | TestHomebrewCollector + TestMasCollector; degradation tests present |
| `tests/collectors/test_claude.py` | Claude tests incl. `test_mcp_never_emits_secrets` | VERIFIED | test_mcp_never_emits_secrets present at line 139 |
| `tests/collectors/test_codex.py` | Codex tests incl. CAT-05 secret assertion | VERIFIED | `test_toml_fallback_reads_only_section_headers` asserts SECRET_PATTERN absent |
| `tests/collectors/test_opencode.py` | OpenCode tests incl. `test_mcp_never_emits_secrets` | VERIFIED | test_mcp_never_emits_secrets present at line 117 |
| `tests/collectors/test_gemini.py` | Gemini tests incl. `test_mcp_never_emits_secrets` | VERIFIED | test_mcp_never_emits_secrets present at line 161 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `collectors/__init__.py` | `collectors/base.py` | `from maccat.collectors.base import Collector, CollectorResult, Section` | WIRED | Verified by import check |
| `collectors/__init__.py` | all 12 collector modules | lazy imports inside `get_registry()` | WIRED | All 12 imports present inside function body |
| `claude.py` `_collect_mcp` | CAT-05 boundary | reads ONLY `cfg.get("type", "stdio")` | WIRED | `_TRANSPORT_WHITELIST` clamps non-whitelisted values to "stdio"; `.command/.env/.args/.url/.headers` never accessed |
| `codex.py` `_collect_via_toml` | Pitfall G | regex on section header lines only — never `tomllib.loads()` | WIRED | `re.match(r"^\[mcp_servers\.(.*)\]$", line.strip())` — value lines structurally excluded |
| `gemini.py` `_collect_mcp` | Pitfall B | `is_file() and stat().st_size > 0` guard | WIRED | Explicit size check at line 84 |
| `chrome.py` | Phase 13 helpers | `chrome_ext_name`, `version_sort_tail`, `json_get` | WIRED | Imported at module level; used in `_collect_profile` |
| `vscode.py` | Phase 13 helpers | `resolve_vsc_ext_name`, `emit_item` | WIRED | Imported at module level; used in `_collect_editor_extensions` |
| `cursor.py` | `vscode._collect_editor_extensions` | `from maccat.collectors.vscode import _collect_editor_extensions` | WIRED | No logic duplication |

---

### Data-Flow Trace (Level 4)

All 12 collectors are read-only system scanners — they read filesystem paths and run system CLIs; they do not render to a UI or maintain state across calls. Data-flow is: system source → parse → return `CollectorResult(sections=[...])`. Each has been confirmed to return non-empty items on real-data inputs via per-collector unit tests.

| Collector | Data Source | Produces Real Data | Status |
|-----------|-------------|-------------------|--------|
| HomebrewCollector | `brew list --formula/--cask` subprocess | Yes (or fallback message when absent) | FLOWING |
| MasCollector | `mas list` subprocess | Yes (or fallback when absent) | FLOWING |
| SetappCollector | `/Applications/Setapp` filesystem scan | Yes (or fallback when absent) | FLOWING |
| WebAppsCollector | `/Applications` filesystem scan | Yes (always present on macOS) | FLOWING |
| ClaudeCollector | `~/.claude/plugins/`, `~/.claude.json`, `~/.claude/skills/`, `~/.claude/agents/` | Yes (empty CollectorResult when files absent) | FLOWING |
| CodexCollector | `codex mcp list --json` CLI or `~/.codex/config.toml` text-grep | Yes (empty when both absent) | FLOWING |
| OpenCodeCollector | `~/.config/opencode/opencode.json`, `~/.config/opencode/agents/` | Yes (empty when absent) | FLOWING |
| GeminiCollector | `~/.gemini/extensions/`, `~/.gemini/config/mcp_config.json` | Yes (empty when absent) | FLOWING |
| VSCodeCollector | `code --list-extensions --show-versions` or `~/.vscode/extensions/extensions.json` | Yes (empty when absent) | FLOWING |
| CursorCollector | `cursor --list-extensions --show-versions` or `~/.cursor/extensions/extensions.json` | Yes (empty when absent) | FLOWING |
| ChromeCollector | `~/Library/Application Support/Google/Chrome/*/Extensions/` | Yes (empty when Chrome absent) | FLOWING |
| FirefoxCollector | `~/Library/Application Support/Firefox/profiles.ini` + per-profile `extensions.json` | Yes (empty when Firefox absent) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 157 collector tests pass | `PYTHONPATH=src ./venv/bin/pytest tests/collectors/ -q` | 157 passed in 0.53s | PASS |
| Full test suite (351 tests) | `PYTHONPATH=src ./venv/bin/pytest -q` | 351 passed in 1.21s | PASS |
| base.py ABC contract | `from maccat.collectors.base import Collector, Section, CollectorResult; Section(title='T',items=[]).raw is False` | OK | PASS |
| REGISTRY returns 12 collectors / 17 sections in canonical order | `get_registry()` + section title assertion | Exact match to canonical list | PASS |
| mypy --strict on collectors/ | `./venv/bin/mypy --strict src/maccat/collectors/` | Success: no issues found in 14 source files | PASS |
| ruff check on collectors/ | `./venv/bin/ruff check src/maccat/collectors/` | All checks passed | PASS |
| raw=True only on first 4 sections (Homebrew/mas/setapp/web) | Section.raw check on get_registry() output | raw=True for first 4, raw=False for remaining 13 | PASS |

---

### Probe Execution

No probes declared for this phase. Step 7c: SKIPPED (no `scripts/*/tests/probe-*.sh` defined for phase 15).

---

### Requirements Coverage

| Requirement | Phase | Description | Status | Evidence |
|-------------|-------|-------------|--------|---------|
| CAT-01 | Phase 15 | All collectors re-implemented (Homebrew, mas, Setapp, web, 4 AI CLIs, VS Code, Cursor, Chrome, Firefox) | SATISFIED | 12 collector files exist; 12 collector classes in REGISTRY; 157 collector tests pass |
| CAT-05 | Phase 15 | No secrets written — MCP entries emit name + transport only | SATISFIED | 4 MCP collectors read ONLY `.type`; each has `SECRET_PATTERN` test; all tests pass |
| CAT-06 | Phase 15 | Graceful degradation — absent source writes fallback, never aborts | SATISFIED | All 12 collectors handle absent sources; verified by direct invocation and dedicated tests |

---

### Anti-Patterns Found

No debt markers (TBD/FIXME/XXX) found in any file in `src/maccat/collectors/`.

Two `PARITY DEVIATION` comments are present and explicitly documented per-project instructions (intentional, accepted, marked with WR-01/WR-02). These are not gaps.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

---

### Human Verification Required

None. All observable truths are verifiable programmatically for this phase (filesystem/CLI collectors with unit tests).

---

## Gaps Summary

No gaps. All four success criteria are verified:

1. All 12 collectors implemented and exercised end-to-end — confirmed by `get_registry()` instantiation, per-collector unit tests (157 pass), and direct `collect()` invocation.
2. Graceful degradation confirmed for Homebrew, MAS, Setapp, Chrome, Firefox (absent-source paths produce valid `CollectorResult` with fallback items or empty items + stderr NOTE).
3. CAT-05 secret-safety confirmed: all four MCP collectors (Claude, Codex, OpenCode, Gemini) have `SECRET_PATTERN` assertions in tests; source code reads only `.type` from MCP configs.
4. Section order in `get_registry()` matches the canonical 17-section zsh `generate_catalog` order exactly, verified by direct Python assertion.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
