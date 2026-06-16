---
phase: 10-computer-folder-identity-foundation
plan: "01"
subsystem: update-list.sh
tags:
  - source-guard
  - validation-rename
  - identity-wiring
  - machine-labels
dependency_graph:
  requires: []
  provides:
    - validate_computer_name (fatal)
    - validate_computer_name_quiet (non-fatal)
    - source-guard for isolated function testing
    - CURRENT_MACHINE wired from TARGET_LOCATION
    - machine-labels.tsv records hostname->computer-folder
  affects:
    - Phase 11 (select_computer menu built on wired identity)
    - Phase 12 (rename built on same wired identity)
tech_stack:
  added: []
  patterns:
    - Zsh source-guard ([[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0)
    - fatal/non-fatal validation pair sharing same rule body
key_files:
  created: []
  modified:
    - update-list.sh
    - machine-labels.tsv
decisions:
  - CURRENT_MACHINE is set from TARGET_LOCATION (not a separate MACHINE_LABEL) so the catalog filename [label] equals the chosen folder name
  - validate_computer_name/_quiet renamed from validate_machine_label/_quiet; error messages updated to "computer name" throughout
  - upsert_machine_label records TARGET_LOCATION as the TSV value; MACHINE_LABEL global preserved for --machine back-compat only
  - git_commit_and_push commit message simplified to "Added [CURRENT_MACHINE] catalog at DATE" since CURRENT_MACHINE now carries the full identity
metrics:
  duration: "~3 minutes"
  completed_date: "2026-06-14"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 10 Plan 01: Computer-Folder Identity Foundation Summary

**One-liner:** Source-guard + validate_computer_name rename + CURRENT_MACHINE="$TARGET_LOCATION" wiring so catalog filenames carry the folder name as identity.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Zsh source-guard before main block | 1a94cb5 | update-list.sh |
| 2 | Rename validation helpers and update all call sites | 425be0d | update-list.sh |
| 3 | Wire CURRENT_MACHINE from TARGET_LOCATION; update upsert, map header, display_usage | 7e631a0 | update-list.sh, machine-labels.tsv |

## What Was Built

**Task 1 — Source-guard:**
Added `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0` immediately before the `# MAIN SCRIPT EXECUTION` section. When sourced (e.g. `source update-list.sh` inside a subshell), the guard fires and returns before the main block runs. When executed directly (`./update-list.sh`), the guard is skipped. This makes isolated function testing via `source` safe.

**Task 2 — Validation rename:**
Renamed `validate_machine_label` → `validate_computer_name` (fatal, `exit 1`) and `validate_machine_label_quiet` → `validate_computer_name_quiet` (non-fatal, `return 1`). Validation logic (4 checks: non-empty, no leading/trailing whitespace, no `[][/]`, no TAB/newline) is byte-identical. Error messages updated from `"--machine label"` / `"Label"` to `"computer name"`. All 3 call sites updated: `parse_arguments`, `resolve_machine_label`, `rename_machine`. The 10 `while true` re-prompt loops are preserved unchanged.

**Task 3 — Identity wiring:**
- `CURRENT_MACHINE="$TARGET_LOCATION"` in the main block (was `"$MACHINE_LABEL"`)
- `upsert_machine_label` now writes `TARGET_LOCATION` as the TSV value in both the replace and append paths; echo updated to "Saved computer folder mapping"
- Header-creation template updated to "hostname to computer-folder map" / "Format: hostname\\tcomputer-folder"
- `machine-labels.tsv` live header updated to match
- `display_usage`: `[machine-label]` → `[computer-folder]` in filename description; `--machine` option description updated; global comment updated
- `git_commit_and_push` commit message: `"Added [${CURRENT_MACHINE}] catalog at ${CURRENT_DATE}"`
- `MACHINE_LABEL` global and `resolve_machine_label` function preserved for back-compat (Phase 11 will replace them)

## Deviations from Plan

None — plan executed exactly as written. All 10 `while true` loops, the hostname-first menu in `resolve_machine_label`, and the pure-zsh `${base##*-}` timestamp parse in `rename_machine` are unchanged.

## Verification Results

All checks passed:

- `zsh -n update-list.sh` — PASS
- `zsh -c "source update-list.sh; echo sourced-ok"` prints only `sourced-ok` — PASS
- `validate_machine_label` occurrences in non-comment lines: 0 — PASS
- `validate_computer_name` occurrences: 3; `validate_computer_name_quiet`: 4 — PASS
- `CURRENT_MACHINE="$TARGET_LOCATION"` is the sole assignment — PASS
- `machine-labels.tsv` header contains "computer-folder" in 2 lines — PASS
- 10 `while true` loops preserved — PASS
- Isolated function tests: fatal exits with exit=1 on empty/bracket; quiet returns 1 without shell exit; valid names (apostrophe, spaces) pass — PASS
- Isolated upsert test: writes TARGET_LOCATION as TSV value; "Example Computer" round-tripped correctly — PASS

## Known Stubs

None — no placeholder data or hardcoded stubs introduced.

## Threat Flags

No new security-relevant surface introduced beyond the threat model in the plan. Validation functions (T-10-01 mitigation) are correctly wired to both the flag path (`validate_computer_name`) and the interactive re-prompt path (`validate_computer_name_quiet`).

## Self-Check: PASSED

- `update-list.sh` exists and is modified: FOUND
- `machine-labels.tsv` exists and is modified: FOUND
- Commit 1a94cb5 (Task 1): FOUND
- Commit 425be0d (Task 2): FOUND
- Commit 7e631a0 (Task 3): FOUND
