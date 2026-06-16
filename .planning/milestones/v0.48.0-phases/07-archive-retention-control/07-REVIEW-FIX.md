---
phase: 07-archive-retention-control
fixed_at: 2026-06-13T23:59:45Z
review_path: .planning/phases/07-archive-retention-control/07-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-06-13T23:59:45Z
**Source review:** .planning/phases/07-archive-retention-control/07-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03 — Critical + Warning; 0 Critical, 3 Warning)
- Fixed: 3
- Skipped: 0

In-scope filter was `critical_warning`, so the 4 Info findings (IN-01..IN-04) were not addressed.

## Fixed Issues

### WR-01: Interactive prompt emits a flag-specific error message for prompt input

**Files modified:** `update-list.sh`
**Commit:** 35cbc54
**Applied fix:** Changed the invalid-input error in `resolve_archive_retention` (line 236) from `ERROR: --archive-days must be a positive integer (got '...')` to `ERROR: Archive retention must be a positive integer (got '...')`. The prompt path no longer references a `--archive-days` flag the user did not type.

### WR-02: `read` without `-r` in `resolve_archive_retention` mangles backslashes

**Files modified:** `update-list.sh`
**Commit:** 85b7325
**Applied fix:** Changed `read input` to `read -r input` (line 228) so backslashes in interactive retention input are validated as-typed instead of being interpreted by `read`.

### WR-03: Non-interactive guard exists for retention but not for location

**Files modified:** `update-list.sh`
**Commit:** 141944c
**Applied fix:** Added a TTY guard near the top of `get_target_location` (after the existing command-line-argument short-circuit, before the interactive prompt). When no `--personal`/`--office` flag was given and stdin is not a TTY, the script now exits with `ERROR: No location specified and stdin is not a TTY. Pass --personal or --office.` instead of reading EOF and falling through to the invalid-choice branch. This mirrors the Phase 7 retention guard and restores the front-loaded-prompt non-interactive invariant.

## Verification

- Tier 1: re-read each modified region; all fixes present, surrounding code intact.
- Tier 2: `zsh -n update-list.sh` passes after all three fixes.

All three are messaging/robustness fixes (not logic-algorithm changes), verified by syntax check and re-read.

---

_Fixed: 2026-06-13T23:59:45Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
