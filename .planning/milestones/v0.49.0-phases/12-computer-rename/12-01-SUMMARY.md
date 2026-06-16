---
phase: 12-computer-rename
plan: "01"
subsystem: cli
tags: [zsh, rename, folder-model, interactive-menu, pty-test]

# Dependency graph
requires:
  - phase: 11-computer-selection-cli
    provides: "select_computer folder-discovery union (catalog dirs + map values) and Quit/EOF input-loop pattern; validate_computer_name_quiet; parse_arguments --rename + selecting-flag conflict guard"
provides:
  - "rename_machine front-half reworked to a folder-centric picker (alphabetical discovery + Quit)"
  - "Validated new-name re-prompt loop bound to old_name/new_name locals"
  - "Four guards: empty-list (exit 0), new==old no-op (exit 0), folder-not-found (exit 0), HARD refuse-clobber (exit 1)"
  - "Single plain folder mv (old_dir -> new_dir) producing old_name/new_name/old_dir/new_dir locals for Plan 02"
  - "test-rename-front-12-01.sh: mktemp+PTY harness proving picker/Quit/guards/move with zero real-tree or real-git access"
affects: [12-02, computer-rename, rename_machine back-half]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PTY-driven testing of TTY-guarded interactive zsh functions via a python3 pty.fork driver"
    - "Folder-discovery union reused from select_computer with the remembered-default promotion dropped"

key-files:
  created:
    - test-rename-front-12-01.sh
  modified:
    - update-list.sh

key-decisions:
  - "Stop the front-half with `return 0` immediately after the folder move so the legacy back-half does not run against the moved folder; legacy region kept (not deleted) as unreachable code with parse-only shims, to be replaced by Plan 02"
  - "Drive the TTY-guarded rename_machine over a python3 PTY (pty.fork) so the real `[[ ! -t 0 ]]` guard is exercised, never bypassed, without a live tool run"

patterns-established:
  - "PTY test driver: source the script under the source-guard, point SCRIPT_DIR at a mktemp fixture, run rename_machine inside pty.fork with scripted stdin, assert on output + on-disk fixture state"

requirements-completed: [RNM-01]

# Metrics
duration: 8min
completed: 2026-06-14
---

# Phase 12 Plan 01: Computer Rename Front-Half Summary

**Reworked `rename_machine`'s front half from the Phase 9 label-only flow into a folder-centric picker (alphabetical discovery + Quit), a validated new-name prompt, empty-list / new==old / folder-not-found / HARD refuse-clobber guards, and a single plain folder `mv` — proven by an isolated mktemp+PTY harness (23/23 PASS) with zero real-tree or real-git access.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-14T16:57:00Z
- **Completed:** 2026-06-14T17:05:12Z
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- Replaced the OLD label enumeration (map values + filename `[segment]` across 4 hardcoded dirs) and the OLD-label numbered picker with the Phase-11 folder-discovery union (catalog-bearing top-level dirs + `machine-labels.tsv` values, deduped via `_name_in_list`), sorted alphabetically only, with a Quit entry (number / `q` / `quit` / EOF -> exit 0, nothing changed).
- Kept the validated new-name re-prompt loop (`validate_computer_name_quiet`), renamed to `old_name`/`new_name`.
- Implemented all four guards per CONTEXT: empty-list warn+exit 0, new==old warn+exit 0, folder-not-found warn+exit 0, and the HARD refuse-clobber (`[[ -e "$new_dir" ]]` -> ERROR + `exit 1`, no move, no commit) replacing the old soft collision warning.
- Performed the single plain `mv "$old_dir" "$new_dir"` (archive/ rides along) FIRST, then stop cleanly; the locals `old_name`/`new_name`/`old_dir`/`new_dir` and the moved folder are ready for Plan 02's rewrite/map/commit.
- Confirmed (no change needed) the `parse_arguments` `--rename` + selecting-flag conflict guard (exit 1).
- Built `test-rename-front-12-01.sh`: a mktemp-fixture + python3-PTY harness (23 assertions) covering Quit-by-number / Quit-by-`q` / EOF, empty list, new==old no-op, folder move, and refuse-clobber, plus the parse guard — all inside throwaway fixtures, never touching the repo's real `personal/`/`office/` trees or real git.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace label enumeration + OLD picker with folder-discovery picker + Quit; new-name prompt; no-op/not-found/refuse-clobber guards** - `2525a4e` (feat)
2. **Task 2: Isolated mktemp-fixture (PTY) test of picker + guards; verify parse_arguments --rename guard** - `2f1fb17` (test)

_No TDD multi-commit split — tasks are `type="auto"`._

## Files Created/Modified
- `update-list.sh` - Reworked the front half of `rename_machine` (folder picker + Quit, validated new-name prompt, four guards, single folder mv, `return 0` stop). Reworded the TTY guard to "computer names". Legacy back-half kept as unreachable code with parse-only shims for Plan 02 to replace.
- `test-rename-front-12-01.sh` - New throwaway harness: mktemp fixtures + python3 PTY driver exercising the real TTY-guarded `rename_machine`; asserts output + on-disk fixture state; verifies the parse_arguments rename guard.

## Decisions Made
- **Stop with `return 0` after the folder move.** The plan allowed leaving the legacy back-half "intact OR commented out." A bare fall-through would have run the legacy file-rename loop / `renamed_count==0` abort gate / map rewrite against the already-moved folder, emitting a misleading "No catalog files found" warning. Adding an explicit `return 0` after the `mv` makes the legacy region unreachable in Plan 01 (kept, not deleted) so Plan 02 cleanly replaces it. Parse-only shims (`old_label`/`new_label`/`dirs`) keep the legacy region parsing under `zsh -n`.
- **PTY test driver.** `rename_machine` begins with a `[[ ! -t 0 ]]` TTY guard, so piping stdin trips the guard before the picker. Rather than bypass or stub the guard (which would not test the real function), the harness drives the sourced function inside a `python3` `pty.fork` so stdin is a real TTY and the guard passes naturally.

## Deviations from Plan
None - plan executed exactly as written. (The `return 0`-after-move and PTY approaches are explicit options the plan offered: "leave it intact OR comment it out" and "drive functions in `zsh -c` subshells feeding scripted stdin" — the PTY is the mechanism required to satisfy the function's TTY guard without a live run.)

## Issues Encountered
- **TTY guard blocks piped stdin.** Feeding scripted input over a pipe trips `[[ ! -t 0 ]]` before the picker. Resolved by driving the function inside a python3 PTY (`pty.fork`) so fd 0 is a real terminal. No change to the script's guard.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 owns the back half: the in-folder filename rewrite (scoped to `new_dir` + `new_dir/archive`, with the Y/n opt-out), the unconditional map update (`value==old_name -> new_name` in BOTH modes), and the single commit staging old+new folder paths + the map (honoring `--no-commit`). The front half hands it `old_name`/`new_name`/`old_dir`/`new_dir` and the already-moved folder.
- Plan 02 must remove the `return 0` stop, the `old_label`/`new_label`/`dirs` shims, and the legacy back-half (the `renamed_count==0` abort gate must NOT be reused — the folder move already happened and the map must update in both modes).
- `select_computer` / Phase 11 selection behavior was left untouched.

## Self-Check: PASSED
- update-list.sh: FOUND (modified `rename_machine`)
- test-rename-front-12-01.sh: FOUND
- Commit 2525a4e: FOUND
- Commit 2f1fb17: FOUND
- `zsh -n update-list.sh`: exits 0
- `zsh test-rename-front-12-01.sh`: 23/23 PASS

---
*Phase: 12-computer-rename*
*Completed: 2026-06-14*
