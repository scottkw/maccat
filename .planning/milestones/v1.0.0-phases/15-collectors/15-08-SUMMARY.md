---
phase: 15-collectors
plan: "08"
subsystem: collectors
tags: [chrome, firefox, browser-extensions, multi-profile, version-sort, crlf]
dependency_graph:
  requires:
    - 15-01  # base.py: Collector, CollectorResult, Section
    - 13-01  # format.py: emit_item, version_sort_tail, flush_section
    - 13-02  # helpers: chrome_name.py, json_io.py
  provides:
    - src/maccat/collectors/chrome.py
    - src/maccat/collectors/firefox.py
  affects:
    - src/maccat/collectors/__init__.py  # get_registry() now resolves all 12 collectors
tech_stack:
  added: []
  patterns:
    - "module-level _BASE/_FF_DIR constants (not class attrs) for monkeypatching"
    - "version_sort_tail subprocess sort -V for Chrome version dir selection"
    - "splitlines() not split('\\n') for CRLF-safe profiles.ini parsing (Pitfall E)"
    - "app-profile location filter for Firefox extensions.json"
    - "cross-profile item accumulation; flush_section dedup by Phase 16 orchestrator"
key_files:
  created:
    - src/maccat/collectors/chrome.py
    - src/maccat/collectors/firefox.py
    - tests/collectors/test_chrome.py
    - tests/collectors/test_firefox.py
  modified: []
decisions:
  - "COMPONENT_DENYLIST is a module-level frozenset constant (10 IDs) — never a file, never an env var"
  - "Chrome profile enumeration: Default first, then sorted(glob('Profile */')) for determinism"
  - "Firefox _get_profile_paths uses splitlines() for CRLF safety (Pitfall E mitigation)"
  - "Both collectors raw=False — Phase 16 orchestrator calls flush_section once for cross-profile dedup"
metrics:
  duration_minutes: 3
  completed_date: "2026-06-15"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
---

# Phase 15 Plan 08: ChromeCollector + FirefoxCollector Summary

**One-liner:** Multi-profile Chrome and Firefox extension collectors with component denylist, sort -V version selection, CRLF-safe profiles.ini parsing, and app-profile location filter.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ChromeCollector and FirefoxCollector | 9b533aa | chrome.py, firefox.py |
| 2 | Unit tests for ChromeCollector and FirefoxCollector | 48e14dd | test_chrome.py, test_firefox.py |

## What Was Built

### ChromeCollector (`src/maccat/collectors/chrome.py`)

Implements multi-profile Chrome extension collection at byte-parity with `update-list.sh:2074` (`collect_chrome_extensions`):

- **Profile enumeration:** `Default` profile first, then `sorted(glob("Profile */"))` for determinism — mirrors zsh `:2089` ordering
- **COMPONENT_DENYLIST:** `frozenset` of 10 component extension IDs pre-installed by Chrome (inline constant; never a file)
- **Skipped entries:** directories named `Temp`, starting with `_` (e.g. `_metadata`), or in the denylist
- **Version directory selection:** `version_sort_tail(candidates)` — Phase 13 helper using `sort -V | tail -1` subprocess; never Python `sorted()`
- **Name resolution:** `chrome_ext_name(manifest)` — Phase 13 helper resolving `__MSG_key__` via `_locales` NLS lookup
- **Version extraction:** `json_get(manifest, "version")` — Phase 13 helper
- **Cross-profile dedup:** `raw=False`; items accumulated across all profiles; `flush_section` called once by Phase 16 orchestrator

### FirefoxCollector (`src/maccat/collectors/firefox.py`)

Implements multi-profile Firefox extension collection at byte-parity with `update-list.sh:2154` (`collect_firefox_extensions`):

- **Profile discovery:** `_get_profile_paths()` reads `profiles.ini`, extracts `Path=` values using `.splitlines()` (not `.split("\n")`) — CRLF safety for Pitfall E
- **Extension parse:** `extensions.json` per profile; only `location == "app-profile"` entries included (excludes `app-builtin`, `app-builtin-addons`)
- **Name fallback:** `defaultLocale.name` → fallback to `id_` if absent/null
- **ID guard:** skips addons with empty id or `id == "null"`
- **Cross-profile dedup:** `raw=False`; items accumulated; `flush_section` by Phase 16 orchestrator

### Tests

**test_chrome.py** (9 behaviors):
- `test_collects_default_profile`, `test_collects_multiple_profiles`
- `test_skips_component_extension`, `test_skips_temp_directory`, `test_skips_underscore_directory`
- `test_version_sort_tail_used` — creates two version dirs (1.0.0_0 and 2.0.0_0); asserts higher selected
- `test_chrome_not_installed` (CAT-06), `test_chrome_section_title`, `test_chrome_raw_is_false`

**test_firefox.py** (10 behaviors):
- `test_collects_from_profile`, `test_firefox_section_title`, `test_firefox_raw_is_false`
- `test_location_filter_excludes_app_builtin`, `test_location_filter_includes_only_app_profile`
- `test_null_id_skipped`, `test_name_fallback_to_id`
- `test_crlf_path_handling` — writes `\r\n` bytes; verifies path resolves without `\r`
- `test_cross_profile_dedup` — two profiles with same addon; verifies accumulation
- `test_firefox_not_installed` (CAT-06)

All fixtures use `tmp_path` — never real `~/Library/Application Support/Google/Chrome` or `~/Library/Application Support/Firefox`.

## Integration Check

`get_registry()` now imports all 12 collectors cleanly:

```
registry len 12
collector types: ['HomebrewCollector', 'MasCollector', 'SetappCollector', 'WebAppsCollector',
  'ClaudeCollector', 'CodexCollector', 'OpenCodeCollector', 'GeminiCollector',
  'VSCodeCollector', 'CursorCollector', 'ChromeCollector', 'FirefoxCollector']
```

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **New tests:** 19 passed (test_chrome.py + test_firefox.py)
- **Full suite:** 333 passed in 1.23s
- **ruff:** clean on all 4 files
- **mypy --strict src/maccat:** 1 known error only (`src/maccat/__main__.py:20` — Phase-16 `maccat.cli` stub)

## Known Stubs

None.

## Threat Flags

No new threat surface introduced beyond plan scope.

## Self-Check: PASSED

- [x] `src/maccat/collectors/chrome.py` exists (commit 9b533aa)
- [x] `src/maccat/collectors/firefox.py` exists (commit 9b533aa)
- [x] `tests/collectors/test_chrome.py` exists (commit 48e14dd)
- [x] `tests/collectors/test_firefox.py` exists (commit 48e14dd)
- [x] `get_registry()` returns 12 collectors
- [x] 333 tests pass; mypy --strict clean except known __main__.py:20 stub
