---
phase: 23-retire-zsh-reference
plan: "02"
subsystem: zsh-reference
tags:
  - cleanup
  - test-scaffold
  - ci
dependency_graph:
  requires:
    - 23-01
  provides:
    - ZSH-01
    - ZSH-02
  affects:
    - .github/workflows/ci.yml
    - tests/conftest.py
tech_stack:
  added: []
  patterns:
    - "git rm for staged deletion of scaffolding"
key_files:
  deleted:
    - update-list.sh
    - tests/test_golden_parity.py
    - tests/test_update_list_integrity.py
    - tests/golden/ (entire directory: fixtures, golden files, generate.py, normalize.py)
  modified:
    - tests/conftest.py
    - .github/workflows/ci.yml
decisions:
  - "Deleted entire tests/golden/ scaffold including fixtures — no longer needed after 23-01 backfill"
  - "Removed only the --update-golden option/fixture from conftest.py; all other fixtures preserved"
  - "Removed only the TEST-04 zsh -n step from CI; PYTHONHASHSEED matrix and pytest/ruff/mypy gates kept"
metrics:
  duration: "120s"
  completed: "2026-06-16"
  tasks_completed: 3
  files_changed: 43
---

# Phase 23 Plan 02: Retire Zsh Reference and Parity Scaffold Summary

**One-liner:** Deleted update-list.sh, the zsh parity test suite, and the CI zsh -n syntax gate — removing the ~3400-line temporary scaffold now that Phase 22/23-01 backfill is complete.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Verify and delete scaffold (update-list.sh, test files, tests/golden/) | 6530178 | 41 deleted |
| 2 | Clean conftest.py and remove CI zsh -n step | 6530178 | 2 modified |
| 3 | Full suite gate (pytest + ruff + mypy) | 6530178 | validation only |

## Deviations from Plan

None — plan executed exactly as written. The `tests/golden/__pycache__` directory required a manual `rmdir` after `git rm` emptied the tracked content (untracked bytecode left a hollow directory on disk; not a git issue, just filesystem cleanup).

## Quality Gate Results

| Gate | Result | Detail |
|------|--------|--------|
| `ruff check src tests` | PASS | All checks passed |
| `mypy --strict src/maccat` | PASS | No issues found in 30 source files |
| `pytest -x -q` | PASS | 421 passed, 5 skipped (pyz infrastructure skips only — not parity-related) |

No parity/golden/zsh skips remain in the test output.

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `test ! -f update-list.sh` | PASS |
| `test ! -f tests/test_golden_parity.py` | PASS |
| `test ! -f tests/test_update_list_integrity.py` | PASS |
| `test ! -d tests/golden` | PASS |
| `grep -c "zsh -n" .github/workflows/ci.yml` == 0 | PASS |
| `grep -c "update_golden" tests/conftest.py` == 0 | PASS |
| `grep -rn "tests.golden" tests/` == 0 | PASS |
| `grep -c "pythonhashseed" .github/workflows/ci.yml` >= 1 | PASS |
| pytest passes | PASS |
| ruff passes | PASS |
| mypy --strict passes | PASS |

## Self-Check: PASSED

- update-list.sh: not present (confirmed)
- tests/golden/: not present (confirmed)
- Commit 6530178: exists and staged 43 file changes (41 deletions + 2 modifications)
