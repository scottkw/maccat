---
phase: 17-parity-safety-tests
plan: "03"
subsystem: testing/ci
tags: [safety-invariants, ci, zsh-integrity, pytest-markers, github-actions]
dependency_graph:
  requires: [17-01, 17-02]
  provides: [TEST-03, TEST-04, CI-workflow]
  affects: [tests/test_safety_invariants.py, tests/test_update_list_integrity.py, .github/workflows/ci.yml]
tech_stack:
  added: [GitHub Actions CI, pytest markers]
  patterns: [pytestmark module-level marker, subprocess zsh -n syntax check, PYTHONHASHSEED matrix]
key_files:
  created:
    - tests/test_safety_invariants.py
    - tests/test_update_list_integrity.py
    - .github/workflows/ci.yml
  modified:
    - pyproject.toml
decisions:
  - "safety_invariant marker registered in pyproject.toml markers list to suppress PytestUnknownMarkWarning"
  - "PYTHONHASHSEED matrix [0, 42, 'random'] satisfies criterion-4; 'random' exercises per-run randomized seed while 0/42 add reproducible diagnostics"
  - "macos-latest only runner — no ubuntu/windows (zsh built-in dependency)"
  - "Version tags (checkout@v4, setup-python@v5) not SHA hashes per plan requirement"
metrics:
  duration: 2
  completed_date: "2026-06-15"
  tasks_completed: 2
  files_created: 3
  files_modified: 1
---

# Phase 17 Plan 03: Safety-Invariant Suite, TEST-04 Integrity Check, and CI Workflow Summary

**One-liner:** Three tagged destructive-op safety invariants (TEST-03), a zsh -n integrity tripwire (TEST-04), and a GitHub Actions CI workflow with PYTHONHASHSEED matrix [0, 42, "random"] on macos-latest.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write test_safety_invariants.py and test_update_list_integrity.py, register marker | d4f9078 | tests/test_safety_invariants.py, tests/test_update_list_integrity.py, pyproject.toml |
| 2 | Create .github/workflows/ci.yml with PYTHONHASHSEED matrix and zsh -n step | 91cdbac | .github/workflows/ci.yml |

## What Was Built

### tests/test_safety_invariants.py (TEST-03)
Three explicit safety invariants tagged `pytestmark = pytest.mark.safety_invariant`:
- `test_prune_skips_unparseable_filename` — INVARIANT (a): `prune_old_archives` with `archive_days=0` never deletes `old-notes.txt` (unparseable filename). Patches `maccat.retention.cutoff_yyyymmdd` return value for time-independence.
- `test_retain_keeps_all_tied_newest` — INVARIANT (b): `retain_newest_per_host` keeps both `alpha` and `beta` files with identical timestamps; archive dir empty.
- `test_rename_hard_refuses_clobber` — INVARIANT (c): `rename_machine` raises `SystemExit` when destination folder already exists; both `OldName/` and `NewName/` remain intact.

All three use `tmp_path` fixtures — never touch real `personal/`/`office/`/`$HOME` paths.

### tests/test_update_list_integrity.py (TEST-04)
Single test `test_update_list_passes_zsh_syntax_check` runs `subprocess.run(["zsh", "-n", ...])` against `update-list.sh`. Fixed path from `Path(__file__).parent.parent`, no `shell=True`, no user-interpolated input. Acts as a tripwire: if `update-list.sh` is accidentally modified during Python development, CI catches it immediately.

### pyproject.toml
Added `markers = ["safety_invariant: explicit destructive-op safety invariants (TEST-03)"]` under `[tool.pytest.ini_options]`. Allows `pytest -m safety_invariant` to filter exactly 3 tests without `PytestUnknownMarkWarning`.

### .github/workflows/ci.yml
First CI workflow for the project:
- `on: push (branches: main) + pull_request`
- `runs-on: macos-latest` (zsh is macOS built-in; parity tests need zsh)
- `strategy.matrix.pythonhashseed: [0, 42, "random"]` with `env.PYTHONHASHSEED: ${{ matrix.pythonhashseed }}`
- Steps: `actions/checkout@v4`, `actions/setup-python@v5` (3.11), install deps, ruff, mypy --strict, pytest -x -q, named step "Check update-list.sh syntax (TEST-04)" running `zsh -n update-list.sh`

## Verification Results

```
PYTHONPATH=src ./venv/bin/pytest -m safety_invariant -v
  3 passed, 418 deselected

PYTHONPATH=src ./venv/bin/pytest -x -q
  421 passed

./venv/bin/ruff check src tests
  All checks passed!

PYTHONPATH=src ./venv/bin/mypy --strict src/maccat
  Success: no issues found in 29 source files

zsh -n update-list.sh
  exit 0 (syntax OK)

git diff --quiet HEAD -- update-list.sh
  clean (byte-unmodified)
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All tests use isolated `tmp_path` fixtures. CI workflow uses no secrets and performs read-only repo operations.

## Self-Check: PASSED

- tests/test_safety_invariants.py: FOUND
- tests/test_update_list_integrity.py: FOUND
- .github/workflows/ci.yml: FOUND
- pyproject.toml (markers): FOUND
- Commit d4f9078: FOUND
- Commit 91cdbac: FOUND
- update-list.sh: byte-unmodified (git diff clean)
- pytest -m safety_invariant: 3 passed (exact count confirmed)
- Full suite: 421 passed
