---
phase: 07-archive-retention-control
plan: 01
subsystem: cli
tags: [zsh, shell, archive, retention, flags, validation]

# Dependency graph
requires: []
provides:
  - "--archive-days N flag in parse_arguments with fail-fast integer validation"
  - "resolve_archive_retention() function with TTY check, interactive prompt, and same validation"
  - "ARCHIVE_DAYS_SET sentinel global to communicate flag-vs-prompt path"
  - "resolve_archive_retention wired into main block after get_target_location"
affects: [08-machine-identity, 09-machine-rename]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flag sentinel pattern: ARCHIVE_DAYS_SET=false top-level global; set true by parse_arguments; read by resolve_archive_retention to skip prompt"
    - "TTY guard: [[ ! -t 0 ]] in interactive functions to prevent read hang in cron/piped contexts"
    - "Fail-fast validation: regex + arithmetic guard ([[ val =~ ^[0-9]+$ ]] && (( val >= 1 ))) run in parse_arguments before any file ops"

key-files:
  created: []
  modified:
    - update-list.sh

key-decisions:
  - "ARCHIVE_DAYS_SET sentinel (not a modified ARCHIVE_AGE_DAYS default) used to distinguish flag-supplied vs default value, keeping the top-of-file constant readable"
  - "resolve_archive_retention placed after get_target_location and before git_pull — all interactive prompts front-loaded before any file or network operations"
  - "Same error string used in both parse_arguments and resolve_archive_retention for consistency"

patterns-established:
  - "Flag-or-prompt pattern: flag sets sentinel + value in parse_arguments; resolve_* function checks sentinel and skips prompt if set — mirrors existing --personal/--office pattern"

requirements-completed: [ARC-01, ARC-02, ARC-03]

# Metrics
duration: 3min
completed: 2026-06-14
---

# Phase 07 Plan 01: Archive Retention Control Summary

**`--archive-days N` CLI flag with interactive fallback prompt, fail-fast integer validation, and dynamic ARCHIVE_AGE_DAYS flowing into prune_old_archives**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-14T04:45:24Z
- **Completed:** 2026-06-14T04:48:57Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `ARCHIVE_DAYS_SET=false` global sentinel and `--archive-days N` case in `parse_arguments` with fail-fast validation (rejects non-integers, 0, negatives, decimals via `^[0-9]+$` regex + `(( val >= 1 ))`)
- Added `resolve_archive_retention()` function with TTY guard (non-interactive stdin silently uses default 30), `printf` prompt matching the exact spec string, and same validation for prompt input
- Wired `resolve_archive_retention` into main block after `get_target_location` and before `git_pull`; ARCHIVE_AGE_DAYS flows to prune_old_archives with no argument threading needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add --archive-days to parse_arguments and add resolve_archive_retention function** - `fb51f1d` (feat)
2. **Task 2: Wire resolve_archive_retention into main block and verify end-to-end behavior** - `7b8f7b0` (feat)

## Files Created/Modified
- `update-list.sh` - Added ARCHIVE_DAYS_SET global, --archive-days case in parse_arguments, resolve_archive_retention function, and main block call site

## Decisions Made
- Used a boolean sentinel (`ARCHIVE_DAYS_SET`) rather than checking if `ARCHIVE_AGE_DAYS != 30`, keeping the default constant readable and allowing the user to explicitly pass `--archive-days 30` without triggering the prompt
- Placed `resolve_archive_retention` after `get_target_location` and before `git_pull` so all interactive prompts are front-loaded before any network or file operations
- Error message in both code paths uses identical text (`ERROR: --archive-days must be a positive integer (got 'X')`) for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None — exit code verification in initial testing appeared to show 0 due to pipe exit code from `| head -5`; confirmed actual script exit code is 1 by capturing output in a subshell. No code changes were needed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ARC-01, ARC-02, ARC-03 all satisfied
- `ARCHIVE_AGE_DAYS` global is now runtime-configurable; Phase 8 (Machine Identity) can build on the same flag-or-prompt pattern for `--machine`
- `prune_old_archives` signature unchanged — no downstream callers affected

---
*Phase: 07-archive-retention-control*
*Completed: 2026-06-14*
