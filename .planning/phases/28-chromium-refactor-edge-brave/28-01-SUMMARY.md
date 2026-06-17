---
phase: 28-chromium-refactor-edge-brave
plan: "01"
subsystem: collectors
tags: [refactor, chromium, chrome, base-class, tdd]
dependency_graph:
  requires: []
  provides: [ChromiumBaseCollector, COMPONENT_DENYLIST]
  affects: [src/maccat/collectors/chrome.py, tests/collectors/test_chrome.py]
tech_stack:
  added: []
  patterns: [class-attribute parameterization, thin-subclass, re-export for backward compat]
key_files:
  created:
    - src/maccat/collectors/chromium.py
  modified:
    - src/maccat/collectors/chrome.py
    - tests/collectors/test_chrome.py
decisions:
  - "Added _browser_name class attribute to ChromiumBaseCollector for precise NOTE messages"
  - "Removed unused chrome_mod import from test_chrome.py after patch target migration"
metrics:
  duration: ~8 minutes
  completed: 2026-06-17
---

# Phase 28 Plan 01: Chromium Base Class Extraction Summary

**One-liner:** Extracted ChromiumBaseCollector from chrome.py into chromium.py; Chrome is now a thin 4-attribute subclass with byte-identical output.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create chromium.py with ChromiumBaseCollector | 62464de | src/maccat/collectors/chromium.py |
| 2 | Refactor chrome.py + migrate test patch targets | 0593167 | src/maccat/collectors/chrome.py, tests/collectors/test_chrome.py |

## What Was Built

**chromium.py** — new base class module:
- `COMPONENT_DENYLIST` (frozenset of 10 IDs) moved verbatim from chrome.py
- `ChromiumBaseCollector(Collector)` with class attributes `_base: Path`, `_title: str`, `_denylist: frozenset[str]`, `_browser_name: str`
- Full `_collect_profile()` logic (both OSError guards, Temp/underscore/denylist skips, version_sort_tail)
- Full `collect()` logic (presence check, profile enumeration, Default + Profile * pattern, raw=False)
- `_collect_profile` uses `self._denylist` (not module-level constant) for correct subclass parameterization

**chrome.py** — reduced from 104 lines to 25 lines:
- Imports `ChromiumBaseCollector` and `COMPONENT_DENYLIST` from chromium.py
- `__all__` re-exports `COMPONENT_DENYLIST` for backward compatibility
- `ChromeCollector` overrides `_base`, `_title`, `_denylist`, `_browser_name` only
- `_BASE` and `_TITLE` module constants preserved (test_section_titles.py accesses `_TITLE`)

**test_chrome.py** — patch target migration:
- All 9 `patch.object(chrome_mod, "_BASE", base)` calls migrated to `patch.object(ChromeCollector, "_base", new=base)`
- Removed now-unused `import maccat.collectors.chrome as chrome_mod`
- All 11 tests pass

## Verification Results

```
PYTHONPATH=src ./venv/bin/python -m pytest tests/collectors/test_chrome.py -v
  11 passed in 0.08s

PYTHONPATH=src ./venv/bin/ruff check src/maccat/collectors/chromium.py src/maccat/collectors/chrome.py tests/collectors/test_chrome.py
  All checks passed!

MYPYPATH=src ./venv/bin/mypy --strict src/maccat/collectors/chromium.py src/maccat/collectors/chrome.py
  Success: no issues found in 2 source files
```

Chrome byte-parity gate: PASSED — all section title, items format, raw=False, and NOTE/stderr tests green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused chrome_mod import**
- **Found during:** Task 2 ruff check
- **Issue:** After migrating all patch targets from `chrome_mod._BASE` to `ChromeCollector._base`, the `import maccat.collectors.chrome as chrome_mod` became unused, causing ruff F401
- **Fix:** Removed the import line
- **Files modified:** tests/collectors/test_chrome.py
- **Commit:** 0593167

## Known Stubs

None.

## Threat Flags

None — stdlib-only refactor; no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- [x] src/maccat/collectors/chromium.py exists
- [x] src/maccat/collectors/chrome.py is ~25 lines (thin subclass)
- [x] tests/collectors/test_chrome.py has no `patch.object(chrome_mod, "_BASE"` occurrences
- [x] Commits 62464de and 0593167 exist in git log
- [x] 11/11 tests pass; ruff + mypy --strict clean
