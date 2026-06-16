---
phase: 11-computer-selection-cli
reviewed: 2026-06-14T12:10:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: clean
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-14T12:10:00Z
**Depth:** standard
**Status:** clean

## Summary

Re-review iteration 2. Confirmed both prior Warning findings are resolved with no
regressions, and did a light pass over the two fix diffs for newly introduced issues.

- **WR-01** (commit 6762c0e) — RESOLVED. The Enter-default index-resolution loop in
  `select_computer()` now has a post-loop guard (lines 445-448): if `saved_folder` is
  non-empty but not found in `computers[]`, the loop leaves `choice` empty and the new
  guard prints `ERROR: saved default '<folder>' is not in the computer list.` and
  `exit 1` instead of falling through to `computers[0]` (empty in 1-indexed zsh) and
  writing a corrupt `mac-software-list-[]-<ts>.txt` at the repo root.
- **WR-02** (commit b2004ba) — RESOLVED. The dead `MACHINE_LABEL=""` global and its
  comment were removed, and the stale "not the legacy MACHINE_LABEL global" comment in
  the `--machine` case was cleaned up. `grep` confirms zero remaining references.

Verification performed (no production run — script is destructive):
- `zsh -n update-list.sh` passes.
- `grep -n MACHINE_LABEL` returns nothing. The only `resolve_machine_label` /
  `get_target_location` hits are in a doc comment (lines 285-286), which is expected.
- Isolated `zsh` harness extracting the input-loop logic exercised all six relevant
  paths:
  - (a) saved folder present + Enter → selects the saved folder (legitimate default
    path preserved).
  - (a2) saved folder at index 1 + Enter → selects index 1.
  - (b) no remembered default + Enter → re-prompts ("please enter a number"); the new
    guard is inside the `[[ -n "$saved_folder" ]]` block and does NOT fire for an empty
    saved_folder.
  - (c) normal numeric selection with saved set → guard does NOT fire (it is only
    reachable from the empty-input branch, which numeric input bypasses).
  - (d) pathological broken-invariant (saved set, not in list) + Enter → guard fires
    and exits 1 (the WR-01 fix working as designed).
  - (e)/(f) `q` and EOF → clean QUIT before any catalog write.

No new Critical or Warning issues were introduced by either diff. The four pre-existing
Info findings remain open and do not block clean status.

## Info

### IN-01: Nested helper `_name_in_list` leaks into global scope

**File:** `update-list.sh:350-357`
**Issue:** `_name_in_list` is defined inside `select_computer`, but zsh function
definitions are not lexically scoped — the definition persists in the global function
table after `select_computer` returns, and it closes over the `computers` global
implicitly. A same-named helper elsewhere would silently collide, and `rename_machine`
independently reimplements the same dedup inline rather than sharing it.

**Fix:** Hoist `_name_in_list` to a top-level helper that takes the array name as an
argument and reuse it in `rename_machine`, or `unfunction _name_in_list` before
`select_computer` returns. Low priority — current behavior is correct.

### IN-02: Same selecting-flag passed twice triggers mutual-exclusion error

**File:** `update-list.sh:263-268`
**Issue:** `selecting_flags_seen` counts occurrences, not distinct flags. `--personal
--personal` or `--computer foo --computer foo` increments the counter to 2 and fails
with "mutually exclusive", even though both resolve to the same folder. Minor false
positive of the mutual-exclusion guard.

**Fix:** Acceptable as fail-fast strictness. If softer behavior is desired, compare the
resolved `TARGET_LOCATION` values rather than counting occurrences, and only error when
two flags disagree.

### IN-03: Two near-identical validators duplicate four rules

**File:** `update-list.sh:117-141` and `update-list.sh:156-175`
**Issue:** `validate_computer_name` (fatal, `exit 1`) and `validate_computer_name_quiet`
(non-fatal, `return 1`, reason to stdout) repeat the same four validation rules
verbatim. Any future rule change must be made in both places or they will drift.

**Fix:** Implement the rules once in the `_quiet` variant and have the fatal wrapper
call it:

```zsh
validate_computer_name() {
    local reason
    reason=$(validate_computer_name_quiet "$1") || { echo "$reason"; exit 1; }
}
```

### IN-04: Folder-discovery union does not consult the four label directories

**File:** `update-list.sh:359-377`
**Issue:** `select_computer` discovers folders from (a) top-level dirs containing
catalogs and (b) `machine-labels.tsv` values, but unlike the removed
`resolve_machine_label` it no longer parses labels from existing catalog filenames under
`personal/archive`, `office/archive`, etc. A folder whose only catalogs were already
archived and whose map row was hand-deleted would not appear in the menu. Consistent with
the Phase 11 "folder IS identity" model (archived files live under the same top-level
folder, which still globs in source-a), so this is informational rather than a defect.

**Fix:** None required if the narrowed model is intended. Confirm the intent is
documented in the phase plan.

---

_Reviewed: 2026-06-14T12:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
