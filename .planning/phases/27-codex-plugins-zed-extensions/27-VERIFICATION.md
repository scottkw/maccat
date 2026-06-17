---
phase: 27-codex-plugins-zed-extensions
verified: 2026-06-17T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 27: Codex Plugins + Zed Extensions Verification Report

**Phase Goal:** The catalog captures Codex plugins and Zed extensions as two independent new sections
**Verified:** 2026-06-17
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A generated catalog includes a "Codex Plugins" section immediately after "Codex MCP Servers"; on Codex v0.46.0 the section emits `(none found)` — not an error, not missing | VERIFIED | Registry live-run: `Codex Plugins @ 8, immediately after Codex MCP Servers @ 7`. Test `test_plugins_absent_both_paths_items_empty` passes with `sections[1].items == []`. 580 tests pass. |
| 2 | A generated catalog includes a "Zed Extensions" section listing each non-dev extension as `name (version) [id]`; `dev: true` excluded; `(none found)` when Zed absent | VERIFIED | `zed.py` parses `index.json`, filters `info.get("dev")`, calls `emit_item(name, version, ext_id)`. `test_zed_collects_extension_name_version_id` asserts `items[0] == "HTML (0.3.1) [html]"`. `test_zed_excludes_dev_extensions` passes. `test_zed_absent_index_returns_empty` passes with `items == []`. |
| 3 | Both new sections appear in reinstall output as manual-checklist items only (no auto-install) — zero changes to reinstall/parser.py or emitter.py | VERIFIED | `SECTION_SOURCE_MAP` in `emitter.py` has exactly 4 keys (Homebrew, App Store, VS Code, Cursor) — neither "Codex Plugins" nor "Zed Extensions" present. `test_new_titles_fall_to_manual_checklist` passes, asserting `=== Manual Checklist ===` appears and no `mas install` command emitted. Phase 27 commits do not include `parser.py` or `emitter.py`. |
| 4 | A section-title uniqueness test asserts all collector title constants are unique — passes for all 19 titles (17 existing + 2 new) | VERIFIED | `test_all_section_titles_are_unique` in `test_section_titles.py` collects all 19 title constants, asserts `len(titles) == 19` and `len(titles) == len(set(titles))`. Test passes. |
| 5 | New sections honor FMT-01 (name (version) [id] + graceful degradation), FMT-03 (identity-only Codex — never reads .mcp.json), FMT-04 (deterministic stable sort); stdlib-only | VERIFIED | No `tomllib` import in `codex.py` (all 4 occurrences are in docstrings/comments). No `.mcp.json` file reads (all 3 occurrences are in docstring/comments). All `return []` paths are in graceful-degradation error handlers (OSError, JSONDecodeError, non-zero exit). No new pip dependencies added. mypy strict passes on both files. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/collectors/codex.py` | Extended CodexCollector with `_collect_mcp()` + `_collect_plugins()` + 2-section `collect()` | VERIFIED | `_PLUGINS_TITLE = "Codex Plugins"` at module level (line 26). `_collect_mcp()` returns `Section`. `_collect_plugins()` returns `Section`. `collect()` returns `CollectorResult(sections=[self._collect_mcp(), self._collect_plugins()])`. 245 lines, substantive. |
| `src/maccat/collectors/zed.py` | ZedCollector parsing index.json, dev-filter, emit_item, graceful degradation | VERIFIED | `_INDEX` and `_TITLE = "Zed Extensions"` at module level. `collect()` checks `_INDEX.is_file()`, wraps JSON parse in try/except, filters `dev`, calls `emit_item`. 71 lines, substantive. |
| `src/maccat/collectors/__init__.py` | Updated get_registry() with ZedCollector after CursorCollector | VERIFIED | `ZedCollector` imported and inserted between `CursorCollector()` and `ChromeCollector()`. Docstring updated to "19 sections from 13 collectors". |
| `tests/collectors/test_codex.py` | Tests for new plugins section — present-mocked AND absent → items == [] | VERIFIED | `TestCodexPluginsSection` class with 7 test methods covering: absent paths (items == []), TOML quoted id, CAT-05 regression (no value lines), unquoted barename, title constant check, section count stability when CLI non-zero, CLI JSON parse. |
| `tests/collectors/test_zed.py` | Full behavioral spec — present, absent, malformed, dev-filter, missing fields | VERIFIED | 3 test classes, 11 methods: section count/title, name/version/id format, dev-filter include/exclude, absent index, NOTE to stderr, malformed JSON, non-object JSON (5 payloads parametrized), missing manifest, non-dict entry, empty extensions. |
| `tests/collectors/test_section_titles.py` | Uniqueness assertion for all 19 section titles; reinstall passthrough assertion | VERIFIED | `test_all_section_titles_are_unique` (19 titles, len == set check) and `test_new_titles_fall_to_manual_checklist` (ParsedCatalog with both new sections, checks Manual Checklist header present, no `mas install`). Both pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `codex.py::collect()` | `_collect_mcp()` and `_collect_plugins()` | `CollectorResult(sections=[self._collect_mcp(), self._collect_plugins()])` | WIRED | Lines 236-240 of codex.py match exactly. |
| `_collect_plugins` TOML path | `~/.codex/config.toml` | `re.match(r'^\[plugins\."?([^"\]]+)"?\]$', line.strip())` | WIRED | `_collect_plugins_via_toml` at lines 177-201 uses the exact regex on `_TOML_PATH.read_text()`. |
| `zed.py::collect()` | `_INDEX` (Path) | `_INDEX.is_file()` check before json parse | WIRED | Line 38 of zed.py: `if not _INDEX.is_file():` → degrade. Line 43: `json.loads(_INDEX.read_text(...))`. |
| `test_section_titles.py` | all 19 title constants | direct module imports + `len(titles) == len(set(titles))` | WIRED | All 19 constants imported at lines 57-75 and collected into `titles` list. Assert fires with exact count. |
| `__init__.py::get_registry()` | ZedCollector | import + `ZedCollector()` after `CursorCollector()` | WIRED | Line 56: `from maccat.collectors.zed import ZedCollector`. Line 71: `ZedCollector(),` appears after `CursorCollector()` on line 70. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `codex.py::_collect_plugins_via_toml` | `items: list[str]` | `_TOML_PATH.read_text()` → regex match on `[plugins.*]` headers | Yes — reads live TOML file, regex extracts plugin ids | FLOWING |
| `zed.py::collect` | `items: list[str]` | `_INDEX.read_text()` → `json.loads()` → `data.get("extensions", {})` | Yes — reads live index.json, iterates entries | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| "Codex Plugins" immediately after "Codex MCP Servers" in registry | `from maccat.collectors import get_registry; ... ci=7, pi=8, adjacent=True` | adjacent: True | PASS |
| "Zed Extensions" after CursorCollector, before ChromeCollector | `zi=16, cursor=15, chrome=17` | Both ordering constraints satisfied | PASS |
| Total section count is 19 | `len(titles) == 19` | 19 | PASS |
| Full test suite passes (580 tests, no regressions) | `./venv/bin/python -m pytest -q` | 580 passed | PASS |
| Phase-specific tests pass (41 tests) | `pytest test_codex.py test_zed.py test_section_titles.py -q` | 41 passed in 0.62s | PASS |
| Ruff lint clean | `ruff check src/maccat/collectors/codex.py zed.py __init__.py tests/...` | All checks passed | PASS |
| mypy strict clean | `mypy --strict src/maccat/collectors/codex.py zed.py` | Success: no issues found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CDX-02 | 27-01-PLAN.md | Catalog Codex plugins as "Codex Plugins" section; identity-only, never reads .mcp.json, degrades on v0.46.0 | SATISFIED | `_collect_plugins()` in codex.py implements CLI-then-TOML-header-grep. No tomllib, no .mcp.json. items == [] on v0.46.0 confirmed by test. |
| BRW-03 | 27-02-PLAN.md | Catalog Zed installed extensions from index.json; dev: true filtered; degrades when absent | SATISFIED | `ZedCollector` in zed.py reads index.json, filters `info.get("dev")`, returns empty section on absent/malformed. |

### Anti-Patterns Found

No anti-pattern blockers. All `return []` occurrences in codex.py and zed.py are in explicit error-handling paths (OSError, JSONDecodeError, non-zero subprocess exit, non-dict guards) — not stub placeholders. No TBD/FIXME/XXX markers in any phase 27 file.

### Human Verification Required

None. All success criteria are mechanically verifiable and confirmed via test execution and live registry output.

---

_Verified: 2026-06-17_
_Verifier: Claude (gsd-verifier)_
