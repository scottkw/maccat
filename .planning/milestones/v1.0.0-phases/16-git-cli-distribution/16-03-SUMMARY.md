---
phase: 16-git-cli-distribution
plan: "03"
subsystem: distribution
tags: [zipapp, build-script, smoke-tests, PKG-03]
dependency_graph:
  requires: [16-02]
  provides: [dist/maccat.pyz, scripts/build-pyz.sh, tests/test_pyz.py]
  affects: []
tech_stack:
  added: []
  patterns: [stdlib-zipapp, subprocess-smoke-test, skip-guard]
key_files:
  created:
    - scripts/build-pyz.sh
    - tests/test_pyz.py
  modified: []
decisions:
  - "src/ (not src/maccat/) as zipapp source — maccat/ appears as top-level dir in archive, making import maccat work"
  - "dist/ already in .gitignore before this plan — verified, no edit needed"
  - "test_pyz_no_file_relative_catalog strips HOME to tmp_path to prevent real ~/.config/maccat/config.toml from being found"
metrics:
  duration_seconds: 144
  completed_date: "2026-06-15"
  tasks_completed: 2
  files_changed: 2
---

# Phase 16 Plan 03: Build Script + PKG-03 Smoke Tests Summary

stdlib zipapp build script and five PKG-03 smoke tests proving cwd-independence, no native libs, and no __file__-relative catalog resolution in the .pyz artifact.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | scripts/build-pyz.sh + dist/maccat.pyz build | 27f7bd3 | scripts/build-pyz.sh |
| 2 | tests/test_pyz.py — 5 PKG-03 smoke tests | 1c3ee64 | tests/test_pyz.py |

## What Was Built

### Task 1 — scripts/build-pyz.sh

Single bash script (27 lines, `set -euo pipefail`) that:
- Derives `SRC_DIR` and `DIST_DIR` from `SCRIPT_DIR` (script-relative, not cwd-relative)
- Purges `__pycache__` before building for a clean archive
- Calls `python3 -m zipapp "$SRC_DIR"` with `--output`, `--python "/usr/bin/env python3"`, `--main "maccat.__main__:main"`, `--compress`
- Source is `src/` (not `src/maccat/`) — critical for `import maccat` to work inside the archive

Verification results:
- `dist/maccat.pyz --version` → `maccat 1.0.0` (exit 0) from project root and from `/tmp`
- `dist/maccat.pyz --help` → exit 0
- `zipfile.ZipFile` namelist: 34 entries, 0 `.so`/`.dylib` files
- `dist/` and `*.pyz` already in `.gitignore` — no edit needed; artifact not committed

### Task 2 — tests/test_pyz.py

Five smoke tests covering PKG-03:

| Test | Assertion | Acceptance |
|------|-----------|------------|
| `test_pyz_version_from_unrelated_cwd` | `--version` exits 0 from `tmp_path`; stdout contains `maccat` | PKG-03 cwd-independence |
| `test_pyz_help_from_unrelated_cwd` | `--help` exits 0 from `tmp_path` | PKG-05 help from any dir |
| `test_pyz_no_so_dylib` | `zipfile.ZipFile.namelist()` contains zero `.so`/`.dylib` entries | PKG-03 pure Python |
| `test_pyz_no_file_relative_catalog` | No-config run (HOME→tmp, no MACCAT_CATALOG_DIR) exits nonzero with "catalog" in output | PKG-03 no __file__ fallback |
| `test_pyz_maccat_package_importable_from_pyz` | `sys.path.insert(0, pyz); import maccat; maccat.__version__ == "1.0.0"` | correct archive layout |

All tests skip cleanly when `dist/maccat.pyz` is absent (skip guard via `_require_pyz()`).

## Verification Results

```
scripts/build-pyz.sh         → Built: .../dist/maccat.pyz
maccat.pyz --version         → maccat 1.0.0 (exit 0, project root)
maccat.pyz --version (cwd=/tmp) → maccat 1.0.0 (exit 0)
zipfile native lib count     → 0
.gitignore dist/ entry       → line 9: dist/
.gitignore *.pyz entry       → line 11: *.pyz
dist/maccat.pyz in git ls-files → (empty — not tracked, correct)
pytest tests/test_pyz.py     → 5 passed
pytest (full suite)          → 394 passed
ruff check tests/test_pyz.py → All checks passed
mypy --strict tests/test_pyz.py → Success: no issues found
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All test behavior is fully wired (tests run against the real built artifact, not mocks).

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. `scripts/build-pyz.sh` reads `src/` and writes to `dist/` (gitignored). `tests/test_pyz.py` launches subprocess invocations of the `.pyz` with sanitized environments — no secrets exposed.

## Self-Check: PASSED

Files exist:
- [x] `/Users/ken/dev/mac-software-list/scripts/build-pyz.sh` — FOUND
- [x] `/Users/ken/dev/mac-software-list/tests/test_pyz.py` — FOUND
- [x] `/Users/ken/dev/mac-software-list/dist/maccat.pyz` — FOUND (built, not committed)

Commits exist:
- [x] 27f7bd3 — feat(16-03): scripts/build-pyz.sh
- [x] 1c3ee64 — test(16-03): tests/test_pyz.py
