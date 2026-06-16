---
phase: 08-machine-identity
plan: "01"
subsystem: machine-identity
tags: [machine-label, hostname-map, flag-parsing, interactive-menu, git-staging]
dependency_graph:
  requires: [07-01]
  provides: [machine-labels.tsv, resolve_machine_label, MACHINE_LABEL]
  affects: [OUTPUT_FILENAME, git_commit_and_push, retain_newest_per_host]
tech_stack:
  added: []
  patterns: [flag-or-map-or-menu, atomic-write-via-tmp, TTY-guard, upsert-pattern]
key_files:
  created:
    - machine-labels.tsv
  modified:
    - update-list.sh
decisions:
  - validate_machine_label placed before parse_arguments so the --machine case can call it at parse time
  - upsert uses raw IFS= read loop to preserve comment/blank lines verbatim before TAB-split for data lines
  - upsert_machine_label writes to .tmp then mv for atomic corruption-safe updates
  - resolve_machine_label persists on EVERY resolution path (flag, map reselect, new label) per 08-CONTEXT decisions
metrics:
  duration_minutes: 4
  completed_date: "2026-06-14"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 08 Plan 01: Machine Identity Summary

**One-liner:** Friendly machine labels via `--machine` flag, hostname-to-label map (`machine-labels.tsv`), and interactive numbered menu replacing raw `$(hostname)` in catalog filenames.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add --machine flag, validate_machine_label, MACHINE_LABEL global | bab9cbc | update-list.sh |
| 2 | Implement resolve_machine_label, upsert_machine_label; create machine-labels.tsv | dd1399e | update-list.sh, machine-labels.tsv |
| 3 | Wire resolved label into OUTPUT_FILENAME and git flow | 30c2639 | update-list.sh |

## What Was Built

### New Functions

**`validate_machine_label($1)`** — Placed before `parse_arguments` so the `--machine)` case can call it at parse time. Rejects empty values, leading/trailing whitespace, and `/`, `[`, `]` characters. Called from both `parse_arguments` and the interactive create-new path in `resolve_machine_label`.

**`upsert_machine_label()`** — Writes or updates the hostname→label entry in `machine-labels.tsv`. Uses a raw `IFS= read -r line` loop to read the file verbatim, preserving comment and blank lines; only data lines get TAB-split. Writes to a `.tmp` file then `mv` for atomic, corruption-safe updates.

**`resolve_machine_label()`** — Sets `MACHINE_LABEL` global via four-step resolution:
1. Flag fast-path: `[[ -n "$MACHINE_LABEL" ]]` → persist via upsert, return
2. Map-lookup: read `machine-labels.tsv`, match `$(hostname)`, return if found
3. Non-interactive TTY guard: exit 1 with actionable error if stdin is not a TTY
4. Interactive numbered menu: distinct labels from map + "Create new label" option; persists via upsert

### New File

**`machine-labels.tsv`** — TAB-delimited hostname→label map at repo root. Created with three header comment lines. Initially empty (no host entries). Script populates on first run. Committed to git via `git add machine-labels.tsv` added to `git_commit_and_push`.

### Wiring Changes

- `MACHINE_LABEL=""` global sentinel added in configuration block
- `resolve_machine_label` called in main block after `resolve_archive_retention`, before `git_pull`
- `CURRENT_MACHINE=$(hostname)` replaced with `CURRENT_MACHINE="$MACHINE_LABEL"` — label flows into `OUTPUT_FILENAME`
- `git_commit_and_push` stages `machine-labels.tsv` alongside the target location changes
- `--no-commit` manual-commit hint updated to include `machine-labels.tsv`
- Inline comment added to both `retain_newest_per_host` host-extraction lines confirming space-containing label safety

## Verification Results

All 11 phase verification assertions pass:

1. `zsh -n update-list.sh` exits 0
2. `resolve_machine_label` count: 4 (definition + 3 references)
3. `upsert_machine_label` count: 6 (definition + call sites)
4. `validate_machine_label` count: 4 (definition + 2 call sites)
5. `MACHINE_LABEL=""` count: 1 (global sentinel)
6. `machine-labels.tsv` count: 7 (map_file path + git add + hint)
7. `machine-labels.tsv` exists at repo root
8. TAB-split read (`IFS=`) present: 21 occurrences
9. `stdin is not a TTY` TTY guard: 4 occurrences
10. `CURRENT_MACHINE="$MACHINE_LABEL"` present in main block
11. `CURRENT_MACHINE=$(hostname)` absent from main block (removed)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The machine-labels.tsv is intentionally empty at creation; no stub data — the script populates it on first run as designed.

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers. The `machine-labels.tsv` is a committed text file read (not executed) by the script. Label values are interpolated only into `OUTPUT_FILENAME` string construction, never into `eval` or command substitution.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| update-list.sh exists | FOUND |
| machine-labels.tsv exists | FOUND |
| 08-01-SUMMARY.md exists | FOUND |
| Commit bab9cbc (Task 1) | FOUND |
| Commit dd1399e (Task 2) | FOUND |
| Commit 30c2639 (Task 3) | FOUND |
