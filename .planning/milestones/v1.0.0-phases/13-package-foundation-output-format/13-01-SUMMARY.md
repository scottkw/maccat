---
phase: 13-package-foundation-output-format
plan: 01
subsystem: infra
tags: [python, pyproject.toml, hatchling, maccat, venv, pytest, ruff, mypy]

requires: []
provides:
  - src/maccat Python package skeleton with src/ layout
  - pyproject.toml with name=maccat, requires-python>=3.11, zero runtime deps, hatchling backend
  - __version__ = "1.0.0" in src/maccat/__init__.py
  - __main__.py version guard (PKG-02) fires before any maccat.* import
  - Dev venv with pytest 9.1.0, ruff 0.15.17, mypy 2.1.0 installed in editable mode
  - .gitignore covering venv/, __pycache__, dist/, .pyz, dev caches
affects:
  - 13-02 (format layer — catalog/format.py, catalog/writer.py, helpers/)
  - 13-03 (tests scaffold — pytest infra is ready)
  - 14-*  (config layer — imports maccat; venv present)
  - 15-*  (collectors — all import maccat.catalog.*)
  - 16-*  (CLI + zipapp — maccat.__main__:main entry point)

tech-stack:
  added:
    - hatchling >= 1.26 (build backend)
    - pytest 9.1.0 (dev only)
    - ruff 0.15.17 (dev only)
    - mypy 2.1.0 (dev only)
  patterns:
    - src/ layout (PEP 517) — prevents accidental uninstalled-package imports during tests
    - sys.exit(str) version guard as first executable code in __main__.py
    - All maccat.* imports deferred inside main() body — never at module top level

key-files:
  created:
    - pyproject.toml
    - .python-version
    - .gitignore
    - src/maccat/__init__.py
    - src/maccat/__main__.py
    - src/maccat/catalog/__init__.py
    - src/maccat/helpers/__init__.py
  modified: []

key-decisions:
  - "Package name maccat locked in pyproject.toml (not mac_software_list or maclist — stale names)"
  - "Zero runtime deps enforced by omitting [project.dependencies] section entirely — comment updated to avoid grep false positive"
  - "Version guard uses sys.exit(str) not print+exit to emit actionable message to stderr in one call"
  - "Phase 16 stub in main() raises NotImplementedError('Phase 16') rather than pass — clearer intent"

patterns-established:
  - "src/ layout pattern: package lives at src/maccat/, import path is maccat.*"
  - "Version guard pattern: import sys first, guard fires at module load before any maccat.* import"
  - "Dev tools in [project.optional-dependencies] dev — never in [project.dependencies]"

requirements-completed: [PKG-01, PKG-02]

duration: 2min
completed: 2026-06-14
---

# Phase 13 Plan 01: Package Foundation Summary

**importable `src/maccat` package skeleton with pyproject.toml (hatchling, >=3.11, zero runtime deps), sys.version_info guard in __main__.py, and dev venv with pytest/ruff/mypy**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-14T19:53:07Z
- **Completed:** 2026-06-14T19:55:10Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `pyproject.toml` canonicalises maccat name, >=3.11 floor, zero runtime deps, hatchling build backend, dev extras
- `src/maccat/__init__.py` exposes `__version__ = "1.0.0"` with no imports or side effects (PKG-01 verified)
- `src/maccat/__main__.py` version guard fires before any maccat.* import using sys.exit(str) with actionable Homebrew + direct URL message (PKG-02 verified)
- Dev venv created with pytest 9.1.0, ruff 0.15.17, mypy 2.1.0 in editable mode; gitignored

## Task Commits

1. **Task 1: Create pyproject.toml and package root files** - `cd546cc` (feat)
2. **Task 2: Create __main__.py version guard + venv with dev deps** - `221563f` (feat)

**Plan metadata:** `5dd91f8` (docs: complete plan)

## Files Created/Modified

- `pyproject.toml` — build config, project metadata, dev extras, tool config (ruff, mypy, pytest)
- `.python-version` — "3.11" pin for pyenv users
- `.gitignore` — excludes venv/, __pycache__, dist/, .pyz, .mypy_cache, .ruff_cache, .pytest_cache
- `src/maccat/__init__.py` — `__version__ = "1.0.0"`, module docstring, nothing else
- `src/maccat/__main__.py` — import sys; version guard; deferred main() stub; __main__ guard
- `src/maccat/catalog/__init__.py` — `"""Catalog output format layer."""` stub
- `src/maccat/helpers/__init__.py` — `"""Shared helper utilities."""` stub

## Decisions Made

- Package name `maccat` locked in pyproject.toml — stale names `maclist`/`mac_software_list` from prior research docs not used
- Comment in pyproject.toml changed from `# No [project.dependencies]` to `# Zero runtime deps — stdlib only` to prevent grep false positive in acceptance criteria
- `main()` stub raises `NotImplementedError("Phase 16")` rather than `pass` — communicates intent more clearly
- Phase 16 stub uses `from maccat.cli import run` inside `main()` body — mirrors the exact deferred import pattern from PATTERNS.md

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .gitignore**
- **Found during:** Task 1 (package root files)
- **Issue:** No .gitignore existed in the repo. Without it, the entire `venv/` directory (hundreds of MB of installed packages), `__pycache__/`, `*.egg-info/`, and build artifacts would be untracked and risk accidental commit
- **Fix:** Created `.gitignore` covering venv/, .venv/, __pycache__, .egg-info/, dist/, build/, .pyz, .DS_Store, .vscode/, .idea/, .pytest_cache/, .mypy_cache/, .ruff_cache/
- **Files modified:** .gitignore (new)
- **Verification:** `venv/` confirmed gitignored — does not appear in `git status` after install
- **Committed in:** cd546cc (Task 1 commit)

**2. [Rule 1 - Bug] Renamed pyproject.toml zero-deps comment to avoid grep false positive**
- **Found during:** Task 1 verification
- **Issue:** The acceptance criterion `grep -c 'project.dependencies' pyproject.toml` returning 0 was tripped by the comment `# No [project.dependencies]` — the comment itself contains the string being searched
- **Fix:** Changed comment to `# Zero runtime deps — stdlib only; no third-party packages at runtime`
- **Files modified:** pyproject.toml
- **Verification:** `grep -q 'requires-python' pyproject.toml && ! grep -q 'project.dependencies' pyproject.toml && echo "OK"` now prints OK
- **Committed in:** cd546cc (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. The .gitignore is foundational for a Python project; the grep fix ensures acceptance criteria actually verify what they intend to verify.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None — venv is installed and operational. No external services required.

## Next Phase Readiness

- `PYTHONPATH=src ./venv/bin/python -c "import maccat; print(maccat.__version__)"` prints `1.0.0` — Phase 13 Plan 02 can immediately add `catalog/format.py` and `catalog/writer.py`
- pytest, ruff, mypy all available in venv — Phase 13 Plan 03 (tests) has everything it needs
- `src/maccat/catalog/` and `src/maccat/helpers/` sub-packages exist with stub `__init__.py` — Plan 02 adds the implementation files into these directories

---
## Self-Check: PASSED

All created files confirmed present:
- pyproject.toml FOUND
- .python-version FOUND
- .gitignore FOUND
- src/maccat/__init__.py FOUND
- src/maccat/__main__.py FOUND
- src/maccat/catalog/__init__.py FOUND
- src/maccat/helpers/__init__.py FOUND
- 13-01-SUMMARY.md FOUND

All task commits confirmed:
- cd546cc (Task 1) FOUND
- 221563f (Task 2) FOUND

---
*Phase: 13-package-foundation-output-format*
*Completed: 2026-06-14*
