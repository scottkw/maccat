---
phase: 08-machine-identity
fixed_at: 2026-06-14T00:35:00Z
review_path: .planning/phases/08-machine-identity/08-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 8: Code Review Fix Report

**Fixed at:** 2026-06-14T00:35:00Z
**Source review:** .planning/phases/08-machine-identity/08-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01 + WR-01..WR-04; IN-02 also addressed opportunistically as part of CR-01's hunk)
- Fixed: 5
- Skipped: 0

> Note: All fixes touch the single file `update-list.sh` at distinct,
> non-adjacent locations and were verified independently. They share one
> commit because the commit tool stages by file path (whole-file), not by
> hunk. Each fix below was applied and verified as a separate unit of work.

## Fixed Issues

### CR-01: Label validation regex does not reject `/`, `[`, or `]`

**Files modified:** `update-list.sh`
**Commit:** d6dce31
**Applied fix:** Replaced the non-functional `[[ "$val" =~ [/\[\]] ]]` with
`[[ "$val" =~ '[][/]' ]]` (single-quoted bracket expression, `]` placed first so
it is literal). Verified in isolated zsh 5.9: `Office/Laptop`, `has[bracket`, and
`has]bracket` are now REJECTED, while `Example Computer` and `Normal Label` are
ACCEPTED. Also split the previously combined error message so the forbidden-char
branch reports only `/`, `[`, `]` (addresses IN-02's split-message intent for
this branch).

### WR-01: Validation permits TAB and newline

**Files modified:** `update-list.sh`
**Commit:** d6dce31
**Applied fix:** Added an explicit guard in `validate_machine_label`:
`[[ "$val" == *$'\t'* || "$val" == *$'\n'* ]]` rejecting interior TAB (the TSV
column delimiter) and newline (which would split a logical map entry across
physical lines). Verified a tab-bearing label is now rejected.

### WR-02: Last map entry dropped when file lacks trailing newline

**Files modified:** `update-list.sh`
**Commit:** d6dce31
**Applied fix:** Changed all three map-reading loops to the
`while ... read -r ... || [[ -n "$var" ]]` idiom so a final unterminated line is
processed:
- `upsert_machine_label` rewrite loop (`while IFS= read -r line || [[ -n "$line" ]]`)
- `resolve_machine_label` lookup loop (`|| [[ -n "$map_host" ]]`)
- `resolve_machine_label` menu-build loop (`|| [[ -n "$map_host" ]]`)
Verified with a map file ending in `host2\tLabel Two` (no `\n`): the entry is now
read instead of being silently dropped.

### WR-03: `--machine` consumes a following flag as its label

**Files modified:** `update-list.sh`
**Commit:** d6dce31
**Applied fix:** Strengthened the guard from `[[ -z "$2" ]]` to
`[[ -z "$2" || "$2" == --* ]]` so `--machine --no-commit` errors with
`--machine requires a value` instead of treating `--no-commit` as the label.

### WR-04: `--no-commit` manual instruction stages map without missing-file guard

**Files modified:** `update-list.sh`
**Commit:** d6dce31
**Applied fix:** Rewrote the printed manual-commit instruction to separate the
map staging with the same tolerance as the auto path:
`git add -A "${TARGET_LOCATION}/" && git add machine-labels.tsv 2>/dev/null; git commit ...`
so a missing `machine-labels.tsv` no longer aborts the command sequence.

---

_Fixed: 2026-06-14T00:35:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
