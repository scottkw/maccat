---
phase: "27"
plan: "02"
subsystem: collectors
tags: [zed, extensions, catalog, brw-03, section-titles, reinstall, uniqueness-guard]
dependency_graph:
  requires: [27-01]
  provides: [ZedCollector, test_zed, test_section_titles, opencode_title_constants]
  affects:
    - src/maccat/collectors/zed.py
    - src/maccat/collectors/__init__.py
    - src/maccat/collectors/opencode.py
    - tests/collectors/test_zed.py
    - tests/collectors/test_section_titles.py
tech_stack:
  added: []
  patterns: [single-section-json-file-collector, module-level-constants-for-monkeypatching,
             dev-filter, graceful-degradation-never-raises, uniqueness-guard-test]
key_files:
  created:
    - src/maccat/collectors/zed.py
    - tests/collectors/test_zed.py
    - tests/collectors/test_section_titles.py
  modified:
    - src/maccat/collectors/__init__.py
    - src/maccat/collectors/opencode.py
decisions:
  - "ZedCollector follows firefox.py pattern exactly: module-level _INDEX + _TITLE, single collect() method"
  - "opencode.py received module-level _PLUGINS_TITLE, _MCP_TITLE, _AGENTS_TITLE constants (was inline) for uniqueness test"
  - "test_section_titles.py placed in tests/collectors/ — co-located with collector tests it guards"
  - "Worktree merged from Plan 01 base (a726698) before execution — Plan 01 codex.py changes present"
metrics:
  duration: "6m"
  completed: "2026-06-17"
  tasks: 2
  files_modified: 2
  files_created: 3
  tests_added: 13
  tests_total: 34
---

# Phase 27 Plan 02: Zed Extensions Collector + Section-Title Uniqueness Guard Summary

**One-liner:** ZedCollector reads Zed's index.json with dev-filter and graceful degradation; section-title uniqueness test asserts all 19 titles are unique and both new titles fall to reinstall manual checklist automatically.

## What Was Built

### 1. `src/maccat/collectors/zed.py` (created)
New single-section collector for Zed extensions:
- Module-level `_INDEX = Path.home() / "Library/Application Support/Zed/extensions/index.json"` (patchable)
- Module-level `_TITLE = "Zed Extensions"` (patchable)
- `ZedCollector.collect()` reads index.json, iterates `data.get("extensions", {})`, excludes `dev:true` entries (BRW-03), formats each entry as `name (version) [id]` via `emit_item`
- Graceful degradation: absent index → NOTE to stderr + empty Section; malformed JSON → empty Section; non-dict entry → skip and continue
- Returns exactly 1 `CollectorResult` with 1 `Section`

### 2. `src/maccat/collectors/__init__.py` (modified)
- Added `from maccat.collectors.zed import ZedCollector` to `get_registry()` imports
- Inserted `ZedCollector()` after `CursorCollector()` and before `ChromeCollector()`
- Updated docstring from "17 sections from 12 collectors" to "19 sections from 13 collectors"
- Added sections 9 (Codex Plugins), 17 (Zed Extensions) to section list; renumbered Chrome/Firefox
- Updated CodexCollector comment from "1 section" to "2 sections: MCP Servers, Plugins"

### 3. `src/maccat/collectors/opencode.py` (modified — deviation)
Added module-level section title constants (was inline `title = "..."` local variables):
- `_PLUGINS_TITLE = "OpenCode Plugins"`
- `_MCP_TITLE = "OpenCode MCP Servers"`
- `_AGENTS_TITLE = "OpenCode Agents"`
Updated the three `_collect_*` sub-methods to reference these constants. Required by the uniqueness test to import OpenCode titles without collector instantiation.

### 4. `tests/collectors/test_zed.py` (created, 11 tests)
Full behavioral spec for ZedCollector across 3 test classes:
- `TestZedCollect`: section count, title, name/version/id format (3 tests)
- `TestZedDevFilter`: excludes dev=True, includes dev absent (2 tests)
- `TestZedDegradation`: absent index (items=[] + NOTE), malformed JSON, missing manifest (ext_id fallback), non-dict entry skip, empty extensions object (6 tests)

### 5. `tests/collectors/test_section_titles.py` (created, 2 tests)
Phase-persistent uniqueness guard reused by Phases 28 and 29:
- `test_all_section_titles_are_unique`: imports all 19 title constants from all collector modules, asserts `len(titles) == 19` and `len(titles) == len(set(titles))`
- `test_new_titles_fall_to_manual_checklist`: builds a minimal `ParsedCatalog` with "Codex Plugins" and "Zed Extensions" sections, calls `emit_reinstall_script`, asserts both titles appear in manual checklist output and `mas install` is absent

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Create zed.py + register ZedCollector; add opencode title constants | Done | 1e068f6 |
| 2 | Create test_zed.py + test_section_titles.py | Done | 7d80eaa |

## Verification Results

```
PYTHONPATH=src ./venv/bin/python -m pytest tests/collectors/test_codex.py tests/collectors/test_zed.py tests/collectors/test_section_titles.py -q
34 passed in 0.26s

PYTHONPATH=src ./venv/bin/ruff check src/maccat/collectors/codex.py src/maccat/collectors/zed.py src/maccat/collectors/__init__.py tests/collectors/test_zed.py tests/collectors/test_section_titles.py
All checks passed!

PYTHONPATH=src ./venv/bin/mypy --strict src/maccat/collectors/codex.py src/maccat/collectors/zed.py
Success: no issues found in 2 source files
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added module-level title constants to opencode.py**
- **Found during:** Task 1 (before writing test_section_titles.py)
- **Issue:** `opencode.py` used inline `title = "..."` local variables in each `_collect_*` sub-method. No module-level constants existed. The uniqueness test must import all 19 titles from module constants — it cannot instantiate collectors and run collect() in test_section_titles.py.
- **Fix:** Added `_PLUGINS_TITLE`, `_MCP_TITLE`, `_AGENTS_TITLE` as module-level constants (consistent with codex.py, gemini.py, zed.py patterns). Updated the three sub-methods to reference them. Plan checker note acknowledged this was the preferred approach.
- **Files modified:** `src/maccat/collectors/opencode.py`
- **Commit:** 1e068f6

**2. [Rule 3 - Blocking issue] Merged Plan 01 base changes into worktree before execution**
- **Found during:** Pre-execution context check
- **Issue:** This worktree was spawned from `aab794b` (before Plan 01 commits). Plan 01's `codex._PLUGINS_TITLE` constant (required for uniqueness test) was not present on disk. The parallel execution note said "This worktree includes the Phase 27-01 Codex change" — this was the intended state.
- **Fix:** Fast-forward merged `a726698` (merged Plan 01 base) into this worktree branch via `git merge a726698 --no-edit`.
- **Commit:** Fast-forward merge (no new commit — worktree branch advanced to a726698 + new work)

## Known Stubs

None — ZedCollector is fully wired. When Zed is not installed or index.json is absent, `items == []` triggers `flush_section → "(none found)"`, which is the correct and expected output (not a stub).

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covers. ZedCollector reads only a local user-owned file (index.json); all T-27-04, T-27-05, T-27-06 mitigations implemented as specified.

## Self-Check: PASSED

- [x] `src/maccat/collectors/zed.py` exists with `_INDEX`, `_TITLE`, `ZedCollector`
- [x] `src/maccat/collectors/__init__.py` has `ZedCollector` import and usage after `CursorCollector()`
- [x] `src/maccat/collectors/opencode.py` has `_PLUGINS_TITLE`, `_MCP_TITLE`, `_AGENTS_TITLE`
- [x] `tests/collectors/test_zed.py` exists with 11 test methods
- [x] `tests/collectors/test_section_titles.py` exists with 2 test functions
- [x] Commit 1e068f6 exists (Task 1)
- [x] Commit 7d80eaa exists (Task 2)
- [x] 34 tests pass; ruff clean; mypy --strict clean on src files
