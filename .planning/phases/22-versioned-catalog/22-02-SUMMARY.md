---
plan: 22-02
phase: 22
title: Setapp + WebApps versioned output via plist_version helper
status: complete
requirements: [VER-03, VER-04, VER-05, VER-06]
depends_on: [22-01]

dependency_graph:
  requires:
    - 22-01: src/maccat/helpers/plist_version.py (get_plist_version)
  provides:
    - src/maccat/collectors/setapp.py (versioned Setapp output)
    - src/maccat/collectors/webapps.py (versioned web-installed output)
    - tests/collectors/test_setapp.py (comprehensive versioning + degradation tests)
  affects:
    - catalog output: Setapp and Web-installed sections now emit "name (version)"
    - zsh_parity goldens for Setapp + web-installed (invalidated; to be skipped in 22-03)

tech_stack:
  added: []
  patterns:
    - plist_version helper reuse: both collectors share identical _versioned_entry pattern
    - graceful degradation: name-only when Info.plist absent/unreadable

key_files:
  created: []
  modified:
    - src/maccat/collectors/setapp.py
    - src/maccat/collectors/webapps.py
    - tests/collectors/test_setapp.py

decisions:
  - Inline _versioned_entry() method added to each collector rather than a shared base — keeps collectors self-contained; the shared logic lives in the helper
  - Sort applied AFTER version annotation per VER-06 — sort key is "Name (ver)" string
  - Container/root entries ("Setapp", "Applications") prepended as BASE.name without _versioned_entry call — they are not app bundles
  - plistlib.dumps(FMT_XML) used in test fixtures to avoid raw string fragility

metrics:
  duration: 7 min
  completed: 2026-06-16T15:08:12Z
  tasks_completed: 3
  files_modified: 3
  tests_added: 28
---

# Phase 22 Plan 02: Setapp + WebApps Versioned Output Summary

## One-liner

Setapp and WebApps collectors now emit `name (version)` via the shared `get_plist_version` plist helper, with full graceful degradation and determinism coverage.

## What was built

**`src/maccat/collectors/setapp.py`** (Task 1):
- Imported `get_plist_version` from `maccat.helpers.plist_version`
- Added `_versioned_entry(p: Path) -> str` method: reads `p/Contents/Info.plist` via helper; returns `"name (version)"` if version non-empty, else bare `"name"`
- Container entry `"Setapp"` stays name-only (prepended as `BASE.name`, no `_versioned_entry` call)
- Sort preserved after annotation per VER-06; `raw=True` unchanged
- Module docstring updated to remove byte-parity clause

**`src/maccat/collectors/webapps.py`** (Task 2):
- Same pattern as SetappCollector: `get_plist_version` imported, `_versioned_entry()` added
- Root entry `"Applications"` stays name-only (same rationale)
- `Setapp*` / `*App Store*` filter logic unchanged
- Module docstring updated to remove byte-parity clause

**`tests/collectors/test_setapp.py`** (Task 3):
- Added `_write_plist(app_dir, short_ver, bundle_ver)` fixture helper using `plistlib.dumps(FMT_XML)`
- Updated `TestSetappCollector` (6 tests): fixtures now create `Info.plist` where versioned assertions exist
- Updated `TestWebAppsCollector` (8 tests): same fixture pattern
- Added `TestSetappVersioning` (7 tests): `CFBundleShortVersionString`, `CFBundleVersion` fallback, missing plist degradation, container name-only, determinism, zero-byte plist, sort-after-annotation
- Added `TestWebAppsVersioning` (7 tests): same coverage plus corrupt/garbage plist degradation
- **Total: 28 tests, all passing**

## Requirements satisfied

- VER-03: SetappCollector emits `name (version)` for readable Info.plist
- VER-04: WebAppsCollector emits `name (version)` for readable Info.plist
- VER-05: Container/root entries and missing/corrupt plists degrade to name-only without error
- VER-06: Sort preserved after annotation; two consecutive runs return identical items

## Verification

```
tests/collectors/test_setapp.py: 28 passed
ruff check src/maccat/collectors/setapp.py src/maccat/collectors/webapps.py tests/collectors/test_setapp.py: clean
mypy --strict src/maccat/collectors/setapp.py src/maccat/collectors/webapps.py: clean (no issues)
grep get_plist_version setapp.py: PASS
grep get_plist_version webapps.py: PASS
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | c898845 | feat(22-02): versioned output in SetappCollector via plist_version helper |
| 2    | 55e625d | feat(22-02): versioned output in WebAppsCollector via plist_version helper |
| 3    | abe1d9f | test(22-02): update test_setapp.py for versioned output + degradation paths |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new threat surface introduced. All plist reads are read-only; errors caught by `get_plist_version`; version strings are plain public app metadata written to text catalog.

## Self-Check: PASSED

Files exist:
- src/maccat/collectors/setapp.py: FOUND
- src/maccat/collectors/webapps.py: FOUND
- tests/collectors/test_setapp.py: FOUND

Commits exist:
- c898845: FOUND
- 55e625d: FOUND
- abe1d9f: FOUND
