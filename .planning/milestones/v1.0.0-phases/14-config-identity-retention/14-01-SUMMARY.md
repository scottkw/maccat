---
phase: 14-config-identity-retention
plan: "01"
subsystem: naming
tags: [naming, tdd, fixtures, pure-functions, dataclass]
dependency_graph:
  requires: []
  provides:
    - maccat.naming.CatalogFilename
    - maccat.naming.parse_catalog_filename
    - maccat.naming.make_catalog_filename
    - tests.conftest.git_repo
    - tests.conftest.catalog_repo
  affects:
    - src/maccat/retention.py (Plan 02 — imports parse_catalog_filename)
    - src/maccat/identity.py (Plan 03 — imports make_catalog_filename via conftest)
    - tests/test_retention.py (Plan 02 — uses git_repo, catalog_repo)
    - tests/test_identity.py (Plan 03 — uses git_repo, catalog_repo)
tech_stack:
  added: []
  patterns:
    - frozen dataclass for structured parse results (mirrors json_io.py)
    - parse-returns-None pattern (never raises) for filename validation
    - pytest tmp_path-based disposable git repo fixture
key_files:
  created:
    - src/maccat/naming.py
    - tests/test_naming.py
  modified:
    - tests/conftest.py
decisions:
  - "_FILENAME_RE regex [^\\[\\]]+ prevents brackets in machine label — matches validate_computer_name constraint and zsh update-list.sh lines 964-965 behavior"
  - "CatalogFilename frozen=True ensures it is hashable and usable as a dict key in retention two-pass algorithm"
  - "git_repo fixture uses check=True on git init, bare calls for config (non-fatal if git config fails in some CI contexts)"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-14"
  tasks_completed: 2
  files_changed: 3
---

# Phase 14 Plan 01: naming.py — Catalog Filename Parse/Generate Summary

Pure filename-parsing module with frozen dataclass, regex-based parse returning None on mismatch, make function for generation, plus disposable git repo fixtures for all Phase 14 tests.

## What Was Built

### Task 1: src/maccat/naming.py + tests/test_naming.py (TDD)

**RED:** 21 failing tests written first, covering all parse cases and round-trip behavior.

**GREEN:** Implementation created with:
- `_FILENAME_RE` compiled regex (`^mac-software-list-\[(?P<machine>[^\[\]]+)\]-(?P<ts>\d{14})\.txt$`) — exact Python equivalent of zsh parameter expansion at update-list.sh lines 964–965
- `CatalogFilename` frozen dataclass (machine, timestamp, filename) — immutable, hashable, safe as dict key in retention two-pass algorithm
- `parse_catalog_filename` — returns None (never raises) for any non-matching input; mirrors zsh warn-and-continue policy
- `make_catalog_filename` — no validation (caller's responsibility per PATTERNS.md); round-trips cleanly

All 21 tests pass. ruff + mypy --strict clean.

### Task 2: tests/conftest.py additions

Added two fixtures after the existing `tmp_json` (which was preserved exactly):

- `git_repo(tmp_path)` — disposable git repo via subprocess, sets user.email + user.name; isolation guaranteed by pytest tmp_path
- `catalog_repo(git_repo)` — builds on git_repo, creates `personal/` with one catalog file via `make_catalog_filename`; deferred import of `maccat.naming` inside fixture body (matches existing conftest pattern)

Both fixtures satisfy T-14-02 (never reference real personal/office dirs).

## Verification Results

```
PYTHONPATH=src ./venv/bin/pytest tests/test_naming.py -v     → 21 passed
PYTHONPATH=src ./venv/bin/pytest tests/ -v                   → 80 passed (Phase 13 regression: OK)
./venv/bin/mypy --strict src/maccat/naming.py               → Success: no issues
./venv/bin/ruff check src/maccat/naming.py tests/test_naming.py tests/conftest.py → All checks passed
```

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 609cfe4 | Present — failing tests committed before implementation |
| GREEN (feat commit) | 74306dc | Present — all tests pass after implementation |
| REFACTOR | N/A | No refactor needed |

## Deviations from Plan

None — plan executed exactly as written. The ruff import-sort fix on test_naming.py was auto-applied by `ruff --fix` during the lint/verify step (not a behavioral deviation).

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-14-01: Tampering via adversarial filename | `[^\[\]]+` prevents brackets in machine label; `\d{14}` rejects timestamp injection; returns None on mismatch — no shell-out, no filesystem access |
| T-14-02: Info disclosure via real repo access in tests | git_repo fixture uses pytest tmp_path exclusively; catalog_repo builds on git_repo; neither fixture references real personal/office directories |

## Known Stubs

None — naming.py is a pure utility with complete implementation. conftest fixtures are fully functional.

## Threat Flags

None — naming.py has no network endpoints, no auth paths, no file access patterns (pure string transformation). conftest fixtures create only disposable temp directories.

## Self-Check: PASSED

Files exist:
- src/maccat/naming.py: FOUND
- tests/test_naming.py: FOUND
- tests/conftest.py: FOUND (modified)

Commits exist:
- 609cfe4 (test RED): FOUND
- 74306dc (feat GREEN): FOUND
- d9f6ed8 (feat conftest): FOUND
