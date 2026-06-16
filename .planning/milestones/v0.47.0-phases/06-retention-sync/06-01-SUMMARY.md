---
phase: 06-retention-sync
plan: "01"
subsystem: update-list.sh
tags:
  - retention
  - archive
  - git-staging
  - shell-script
dependency_graph:
  requires: []
  provides:
    - retain_newest_per_host function
    - prune_old_archives function
    - ARCHIVE_AGE_DAYS=30 constant
    - git add -A scoped staging
    - corrected main-block call order
  affects:
    - update-list.sh archive/retention behavior
    - git commit contents (adds deletions and moves)
tech_stack:
  added: []
  patterns:
    - two-pass Zsh associative array (typeset -A) for per-host grouping
    - BSD date -v-Nd cutoff for archive prune
    - setopt local_options null_glob for graceful empty-directory handling
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - Replace age-based archive_old_catalogs with two focused functions: newest-per-host retention + explicit 30-day prune
  - Use typeset -A two-pass algorithm (pass 1: build max-ts map; pass 2: archive non-max) to avoid glob-order bugs
  - Add setopt local_options null_glob to both new functions for RET-04 graceful degradation on empty directories
  - git add -A scoped to TARGET_LOCATION/ to stage adds, moves (as D+A), and prune deletions in one call
metrics:
  duration_minutes: 10
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_modified: 1
---

# Phase 06 Plan 01: Retention & Sync Summary

**One-liner:** Two-pass per-host retention sweep + 30-day archive prune replacing age-based `archive_old_catalogs`, with `git add -A` scoped staging to propagate moves and deletions across machines.

## What Was Built

Replaced `archive_old_catalogs` (single age-based move function) in `update-list.sh` with two new functions and corrected the main-block call order:

**`retain_newest_per_host(target_dir)`** — two-pass Zsh associative array algorithm:
- Pass 1: builds `newest_ts[hostname]` map from all `mac-software-list-*.txt` files in the main folder
- Pass 2: moves any file whose timestamp is not the max for its hostname to `archive/`
- Tied-newest files are ALL kept (data-loss-averse per RET-04)
- Creates `archive/` with `mkdir -p` if absent

**`prune_old_archives(target_dir)`** — BSD `date -v-30d` cutoff hard-delete:
- Computes `cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")`
- Iterates `archive/mac-software-list-*.txt`, extracts 8-digit YYYYMMDD, deletes if `-lt cutoff`
- Returns early if `archive/` does not exist
- Unparseable timestamps: warn + continue, never delete

**`ARCHIVE_AGE_DAYS`** changed from 60 to 30; semantics changed from "move at N days" to "hard-delete archive at N days."

**`git_commit_and_push`** staging: replaced two targeted `git add` calls with `git add -A "${TARGET_LOCATION}/"` to capture additions, moves (as D+A pairs), and prune deletions in one staging call.

**Main block reordered:** `git_pull` → set vars → `mkdir -p` → `generate_catalog` → `retain_newest_per_host` → `prune_old_archives` → (AUTO_COMMIT conditional). Generating before the retention sweep ensures the just-written file is always the newest for this host and is never archived.

**display_usage text** updated to reflect per-machine retention semantics.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Replace archive_old_catalogs with retain_newest_per_host + prune_old_archives; update constant and usage text | a20eafd |
| 2 | Update git_commit_and_push staging and reorder main block | 501099b |
| 3 | Ephemeral self-test — all 14 assertions pass; null_glob fix | efd2d4d |

## Verification Results

```
zsh -n update-list.sh                        → Syntax OK
grep 'ARCHIVE_AGE_DAYS=30'                   → 1 match
grep -c 'archive_old_catalogs'               → 0
grep -c 'retain_newest_per_host'             → 3 (definition + 2 call sites incl. test)
grep 'git add -A.*TARGET_LOCATION'           → 1 match at git_commit_and_push
zsh /tmp/test-retention-06.zsh              → 14 passed, 0 failed
```

Self-test proved:
- Test 1: Oldest catalog for Host A archived; newest kept in main; sole Host B file kept; non-catalog file untouched
- Test 2: Archive file dated 2026-01-01 (>30d) deleted; archive file dated 2026-06-01 (<30d) kept; non-catalog archive file untouched
- Test 3: Second consecutive retain run is a no-op (idempotent)
- Test 4: Empty folder + missing archive/ — both functions complete without error
- Test 5: Unparseable-timestamp file never moved or deleted

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added setopt local_options null_glob to both new functions**
- **Found during:** Task 3 self-test (empty office/ directory caused "no matches found" error)
- **Issue:** The plan's retention/prune functions used `[[ -e "$file" ]] || continue` null-glob guards, but Zsh's default behavior errors on unmatched globs rather than returning the literal pattern. The guard only works after the shell has already attempted glob expansion.
- **Fix:** Added `setopt local_options null_glob` before each for-loop in both `retain_newest_per_host` and `prune_old_archives`, matching the pattern used in other functions throughout the script (lines 944, 1186, 1226, 1331).
- **Files modified:** `update-list.sh`
- **Commit:** efd2d4d (included with Task 3)
- **Requirement satisfied:** RET-04 (graceful degradation on empty folder / missing archive/)

**2. [Rule 3 - Blocking Issue] Corrected sed pattern in self-test to match function definitions only**
- **Found during:** Task 3 — first test run output showed functions being called during sourcing
- **Issue:** `sed -n '/^retain_newest_per_host/,/^}/p'` matched both the function definition header AND the main-block call `retain_newest_per_host "$TARGET_LOCATION"`, causing the sed extraction to include the entire main block tail (which executed on `source`)
- **Fix:** Changed pattern to `/^retain_newest_per_host()/,/^}/p'` (with parentheses) to match only the function declaration line
- **Files modified:** `/tmp/test-retention-06.zsh` (ephemeral — not committed)

## Known Stubs

None. All functions are fully implemented and wired into the main block.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. All file operations are scoped to `${SCRIPT_DIR}/${TARGET_LOCATION}/` and its `archive/` subdir. The threat model mitigations from the plan are all implemented:

| Threat | Mitigation Applied |
|--------|--------------------|
| T-06-01 prune_old_archives rm | Glob `mac-software-list-*.txt`; dir guard; empty-ts skip |
| T-06-02 retain mv | Two-pass ensures newest never moved; tied-newest kept |
| T-06-03 git add -A scope | Path argument is `"${TARGET_LOCATION}/"`, never repo root |
| T-06-04 newest-only copy lost to prune | retain runs first; newest stays in main/; prune only touches archive/ |
| T-06-05 sole catalog archived | Pass 2 skips ts == newest_ts[host]; sole file always satisfies this |
| T-06-06 wrong location touched | Both functions parameterized by $1 (target_dir) |

## Self-Check: PASSED

Files verified:
- `/Users/ken/dev/mac-software-list/update-list.sh` — EXISTS
- `retain_newest_per_host` function — present (grep confirms)
- `prune_old_archives` function — present (grep confirms)
- `ARCHIVE_AGE_DAYS=30` — present
- `git add -A "${TARGET_LOCATION}/"` — present at line 1639

Commits verified:
- a20eafd — present in git log
- 501099b — present in git log
- efd2d4d — present in git log
