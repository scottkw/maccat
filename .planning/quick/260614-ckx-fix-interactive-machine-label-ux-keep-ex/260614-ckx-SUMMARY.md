---
phase: quick
plan: 260614-ckx
subsystem: interactive-label-ux
tags: [ux, interactive, zsh, performance]
dependency_graph:
  requires: []
  provides: [hostname-first-menu, re-prompt-loops, pure-zsh-timestamp]
  affects: [resolve_machine_label, rename_machine, validate_machine_label_quiet]
tech_stack:
  added: []
  patterns: [while-true-re-prompt, pure-zsh-parameter-expansion, non-fatal-validator]
key_files:
  created: []
  modified: [update-list.sh]
decisions:
  - validate_machine_label_quiet added alongside validate_machine_label (not replacing it) so --machine flag path stays fail-fast
  - hostname always placed at labels[1] unconditionally — fresh-machine default with zero friction
  - _label_in_list helper defined inside resolve_machine_label to avoid polluting global namespace
  - rename_machine steps 3 and 4 use while-true with validate_machine_label_quiet instead of validate_machine_label
metrics:
  duration_minutes: 15
  completed_date: "2026-06-14"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 1
---

# Phase quick Plan 260614-ckx: Fix Interactive Machine Label UX Summary

Hostname-first interactive label menu with re-prompt loops and zero-fork timestamp extraction via pure-zsh parameter expansion.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rebuild resolve_machine_label interactive path with hostname-first candidates and re-prompt loops | 2a740e7 | update-list.sh |
| 2 | Add validate_machine_label_quiet and re-prompt loops in rename_machine | 2a740e7 | update-list.sh |
| 3 | Replace subprocess timestamp extraction in rename_machine step 5 with pure-zsh expansion | 2a740e7 | update-list.sh |

## What Was Built

**Task 1 — resolve_machine_label interactive path rebuilt:**
- Candidate list now sources three data points (deduplicated, hostname always at index 1):
  a. Current hostname (always first — fresh-machine default)
  b. Labels from machine-labels.tsv
  c. Labels parsed from catalog filenames across all four directories
- Empty Enter defaults to choice 1 (hostname) with no forced typing
- Menu displays `"1) <hostname>   (keep current machine name)"` for clarity
- Invalid menu choice prints a message and re-prompts — no `exit 1`
- "Create new label" sub-loop calls `validate_machine_label_quiet` and re-prompts on bad input — no `exit 1`

**Task 2 — validate_machine_label_quiet + rename_machine re-prompt loops:**
- Added `validate_machine_label_quiet`: same four validation rules (empty, leading/trailing whitespace, `/[]/`, TAB/newline) but uses `return 1` instead of `exit 1`; emits reason string to stdout for caller display
- `validate_machine_label` (original) left completely unchanged — `--machine` flag path in `parse_arguments` still exits on violation
- `rename_machine` step 3 (OLD label pick): `exit 1` on invalid choice replaced with `while true` re-prompt loop
- `rename_machine` step 4 (NEW label entry): `validate_machine_label "$new_label"` (exit 1) replaced with `while true` loop using `validate_machine_label_quiet`

**Task 3 — pure-zsh timestamp extraction in rename_machine step 5:**
- Replaced `echo "$filename2" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14` (3 subprocess forks per file) with:
  ```zsh
  local base="${filename2%.txt}"
  local ts="${base##*-}"
  ```
- Added `^[0-9]{14}$` regex guard to validate extracted timestamp before use
- The bracketed label format `[LABEL]` ensures the label cannot contain `-`, so `##*-` reliably lands on the 14-digit timestamp

## Deviations from Plan

None — plan executed exactly as written.

The plan noted that `validate_machine_label_quiet` should be implemented before Task 1's new-label sub-loop since Task 1 depends on it. All three tasks were committed as a single atomic commit since they form a coherent UX fix unit and the file changes are all to `update-list.sh`.

## Verification Results

All verification checks passed:

1. `zsh -n update-list.sh` — exits 0 (no syntax errors)
2. Hostname appears in candidate list at `labels[1]` — confirmed via source inspection
3. Empty Enter defaults to `choice=1` — confirmed via `grep -n 'choice=1'`
4. `while true` re-prompt loops present — confirmed in resolve_machine_label (menu + new-label) and rename_machine (steps 3 + 4)
5. No `exit 1` in interactive menu section (lines 475-570) — grep returned empty
6. No `exit 1` in rename_machine steps 3-4 — grep returned empty
7. `validate_machine_label_quiet` exists and uses `return 1` only — confirmed
8. `validate_machine_label` (original) retains 4 `exit 1` calls — confirmed count=4
9. Old `grep -oE | cut` pipeline absent from rename step 5 — grep returned empty
10. Pure-zsh `${base##*-}` expansion present at line 725
11. `^[0-9]{14}$` validation guard present at line 726
12. Unit test: `validate_machine_label_quiet ""` returns exit=1 — PASS
13. Unit test: timestamp extraction — 4/4 cases passed including malformed-name rejection

## Known Stubs

None.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced.
The `validate_machine_label_quiet` function applies the same input sanitization rules as `validate_machine_label`, satisfying threat T-ckx-01 (label sanitization before filename/TSV embedding).

## Self-Check: PASSED

- update-list.sh modified and committed at 2a740e7 — FOUND
- SUMMARY.md created at .planning/quick/260614-ckx-fix-interactive-machine-label-ux-keep-ex/260614-ckx-SUMMARY.md — FOUND
