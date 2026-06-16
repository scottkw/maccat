---
phase: 11-computer-selection-cli
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/11-computer-selection-cli/11-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/11-computer-selection-cli/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (WR-01, WR-02 — Warning severity only; Info IN-01..04 out of scope by request)
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Enter-default resolution can fall through to an empty TARGET_LOCATION

**Files modified:** `update-list.sh`
**Commit:** 6762c0e
**Status:** fixed: requires human verification (logic change in the input-resolution branch)
**Applied fix:** In `select_computer`'s input loop (empty-input / `saved_folder` branch),
the saved-folder index-resolution `while` loop was followed by an unconditional `break`.
If `saved_folder` was non-empty but not present in `computers[]`, the loop left `choice`
empty and the `break` fell through to `TARGET_LOCATION="${computers[0]}"` (empty in
1-indexed zsh), which would write a corrupt `mac-software-list-[]-<ts>.txt` at the repo
root. Added an explicit post-loop guard: if `choice` is still empty after the resolution
loop, print `ERROR: saved default '<folder>' is not in the computer list.` and `exit 1`
(no silent fallback — aligns with the locked "no Enter-default when this Mac has no
remembered computer" decision and the "let it crash" principle). The legitimate
Enter-default path (saved_folder present and found in the list) is unchanged.

Verification: `zsh -n update-list.sh` passes. This is a semantic/logic change, so the
developer should confirm the guard behaves correctly under both the resolved-default and
the broken-invariant case before the phase proceeds to verification.

### WR-02: Orphaned global `MACHINE_LABEL` left behind by the refactor

**Files modified:** `update-list.sh`
**Commit:** b2004ba
**Status:** fixed
**Applied fix:** Removed the dead `MACHINE_LABEL=""` declaration and its leading comment
(`# Computer folder for this run's catalog filename (set by TARGET_LOCATION)`) from the
CONFIGURATION block. Also removed the now-stale comment fragment in the `--machine` case
that referenced "the legacy MACHINE_LABEL global" (the comment now reads simply "Routes to
TARGET_LOCATION."). `grep -n "MACHINE_LABEL" update-list.sh` confirms zero remaining
references. `--machine` was already repointed to `TARGET_LOCATION` and
`resolve_machine_label` was already removed in Phase 11, so this state was fully dead.

Verification: `zsh -n update-list.sh` passes; grep confirms no remaining references.

## Skipped Issues

None — all in-scope findings were fixed.

Out of scope by request (not attempted): IN-01 (`_name_in_list` global leakage),
IN-02 (duplicate selecting-flag false positive), IN-03 (duplicated validators),
IN-04 (narrowed discovery surface). `rename_machine` (Phase 12) was not touched.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
