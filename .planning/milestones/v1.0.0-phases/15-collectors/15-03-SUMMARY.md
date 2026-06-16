---
phase: 15-collectors
plan: "03"
subsystem: collectors
tags: [setapp, webapps, filesystem, raw-write, pitfall-c]
dependency_graph:
  requires: [15-01]
  provides: [SetappCollector, WebAppsCollector]
  affects: [src/maccat/collectors/__init__.py, Phase 16 orchestrator]
tech_stack:
  added: []
  patterns: [tmp_path filesystem fixture, class-per-behavior test pattern, Pitfall-C root-basename prepend]
key_files:
  created:
    - src/maccat/collectors/setapp.py
    - src/maccat/collectors/webapps.py
    - tests/collectors/test_setapp.py
  modified: []
decisions:
  - "Sorted with Python sorted() not subprocess — zsh uses plain sort (not LC_ALL=C sort -f -u); matches spec"
  - "WebAppsCollector does not override available() — base class default True matches zsh (no guard)"
  - "SetappCollector.BASE and WebAppsCollector.BASE are class attributes for patch.object testability"
metrics:
  duration_minutes: 2
  completed_date: "2026-06-15"
  tasks_completed: 2
  files_changed: 3
---

# Phase 15 Plan 03: Setapp + Web-installed Collectors Summary

Implemented SetappCollector and WebAppsCollector — the two filesystem-only raw-write collectors
for Setapp applications and web-installed Applications.

## What Was Built

**SetappCollector** (`src/maccat/collectors/setapp.py`): Scans `/Applications/Setapp/` with
Pitfall-C fix (prepends `"Setapp"` root basename before `iterdir()` results). Returns
`Section(raw=True)`. Absent-dir fallback: `["Setapp is not installed or detected."]`.

**WebAppsCollector** (`src/maccat/collectors/webapps.py`): Scans `/Applications/` with fnmatch
exclusions for `Setapp*` and `*App Store*` directories, plus Pitfall-C root-basename prepend
(`"Applications"`). Always available — no `available()` override. Returns `Section(raw=True)`.

**Unit tests** (`tests/collectors/test_setapp.py`): 14 tests across `TestSetappCollector` and
`TestWebAppsCollector`. All use `tmp_path` filesystem fixtures — CI-safe, never accesses real
`/Applications`. Pitfall-C tests explicitly verify root entries present.

## Tasks

| Task | Description | Commit |
|------|-------------|--------|
| 1 | SetappCollector + WebAppsCollector implementation | 2f66c61 |
| 2 | Unit tests (14 tests, tmp_path fixtures) | f4f0752 |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both collectors are fully wired filesystem implementations.

## Threat Flags

None — read-only directory listing; no new network endpoints or auth paths introduced.

## Self-Check

- [x] `src/maccat/collectors/setapp.py` exists
- [x] `src/maccat/collectors/webapps.py` exists
- [x] `tests/collectors/test_setapp.py` exists
- [x] Commit 2f66c61 exists (Task 1)
- [x] Commit f4f0752 exists (Task 2)
- [x] 217 tests passing (full suite)
- [x] ruff + mypy --strict clean on all 3 files

## Self-Check: PASSED
