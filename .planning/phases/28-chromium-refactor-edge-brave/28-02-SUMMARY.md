---
phase: 28-chromium-refactor-edge-brave
plan: "02"
subsystem: collectors
tags: [edge, brave, chromium, tdd, extensions, browser]
dependency_graph:
  requires: [28-01]
  provides: [EdgeCollector, BraveCollector, EDGE_COMPONENT_DENYLIST, BRAVE_COMPONENT_DENYLIST]
  affects: [collectors/__init__.py, test_section_titles.py]
tech_stack:
  added: []
  patterns: [thin-subclass, class-attribute-parameterization, profile-enumeration-presence-detection]
key_files:
  created:
    - src/maccat/collectors/edge.py
    - src/maccat/collectors/brave.py
    - tests/collectors/test_edge.py
    - tests/collectors/test_brave.py
  modified:
    - src/maccat/collectors/__init__.py
    - tests/collectors/test_section_titles.py
decisions:
  - "EDGE_COMPONENT_DENYLIST ships empty; comment documents the known gap (Microsoft has no canonical list); COMPONENT_DENYLIST baseline still applied via union"
  - "BRAVE_COMPONENT_DENYLIST contains exactly 20 confirmed IDs from brave-browser wiki"
  - "Profile-enumeration presence detection: NOTE fires only when base dir is missing, not when it exists with only NativeMessagingHosts"
metrics:
  duration: "~25 minutes"
  completed: "2026-06-17"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 28 Plan 02: Edge and Brave Collectors Summary

**One-liner:** EdgeCollector and BraveCollector as thin ChromiumBaseCollector subclasses with profile-enumeration presence detection and documented denylists (EDGE empty/gap-documented, BRAVE 20 IDs).

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED  | Failing tests for EdgeCollector + BraveCollector | 4c89f7e | tests/collectors/test_edge.py, tests/collectors/test_brave.py |
| 1 GREEN | EdgeCollector + BraveCollector implementation | 09eb46c | src/maccat/collectors/edge.py, src/maccat/collectors/brave.py |
| 2 | Registry update + section-title count 19→21 | 587b990 | src/maccat/collectors/__init__.py, tests/collectors/test_section_titles.py |

## What Was Built

**edge.py** — `EdgeCollector(ChromiumBaseCollector)` with:
- `_base = ~/Library/Application Support/Microsoft Edge`
- `_title = "Microsoft Edge Extensions"` (also exposed as module-level `_TITLE`)
- `_denylist = COMPONENT_DENYLIST | EDGE_COMPONENT_DENYLIST` (EDGE_COMPONENT_DENYLIST starts empty)
- `_browser_name = "Microsoft Edge"`
- Documented gap: Microsoft publishes no canonical component-ID list; comment on `EDGE_COMPONENT_DENYLIST` instructs how to expand it after a real Edge install

**brave.py** — `BraveCollector(ChromiumBaseCollector)` with:
- `_base = ~/Library/Application Support/BraveSoftware/Brave-Browser`
- `_title = "Brave Browser Extensions"` (also exposed as module-level `_TITLE`)
- `_denylist = COMPONENT_DENYLIST | BRAVE_COMPONENT_DENYLIST` (20 confirmed IDs from Brave Components wiki)
- `_browser_name = "Brave Browser"`

**Registry** — `get_registry()` now returns `[..., ChromeCollector(), EdgeCollector(), BraveCollector(), FirefoxCollector()]` (Chrome → Edge → Brave → Firefox order).

**Section-title uniqueness** — `test_section_titles.py` now asserts 21 unique titles (was 19).

## Test Coverage

43 tests pass across 4 test files:
- `test_edge.py` (15 tests): TestEdgeCollect, TestEdgeExclusions, TestEdgeDegradation, TestEdgeNativeMessagingOnly, module-level constant checks
- `test_brave.py` (17 tests): TestBraveCollect, TestBraveExclusions, TestBraveDegradation, TestBraveNativeMessagingOnly, module-level constant checks including `len(BRAVE_COMPONENT_DENYLIST) == 20`
- `test_chrome.py` (11 tests): unmodified, regression clean
- `test_section_titles.py` (2 tests): 21-title uniqueness + manual-checklist fallthrough

**NativeMessagingHosts-only fixture** (key test in both files): confirms the profile-enumeration presence-detection rule — a base dir that exists but contains only `NativeMessagingHosts/` (no `Extensions/` dirs inside any profile) returns `items=[]` silently with no NOTE in stderr. This prevents spurious output when the browser is not truly installed but left residual directories.

## Static Analysis

- `mypy --strict` on all 5 source files: no issues
- `ruff check` on all 8 source/test files: all checks passed

## Deviations from Plan

None — plan executed exactly as written. The merge of 28-01 commits into this worktree was required setup (the worktree forked before those commits existed on the branch).

## Known Stubs

None.

## Threat Flags

None. Both collectors follow the same trust model as ChromeCollector: read-only access to own profile directory, manifest.json fields obtained via `json_get` (returns empty string on missing/invalid fields), and the NativeMessagingHosts-only case degrades silently per T-28B-03.

## Self-Check: PASSED

Files created:
- src/maccat/collectors/edge.py — FOUND
- src/maccat/collectors/brave.py — FOUND
- tests/collectors/test_edge.py — FOUND
- tests/collectors/test_brave.py — FOUND

Commits:
- 4c89f7e (test RED) — FOUND
- 09eb46c (feat GREEN) — FOUND
- 587b990 (feat registry + titles) — FOUND
