---
phase: 09-machine-rename
plan: "01"
subsystem: machine-rename
tags: [rename, machine-label, flag-parsing, interactive-menu, git-staging, atomic-write]
dependency_graph:
  requires: [08-01]
  provides: [rename_machine, RENAME_MODE, --rename flag]
  affects: [machine-labels.tsv, personal/, office/, display_usage]
tech_stack:
  added: []
  patterns: [RENAME_MODE-short-circuit, four-dir-null-glob, label-dedup-union, atomic-write-via-tmp, TTY-guard, validate-reuse]
key_files:
  created: []
  modified:
    - update-list.sh
decisions:
  - rename_machine placed after resolve_machine_label and before retain_newest_per_host to match execution-flow order
  - candidate enumeration builds union of TSV labels + filename [segment] labels so pre-map machines (computer-one.local, computer-two.local) appear in menu
  - tmp_file variable (not map_file_tmp) used for atomic TSV rewrite consistent with upsert_machine_label naming
  - git add -A personal/ office/ stages all four dirs in one command (personal/archive and office/archive are subdirs)
  - --no-commit path prints manual instructions including both git add and git commit lines
metrics:
  duration_minutes: 8
  completed_date: "2026-06-14"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 09 Plan 01: Machine Rename Summary

**One-liner:** `--rename` mode with `rename_machine` function that renames a machine label across all four catalog directories and updates the hostname-to-label map in a single committed push.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add RENAME_MODE global, --rename flag, and rename_machine function | de873d2 | update-list.sh |
| 2 | Wire RENAME_MODE short-circuit into main block and update display_usage | e80fc35 | update-list.sh |

## What Was Built

### New Global

**`RENAME_MODE=false`** — Sentinel in the configuration block. Set to `true` by the `--rename` flag in `parse_arguments`. When `true`, the main block short-circuits after `parse_arguments`, calling `git_pull` + `rename_machine` + `exit 0`, skipping all catalog-generation logic.

### New Function

**`rename_machine()`** — Placed after `resolve_machine_label` and before `retain_newest_per_host`. Executes the full rename flow:

1. **TTY guard** — exits with actionable error if stdin is not a TTY.
2. **Candidate enumeration** — builds a deduplicated label array from (a) `machine-labels.tsv` entries and (b) `[segment]` values parsed from filenames across all four directories (`personal/`, `personal/archive/`, `office/`, `office/archive/`). Ensures pre-map machines appear in the menu.
3. **OLD label pick** — numbered menu (Zsh 1-indexed), validates integer in range.
4. **NEW label prompt** — `printf` + `read -r`, calls `validate_machine_label` verbatim (rejects `/`, `[`, `]`, TAB, newline, leading/trailing whitespace). No-op guard if NEW == OLD. Collision warning (non-fatal) if NEW already exists for another machine.
5. **File rename loop** — iterates over the four-dir array with `setopt local_options null_glob` and `[[ -e "$file" ]] || continue` guards. Extracts 14-digit timestamp, constructs `mac-software-list-[NEW]-<ts>.txt`, checks destination collision before `mv`.
6. **No-match guard** — exits without modifying the map or calling git if both renamed_count and skipped_count are zero.
7. **Atomic map rewrite** — `IFS= read -r line` loop preserving comments/blanks verbatim; TAB-splits data lines; replaces every entry whose label equals `old_label` with `new_label`; writes to `${map_file}.tmp` then `mv` (consistent with `upsert_machine_label`).
8. **Git commit** — `git add -A personal/ office/` + `git add machine-labels.tsv`; single commit with message `Rename machine label: 'OLD' -> 'NEW' (N file(s) across personal/office)`; push with warn-on-failure. Honors `--no-commit` with manual instructions.
9. **Summary line** — reports renamed_count and skipped_count.

### Wiring Changes

- `--rename)` case added in `parse_arguments` (after `--machine)`, before `*)`).
- `*)` error message updated to include `--rename` in valid options list.
- Main block: `RENAME_MODE` short-circuit inserted between `parse_arguments "$@"` and `get_target_location` (lines 2255–2263).
- `display_usage`: USAGE synopsis extended to include `[--rename]`; OPTIONS list gains `--rename` entry after `--machine`.

## Verification Results

All phase assertions pass (with one noted criterion inconsistency):

1. `zsh -n update-list.sh` exits 0 — PASS
2. `rename_machine` count: 4 (definition + call in main block + call in rename_machine git path comment + RENAME_MODE block) — PASS (>=3)
3. `RENAME_MODE` count: 4 (sentinel + parse case + main block check + comment) — PASS (>=3)
4. `local dirs=(...)` four-dir array: 1 — PASS
5. `setopt local_options null_glob`: 8 — PASS (>=3)
6. `validate_machine_label`: 5 — PASS (>=5)
7. `WARNING: No catalog files found for label`: 1 — PASS
8. `stdin is not a TTY`: 5 — PASS (>=5)
9. `Rename machine label:`: 2 (commit message variable + --no-commit echo) — functionally correct; plan expected 1
10. `--rename` occurrences: 7 — PASS (>=4)
11. `Rename a machine label`: 1 — PASS
12. Main block ordering: parse_arguments(2253) < RENAME_MODE check(2257) < get_target_location(2264) — PASS
13. rename_machine placement: resolve_machine_label(397) < rename_machine(510) < retain_newest_per_host(756) — PASS

## Deviations from Plan

### Minor Criterion Inconsistency (plan artifact, not implementation error)

**`grep -c 'map_file\.tmp'` — criterion expects >=2, actual: 0**

- **Found during:** Task 1 verification
- **Issue:** The plan's grep pattern `map_file\.tmp` (BRE: `map_file` + any-char + `tmp`) cannot match the source text `"${map_file}.tmp"` because the `}` brace precedes `.tmp`, making the literal sequence `map_file.tmp` absent from the source.
- **Implementation status:** The atomic `.tmp + mv` pattern IS present in both `upsert_machine_label` (line 333) and `rename_machine` (line 663) as `local tmp_file="${map_file}.tmp"`. The functional requirement is satisfied.
- **No fix applied:** Renaming the variable to force the grep match would reduce clarity without adding correctness. Documented as a plan-artifact false negative.

**`git add -A personal/ office/` — criterion expects 1, actual: 2**

- Both occurrences are correct: line 701 is the actual git staging command in rename_machine; line 728 is the `--no-commit` manual-commit instructions echo. The plan did not account for the --no-commit echo path.

**`Rename machine label:` — criterion expects 1, actual: 2**

- Line 707 is the commit message variable; line 729 is the --no-commit echo with the suggested commit message. Both are intentional and correct.

## Known Stubs

None. The rename_machine function is fully wired with no placeholder or hardcoded stub values.

## Threat Flags

No new security surface beyond the plan's threat model. The `rename_machine` function:
- Uses `validate_machine_label` (T-09-01: rejects `/`, `[`, `]`, TAB, newline, leading/trailing whitespace)
- Constructs mv destinations from validated label + extracted 14-digit timestamp only — no eval (T-09-02)
- Uses atomic `.tmp + mv` for TSV rewrite (T-09-03)
- Checks `[[ -e "$dest" ]]` before every `mv` to prevent overwrites (T-09-04)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| update-list.sh exists in worktree | FOUND |
| machine-labels.tsv exists in worktree | FOUND |
| 09-01-SUMMARY.md written | FOUND |
| Commit de873d2 (Task 1) | FOUND |
| Commit e80fc35 (Task 2) | FOUND |
| zsh -n passes | PASS |
| rename_machine function present after resolve_machine_label, before retain_newest_per_host | PASS |
| RENAME_MODE short-circuit in main block between parse_arguments and get_target_location | PASS |
