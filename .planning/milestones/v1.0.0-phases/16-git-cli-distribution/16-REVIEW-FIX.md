---
phase: 16-git-cli-distribution
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/16-git-cli-distribution/16-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 16: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/16-git-cli-distribution/16-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-01: `--archive-days` flag value skips positive-integer validation (zsh parity break, possible over-deletion)

**Files modified:** `src/maccat/config.py`, `tests/test_config.py`
**Commit:** 9e38297
**Applied fix:** Added a `flag_val < 1` guard on the FLAG path in
`resolve_archive_days` (config.py:387-389) before the value is returned,
mirroring the interactive path's validation (config.py:413-414) and the zsh
contract (`val >= 1` in update-list.sh:230-233, which rejects both `0` and
negatives). The guard raises `SystemExit` with the same actionable message the
interactive path uses ("ERROR: Archive retention must be at least 1 day (got
N)."). This closes the data-loss path where a negative `--archive-days` pushed
`cutoff_yyyymmdd` (retention.py:34) into the future and caused
`prune_old_archives` to delete archives that should be retained, and where `0`
was accepted in violation of the zsh `>= 1` guarantee.

Confirmed against the zsh spec exactly: `update-list.sh:230` uses
`[[ "$val" =~ ^[0-9]+$ ]] && (( val >= 1 ))`, so zsh rejects `0` as well as
negatives. The Python guard `flag_val < 1` matches this (rejects 0 and
negatives; accepts 1+).

**Regression tests added** (`tests/test_config.py`, class `TestResolveArchiveDays`):
- `test_flag_val_zero_raises` — `--archive-days 0` raises `SystemExit` (no prune).
- `test_flag_val_negative_raises` — `--archive-days -5` raises `SystemExit` (data-loss guard).
- `test_flag_val_one_accepted` — boundary value `1` (smallest valid) still works.

These tests pass the value directly to `resolve_archive_days` and use no real
config or catalog repo (disposable / pure-call fixtures), so no real data is
touched.

**Verification:**
- `PYTHONPATH=src pytest -q`: 395 passed, 5 skipped (3 new tests included).
- `ruff check src/maccat tests`: all checks passed.
- `mypy --strict src/maccat`: 0 errors (29 source files).

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
