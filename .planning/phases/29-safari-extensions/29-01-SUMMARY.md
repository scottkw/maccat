---
phase: 29-safari-extensions
plan: "01"
subsystem: collectors
tags: [safari, browser-extensions, pluginkit, plistlib, bwr-04]
dependency_graph:
  requires:
    - phases/27-codex-plugins-zed-extensions
    - phases/28-chromium-refactor-edge-brave
  provides:
    - SafariCollector — pluginkit + plistlib Safari extension catalog
  affects:
    - src/maccat/collectors/__init__.py
    - tests/collectors/test_section_titles.py
tech_stack:
  added: []
  patterns:
    - pluginkit subprocess never-raising (mirrors MasCollector)
    - per-extension plistlib.load with individual try/except BLE001
    - CFBundleDisplayName fallback chain (parent app plist, never "safari")
    - module-level constants for monkeypatch discipline
    - live-gated smoke test via pytest.skip
key_files:
  created:
    - src/maccat/collectors/safari.py
    - tests/collectors/test_safari.py
  modified:
    - src/maccat/collectors/__init__.py
    - tests/collectors/test_section_titles.py
decisions:
  - "Used _read_appex_name() as separate module-level helper (not inlined in collect()) for clarity and direct testability"
  - "Worktree was branched from v2.1.0 and missing phases 27+28 base files; synced from main repo as prerequisite chore commit"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-17T21:01:01Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 29 Plan 01: SafariCollector (BRW-04) Summary

SafariCollector via `pluginkit -mAvv -p com.apple.Safari.web-extension` with per-extension plistlib reads, CFBundleDisplayName fallback chain, and live-gated smoke test confirming Bitwarden output.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| Base | Sync phases 27+28 worktree base | 85d08a3 | brave.py, chromium.py, edge.py, zed.py, codex.py, opencode.py + tests |
| 1 | Implement SafariCollector | 390f996 | src/maccat/collectors/safari.py |
| 2 | Tests + registry + section count 22 | e70bd53 | tests/collectors/test_safari.py, src/maccat/collectors/__init__.py, tests/collectors/test_section_titles.py |

## What Was Built

**src/maccat/collectors/safari.py** — SafariCollector implementing BRW-04:
- Module-level constants `_TITLE`, `_PLUGINKIT`, `_PLUGIN_POINT`, `_PATH_RE` at module scope for monkeypatching
- `_parse_pluginkit_output(stdout)` extracts `.appex` paths from `pluginkit -mAvv` verbose output via `_PATH_RE` regex
- `_read_appex_name(appex_path, bundle_id)` resolves CFBundleDisplayName → parent app CFBundleDisplayName → parent app CFBundleName (only if not "safari") → bundle_id
- `SafariCollector.collect()` wraps subprocess in try/except OSError + returncode guard; per-extension plist reads each wrapped in `except Exception: # noqa: BLE001`
- Returns `Section(title="Safari Extensions", items=items)` with `raw=False` (flush_section path)

**tests/collectors/test_safari.py** — 15 tests across 5 classes:
- `TestSafariParsePluginkitOutput`: fixture parse, empty string, no-appex lines
- `TestSafariCollect`: Bitwarden mock collect → correct formatted string, section title, raw=False
- `TestSafariDegradation`: absent pluginkit, non-zero exit, empty stdout, bad plist skipped, OSError
- `TestSafariNameResolution`: display name wins, "safari" bundle name rejected, identifier fallback
- `TestSafariSmoke`: live-gated real pluginkit call (passes on this machine)

**Registry and titles**: SafariCollector registered last (after FirefoxCollector), section count bumped 21→22.

## Verification Results

```
pytest tests/ -q  ->  620 passed, 5 skipped
ruff check (all 4 files)  ->  All checks passed!
mypy --strict (safari.py, __init__.py, test_safari.py)  ->  Success: no issues found
Registry order: Last title = Safari Extensions  (confirmed)
Bitwarden fixture parse: [PosixPath('/Applications/Bitwarden.app/Contents/PlugIns/safari.appex')]  (confirmed)
TestSafariSmoke::test_live_pluginkit_returns_paths_without_raising  ->  PASSED
test_section_titles.py::test_all_section_titles_are_unique  ->  PASSED (22 titles)
test_section_titles.py::test_new_titles_fall_to_manual_checklist  ->  PASSED
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree missing phases 27+28 base files**
- **Found during:** Task 1 pre-check
- **Issue:** Worktree branched from v2.1.0 (pre-Phase 27); missing brave.py, chromium.py, edge.py, zed.py, updated codex.py/opencode.py, and test_section_titles.py — all required for test suite to pass
- **Fix:** Copied missing files from main repo as a prerequisite `chore(29-01)` commit before Task 1
- **Files modified:** 11 files (see chore commit 85d08a3)
- **Commit:** 85d08a3

**2. [Rule 1 - Bug] test_safari.py imported subprocess without using it**
- **Found during:** Task 2 ruff check
- **Fix:** Removed unused `import subprocess` line
- **Files modified:** tests/collectors/test_safari.py

**3. [Rule 1 - Bug] test_section_titles.py import sort violated ruff I001**
- **Found during:** Task 2 ruff check
- **Fix:** Moved `safari_mod` import to alphabetical position (after opencode, before setapp)
- **Files modified:** tests/collectors/test_section_titles.py

## Known Stubs

None — SafariCollector reads live data from `/usr/bin/pluginkit` and `.appex` Info.plist files.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary surfaces beyond the SIP-protected `/usr/bin/pluginkit` subprocess (T-29-01, accepted) and read-only local plist reads (T-29-02, T-29-03, T-29-04, accepted/mitigated per threat model).

## Self-Check: PASSED

- [x] src/maccat/collectors/safari.py exists
- [x] tests/collectors/test_safari.py exists
- [x] Commits 85d08a3, 390f996, e70bd53 all present in git log
- [x] assert len(titles) == 22 in test_section_titles.py
- [x] SafariCollector() in __init__.py return list
