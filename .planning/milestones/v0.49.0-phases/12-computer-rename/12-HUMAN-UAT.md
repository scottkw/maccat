---
status: resolved
phase: 12-computer-rename
source: [12-VERIFICATION.md]
started: 2026-06-14
updated: 2026-06-14
---

## Current Test

All complete — executed live (end-to-end) by the autonomous agent in a disposable clone
(`/tmp/msl-uat-phase12`, no git remote) driven through a pseudo-TTY, per user authorization
("I have a backup… can you run the UAT yourself?"). Clone deleted after testing.

## Tests

### 1. Rename picker + Quit
expected: `./update-list.sh --rename` shows a numbered menu of existing computer folders plus Quit; choosing a computer prompts for a new name (re-prompts on invalid, EOF/Ctrl-D exits cleanly); Quit (number / `q` / `quit`) exits status 0 with nothing changed.
result: PASS — menu listed `office`, `personal`, `TestBox`, `Quit` (case-insensitive alphabetical). Invalid input (`99`) re-prompted; `q`, Quit-by-number, and Ctrl-D at the picker all printed `Nothing renamed.` and exited 0 with nothing moved. Ctrl-D at the new-name prompt also exited 0 cleanly (CR-01 fix — no infinite loop). Invalid name `bad/name` was rejected and re-prompted, then a valid name proceeded.

### 2. Default-Y full rename
expected: After choosing a computer and a new name, accepting the default `[Y/n]` rewrite renames the folder (its `archive/` rides along), rewrites every `[oldname]` catalog (main + archive) to `[newname]` preserving the timestamp, updates the hostname→folder map, and stages a SINGLE commit (here `--no-commit` printed instructions).
result: PASS — `TestBox/` → `RenamedBox/`; all 3 catalogs (2 main + 1 archive) rewritten `[TestBox]`→`[RenamedBox]` with timestamps preserved; map `TestBox-host` updated to `RenamedBox`; `--no-commit` printed correct `git add -A -- '…'` instructions (WR-01 `--` fix confirmed). No commit made.

### 3. Opt-out (n) rename
expected: Choosing `n` at the rewrite prompt renames the folder only; existing filenames keep their old `[label]`; the map is STILL updated and the run STILL proceeds (the `renamed_count==0` abort was intentionally removed).
result: PASS — `office/` → `Work/` (all 11 main + 33 archive files moved); filenames kept their old `[hostname]` labels; 0 rewrites but the run proceeded to completion (abort-gate removal confirmed); exit 0.

### 4. Refuse-clobber + no-op guards
expected: Renaming to an existing computer's name hard-refuses (exit 1, no move, no commit); renaming to the same name warns and exits 0 without moving files.
result: PASS — same-name (`personal`→`personal`) warned and exited 0, nothing moved. Refuse-clobber (`personal`→`office`) printed `ERROR: A computer named 'office' already exists. Refusing to merge.` and exited 1 with both folders intact.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None. All 4 live flows passed.

## Bug found & fixed during UAT

Live runs surfaced a defect that source/grep review and the function-test harnesses missed: a
**bare `local f` (no assignment) re-declared each loop iteration** makes zsh echo `f=<value>` to
stdout (typeset-query behavior on re-declaration of an existing local). This leaked internal file
paths into the **interactive menu** of BOTH `select_computer` (Phase 11) and `rename_machine`
(Phase 12) discovery, plus `local file2` in the rewrite loop. Fixed by giving each an assignment
(`local f=""`, `local file2=""`) — commit `cf171fe`. Re-ran the menu in the clone afterward: output
is clean. The menu/rename behavior was otherwise fully correct. Phase 11's `select_computer` carried
the same latent bug and is fixed by the same commit.
