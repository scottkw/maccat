---
phase: 11-computer-selection-cli
plan: "02"
subsystem: cli-selection
tags: [zsh, cli-flags, computer-folder, arg-parsing, main-block-wiring]

requires:
  - phase: 11-01
    provides: "select_computer function (always-shown computer-folder menu, flag short-circuit, Quit/Create-new/Select branches)"
  - phase: 10
    provides: "validate_computer_name (fatal validator); upsert_machine_label; machine-labels.tsv map"
provides:
  - "--computer \"Name\" flag (primary, non-interactive select-or-create)"
  - "--personal / --office / --machine \"X\" as equivalent TARGET_LOCATION aliases"
  - "multi-selecting-flag mutual-exclusion guard + --rename conflict guard"
  - "main block calling select_computer once before generate_catalog/commit"
  - "legacy get_target_location and resolve_machine_label fully removed"
affects: [12-rename-flow]

tech-stack:
  added: []
  patterns:
    - "Selecting-flag counter (selecting_flags_seen) + post-loop fail-fast mutual-exclusion guard"
    - "Aliases route to a single global (TARGET_LOCATION); conflict detected by count, not per-global checks"

key-files:
  created: []
  modified:
    - "update-list.sh (parse_arguments --computer arm + alias routing + guards; main-block rewire; legacy fns removed; display_usage)"
    - "test-parse-arguments-11-02.sh (TDD harness for Task 1)"

key-decisions:
  - "--machine repointed from MACHINE_LABEL to TARGET_LOCATION as a silent alias; MACHINE_LABEL global declaration kept (Phase 12 may reference it) but no longer used for routing"
  - "Conflict detection via a single selecting_flags_seen counter rather than checking each global, since all four flags now write TARGET_LOCATION"
  - "--rename guard switched from -n MACHINE_LABEL to -n TARGET_LOCATION so it rejects --rename + any selecting-flag"
  - "select_computer placed before resolve_archive_retention/git_pull so a Quit (exit 0) short-circuits before any catalog write or commit"

patterns-established:
  - "Selecting-flag mutual-exclusion: increment a local counter in each arm, fail-fast after the parse loop"

requirements-completed: [CLI-01, CLI-02, QUIT-01]

duration: ~4min
completed: 2026-06-14
---

# Phase 11 Plan 02: Wire select_computer into the CLI Summary

**Added the `--computer "Name"` flag with `--personal`/`--office`/`--machine` aliases and a mutual-exclusion guard, rewired the main block to call `select_computer` once (Quit exits before any catalog/commit), and removed the legacy `get_target_location` + `resolve_machine_label` functions.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-14T16:21:33Z
- **Completed:** 2026-06-14T16:25:00Z
- **Tasks:** 2
- **Files modified:** 2 (update-list.sh + TDD harness)

## Accomplishments

- `parse_arguments` gained a `--computer "X"` arm (fatal `validate_computer_name` → `TARGET_LOCATION`), repointed `--machine` as a silent alias to `TARGET_LOCATION`, and added a `selecting_flags_seen` counter with a post-loop mutual-exclusion guard.
- The `--rename` conflict guard now checks `TARGET_LOCATION` (not `MACHINE_LABEL`), so `--rename` combined with any selecting-flag fails fast.
- Main block now calls `select_computer` once, placed before `resolve_archive_retention`/`git_pull`/`generate_catalog`, so a Quit (`exit 0` inside `select_computer`) returns before any retention sweep, catalog write, prune, or commit (QUIT-01 wiring half).
- Removed the dead `get_target_location` and `resolve_machine_label` functions (and the orphaned inner `_label_in_list` helper); `select_computer` is now the sole selection entry point.
- `display_usage` documents `--computer` as primary, plus `--personal`/`--office`/`--machine` aliases, and the synopsis line includes `--computer "Name"`.

## Task Commits

1. **Task 1 (RED): failing parse_arguments tests** - `6f4b98f` (test)
2. **Task 1 (GREEN): --computer flag + alias routing + conflict guards** - `d5c040f` (feat)
3. **Task 2: main-block rewire + dead-function removal + display_usage** - `bcc3ecb` (feat)

_Task 1 followed TDD (test → feat). Task 2 is a structural rewire verified by source/grep assertions._

## Files Created/Modified

- `update-list.sh` — parse_arguments `--computer` arm + alias routing + `selecting_flags_seen` guard + `--rename` guard update + invalid-option message; main block calls `select_computer` once; `get_target_location`/`resolve_machine_label` removed; `display_usage` updated.
- `test-parse-arguments-11-02.sh` — isolated TDD harness sourcing the script (source-guard prevents the destructive main block from running) and exercising the `--computer`/alias/conflict behaviors in `zsh -c` subshells.

## Decisions Made

- **Kept the `MACHINE_LABEL` global declaration** (line 51) per the plan — Phase 12 may still reference it — but stopped routing `--machine` through it; `--machine` now sets `TARGET_LOCATION` directly.
- **Counter-based conflict detection** rather than per-global checks, because `--personal`/`--office`/`--computer`/`--machine` all write the same `TARGET_LOCATION` now (an OR-of-globals check could not distinguish "two flags" from "one flag").

## Deviations from Plan

None - plan executed exactly as written.

The only adjustments were two harness-level fixes inside `test-parse-arguments-11-02.sh` (escaping `[$TARGET_LOCATION]` to avoid a spurious zsh glob in an assertion) — test-scaffold hygiene, no impact on the deliverable script.

## Issues Encountered

- **Plan line numbers were stale** (the script grew to ~2457 lines vs. the plan's ~2431-line snapshot): `get_target_location`, `resolve_machine_label`, and the main block were at higher line numbers than cited. Located the real boundaries by `grep -n` and edited by content, not line number — no functional impact.
- **Two acceptance-criteria greps returned 0 due to grep-flavor artifacts, NOT missing code:**
  - `grep -c 'TARGET_LOCATION="$val"'` returned 0 under BRE (the `$val` brace/quote interaction); `grep -Fc 'TARGET_LOCATION="$val"'` confirms **2** occurrences (the `--computer` and `--machine` arms).
  - `grep -c 'computer "Name"'` returned 0 because the source escapes the quotes inside `echo "..."` strings (`computer \"Name\"`); `grep -Fc 'computer \"Name\"'` confirms **4**, and the synopsis line (`update-list.sh [--computer \"Name\"`) is present. Same class of artifact documented in the Plan 01 summary.

## Verification

Per the destructive-script constraint, `update-list.sh` was NEVER run live — verified only via `zsh -n`, source+grep assertions, and isolated `source`+`parse_arguments` tests in `zsh -c` subshells (the end-of-file source-guard returns before the main block).

**Syntax / source (all pass):**
- `zsh -n update-list.sh` exits 0 after each task.
- `zsh -c "source update-list.sh; echo sourced-ok"` prints only `sourced-ok` (source-guard fires; no main-block run).
- `grep -c '\-\-computer)'` == 1; `grep -c 'selecting_flags_seen'` == 6 (declare + 4 increments + guard); `grep -c 'mutually exclusive'` == 1; `grep -Fc 'TARGET_LOCATION="$val"'` == 2; `grep -c 'Valid options.*--computer'` == 1.
- Dead-function removal (non-comment): `get_target_location()` == 0, `resolve_machine_label()` == 0, non-comment `get_target_location`/`resolve_machine_label`/`_label_in_list` == 0. (The only residual mentions are in `select_computer`'s documentation banner describing what it replaced.)
- Main-block wiring: anchored non-comment `^select_computer$` == 1; awk check confirms `select_computer` precedes `generate_catalog` in the main block.
- `display_usage`: `grep -c '\-\-computer'` == 18; synopsis line carries `--computer "Name"`.

**Isolated behavioral tests (`test-parse-arguments-11-02.sh`, 11/11 PASS):**
- a) `--computer "Example Computer"` → `TARGET_LOCATION="Example Computer"`, no exit.
- b) `--machine Foo` → `TARGET_LOCATION=Foo` (alias).
- c) `--personal` → `personal`; g) `--office` → `office`.
- d) `--computer 'a/b'` → exit 1, output contains the `/`-rule validation ERROR.
- e) `--personal --computer X` → exit 1, `mutually exclusive`.
- f) `--rename --computer X` → exit 1, `--rename cannot be combined`.
- h) `--no-commit` alone → rc 0, empty `TARGET_LOCATION`.

## Scope Guard

- `rename_machine()` is **untouched** (verified present, 1 definition) — Phase 12 scope.
- No remaining call sites for `get_target_location` / `resolve_machine_label` (0 non-comment refs).

## Threat Surface

No new threat surface beyond the plan's `<threat_model>`:
- T-11-04 mitigated: both `--computer` and `--machine` arms call the fatal `validate_computer_name "$val"` BEFORE setting `TARGET_LOCATION` — verified by behavioral case (d).
- T-11-05 mitigated: `selecting_flags_seen > 1` guard + the `--rename` + selecting-flag guard fail fast (exit 1) — verified by cases (e) and (f).
- T-11-SC accepted: no package installs; pure Zsh edits to a single existing file.

## Known Stubs

None.

## Next Phase Readiness

- The CLI surface and main-block wiring for computer selection are complete; `select_computer` is the sole selection entry point.
- Phase 12 (rename flow) can build on the intact `rename_machine` function; `MACHINE_LABEL` global remains available if Phase 12 needs it.

## Self-Check: PASSED

- FOUND: update-list.sh (contains `--computer)` arm, `select_computer` main-block call; `get_target_location`/`resolve_machine_label` removed)
- FOUND: test-parse-arguments-11-02.sh
- FOUND: .planning/phases/11-computer-selection-cli/11-02-SUMMARY.md
- FOUND commit: 6f4b98f (Task 1 RED)
- FOUND commit: d5c040f (Task 1 GREEN)
- FOUND commit: bcc3ecb (Task 2)

---
*Phase: 11-computer-selection-cli*
*Completed: 2026-06-14*
