---
phase: 14-config-identity-retention
plan: "02"
subsystem: retention
tags: [retention, tdd, two-pass, archive, prune, safety-critical]
dependency_graph:
  requires:
    - maccat.naming.parse_catalog_filename
    - maccat.naming.make_catalog_filename
    - tests.conftest.tmp_path
  provides:
    - maccat.retention.retain_newest_per_host
    - maccat.retention.prune_old_archives
    - maccat.retention.cutoff_yyyymmdd
  affects:
    - src/maccat/catalog/writer.py (Phase 16 — generate-then-sweep ordering will call retain/prune)
    - src/maccat/__main__.py (Phase 16 — CLI will wire --archive-days through to prune_old_archives)
tech_stack:
  added: []
  patterns:
    - two-pass retention algorithm (pass 1 builds newest dict, pass 2 keeps ts == newest[machine])
    - parse-returns-None guard: warn-and-continue, never move/delete on parse failure
    - string < comparison for YYYYMMDD (lexicographic == numeric for zero-padded ISO dates)
    - datetime.now() - timedelta as stdlib replacement for BSD date -v-Nd
    - unittest.mock.patch on cutoff_yyyymmdd for time-independent prune tests
key_files:
  created:
    - src/maccat/retention.py
    - tests/test_retention.py
  modified: []
decisions:
  - "Two-pass algorithm is mandatory — single-pass with max() would archive tied-newest files; only two-pass correctly keeps all files whose timestamp equals the per-host maximum"
  - "cutoff_yyyymmdd patched in tests via unittest.mock.patch so prune tests are not calendar-dependent (avoids flaky test on boundary dates)"
  - "prune_old_archives accepts archive_dir directly (not target_dir) — it operates exclusively on the archive/ subdirectory, matching the zsh analog and the prune-scope safety invariant"
  - "string comparison < on YYYYMMDD is intentional and documented — lexicographic order equals numeric order for zero-padded ISO dates, matching zsh -lt integer comparison on the same format"
metrics:
  duration_minutes: 12
  completed_date: "2026-06-14"
  tasks_completed: 2
  files_changed: 2
---

# Phase 14 Plan 02: retention.py — Two-pass Retention and N-day Archive Prune Summary

TDD implementation of safety-critical retention and prune functions: two-pass per-host max-timestamp retention with tied-newest and unparseable-skip invariants, and N-day archive prune operating only on archive/ with identical skip guard.

## What Was Built

### Task 1: tests/test_retention.py (RED — failing tests written before implementation)

17 tests written and committed before `retention.py` existed. All tests failed with `ModuleNotFoundError: No module named 'maccat.retention'` (expected RED state).

**TestRetainNewestPerHost (8 tests):**
- `test_single_file_stays_in_main`: one file per host, no archiving
- `test_older_file_moved_to_archive`: T1 < T2 for same host → T1 to archive/, T2 stays
- `test_tied_newest_both_kept`: idempotency invariant — sole file with max ts is never archived
- `test_tied_newest_two_hosts_tied`: two different hosts with same ts each independently kept
- `test_unparseable_filename_never_moved`: non-catalog .txt → never moved (T-14-03 invariant)
- `test_non_catalog_txt_untouched`: README.txt, .gitkeep untouched
- `test_archive_dir_created_if_absent`: archive/ directory created by the function
- `test_multiple_hosts_independent`: alpha and beta each with old+new; old archived per host

**TestPruneOldArchives (6 tests):**
- `test_old_file_deleted`: YYYYMMDD before cutoff → deleted
- `test_recent_file_kept`: YYYYMMDD after cutoff → kept
- `test_boundary_date_kept`: YYYYMMDD == cutoff → kept (strict < not <=)
- `test_unparseable_filename_never_deleted`: non-catalog .txt in archive/ → never deleted (T-14-04)
- `test_missing_archive_dir_no_error`: absent archive/ → clean early return
- `test_prune_does_not_touch_main_folder`: only archive/ touched; main folder file untouched

**TestCutoffYyyymmdd (3 tests):** 8-digit string return, 1-day=yesterday, 0-day=today.

All prune tests patch `maccat.retention.cutoff_yyyymmdd` with a fixed string ("20260601") to avoid calendar-dependent flakiness.

### Task 2: src/maccat/retention.py (GREEN — all tests pass)

Three exported functions implementing the exact zsh analog behavior:

**`cutoff_yyyymmdd(archive_days: int) -> str`**

Stdlib replacement for BSD `date -v-Nd +%Y%m%d`:
```python
(datetime.now() - timedelta(days=archive_days)).strftime("%Y%m%d")
```
Uses local time (matching BSD `date -v`).

**`retain_newest_per_host(target_dir: Path) -> None`**

Two-pass algorithm (analog: update-list.sh lines 942–1004):
- Creates `archive_dir = target_dir / "archive"` with `mkdir(exist_ok=True)`
- Pass 1: builds `newest: dict[str, str]` — max timestamp per machine label
- Pass 2: for each file, if `cf.timestamp == newest.get(cf.machine, "")` → keep; else rename to archive/; OSError → warn and leave in place
- Unparseable filenames: warned in pass 1, silently skipped in pass 2 — never moved

**`prune_old_archives(archive_dir: Path, archive_days: int) -> None`**

Prune algorithm (analog: update-list.sh lines 1022–1064):
- Early return if `archive_dir.is_dir()` is False
- Loops `archive_dir.glob("mac-software-list-*.txt")`; parses each via `parse_catalog_filename`
- Unparseable → warn + continue (never delete)
- `cf.timestamp[:8] < cutoff_yyyymmdd(archive_days)` → `f.unlink()`
- String comparison is correct: YYYYMMDD is lexicographically ordered = numerically ordered

## Verification Results

```
PYTHONPATH=src ./venv/bin/pytest tests/test_retention.py -v   → 17 passed
PYTHONPATH=src ./venv/bin/pytest tests/ -v                    → 97 passed (regression: OK)
./venv/bin/mypy --strict src/maccat/retention.py              → Success: no issues
./venv/bin/ruff check src/maccat/retention.py tests/test_retention.py → All checks passed
```

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | 3541cfa | Present — all 17 tests fail with ModuleNotFoundError before implementation |
| GREEN (feat commit) | a58ef6a | Present — all 17 tests pass after implementation |
| REFACTOR | N/A | No refactor needed; ruff lint fix applied during GREEN verification |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff lint: unused pytest import + import ordering in test_retention.py**
- **Found during:** GREEN verification (`ruff check`)
- **Issue:** `import pytest` was included but unused; import block ordering violated ruff's isort rules
- **Fix:** Removed unused `import pytest`; applied `ruff --fix` for import ordering
- **Files modified:** tests/test_retention.py
- **Commit:** Included in GREEN commit `a58ef6a`

**2. [Rule 1 - Bug] Unused variables `f1`, `f2` in test_tied_newest_both_kept**
- **Found during:** GREEN verification (`ruff check`)
- **Issue:** Draft test code left two unused Path assignments with planning comments
- **Fix:** Removed the unused paths and replaced the verbose comment block with a focused docstring
- **Files modified:** tests/test_retention.py
- **Commit:** Included in GREEN commit `a58ef6a`

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-14-03: Tampering via retain moving unparseable files | `parse_catalog_filename` guard: None → warn + continue in pass 1; silently continue in pass 2; never calls `f.rename()` on unparseable filename |
| T-14-04: Tampering via prune deleting unparseable files | `parse_catalog_filename` guard: None → warn + continue; `f.unlink()` only called after successful parse AND `cf.timestamp[:8] < cutoff` |

## Known Stubs

None — `retain_newest_per_host` and `prune_old_archives` are fully implemented functions. Phase 16 will wire them into the main CLI flow (generate-then-sweep ordering), but the functions themselves are complete and tested.

## Threat Flags

None — retention.py has no network endpoints, no auth paths. It reads and moves/deletes only catalog `.txt` files under an explicitly passed `Path`. No new trust boundaries introduced.

## Self-Check: PASSED

Files exist:
- src/maccat/retention.py: FOUND
- tests/test_retention.py: FOUND

Commits exist:
- 3541cfa (test RED): FOUND
- a58ef6a (feat GREEN): FOUND
