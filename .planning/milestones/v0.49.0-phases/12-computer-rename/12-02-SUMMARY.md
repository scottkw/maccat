---
phase: 12-computer-rename
plan: "02"
subsystem: cli
tags: [zsh, rename, folder-model, opt-out-prompt, atomic-map, single-commit, pty-test]

# Dependency graph
requires:
  - phase: 12-computer-rename
    plan: "01"
    provides: "rename_machine front-half (folder picker + Quit, validated new-name prompt, four guards, single folder mv) handing off old_name/new_name/old_dir/new_dir locals and the already-moved folder"
provides:
  - "rename_machine back-half: opt-out-gated in-folder filename rewrite scoped to new_dir + new_dir/archive"
  - "Unconditional atomic machine-labels.tsv rewrite (value==old_name -> new_name) running in BOTH rewrite and opt-out modes"
  - "Single commit staging old_name/ (deletions) + new_name/ (adds) + machine-labels.tsv; gated on staged changes (folder moved), NOT on renamed_count"
  - "--no-commit manual-instructions path printing the new folder paths + folder-centric commit message"
  - "renamed_count==0 abort gate REMOVED; legacy old_label/new_label/dirs shims removed"
  - "test-rename-back-12-02.sh: mktemp-fixture + PTY harness with a stubbed git proving Y/opt-out/--no-commit (26/26 PASS) with zero real-tree or real-git access"
affects: [computer-rename, machine-labels.tsv, RNM-02, RNM-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reused the Plan-01 python3 pty.fork PTY driver, extended with a local no-op git() stub to exercise the AUTO_COMMIT path git-free"
    - "Opt-out [Y/n] prompt modeled on resolve_archive_retention's read + empty-default idiom"

key-files:
  created:
    - test-rename-back-12-02.sh
  modified:
    - update-list.sh

key-decisions:
  - "Gate the commit on 'the folder was moved' (staged changes), not on renamed_count — so opt-out and all-collision runs still update the map and commit (CRITICAL DIVERGENCE 1)"
  - "Place the atomic map rewrite UNCONDITIONALLY after the opt-out branch so it runs in both Y and n modes (the folder name is the computer identity)"
  - "Fixed a latent bare-redirect hang (`> \"$tmp_file\"` runs zsh $READNULLCMD=cat on stdin) by using `: > \"$tmp_file\"` — required for the interactive --rename map rewrite to not block forever"

patterns-established:
  - "PTY harness + no-op git() stub: source the script, point SCRIPT_DIR at a mktemp fixture, define git(){return 0;}, drive rename_machine over pty.fork; lets the AUTO_COMMIT branch be tested with zero real git"

requirements-completed: [RNM-02, RNM-03]

# Metrics
duration: 22min
completed: 2026-06-14
---

# Phase 12 Plan 02: Computer Rename Back-Half Summary

**Reworked `rename_machine`'s back half into the folder-centric flow: an opt-out-gated in-folder filename rewrite (scoped to the moved folder + its archive), an unconditional atomic `machine-labels.tsv` update that runs in BOTH rewrite and opt-out modes, and a single commit staging the old + new folder paths + the map (with a folder-centric `--no-commit` manual path) — the `renamed_count==0` abort gate and all legacy shims removed, proven by a mktemp+PTY harness with a stubbed git (26/26 PASS) and zero real-tree/real-git access.**

## Performance

- **Duration:** ~22 min
- **Tasks:** 2
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments
- Added the `[Y/n]` opt-out prompt (default Y): `Rewrite all existing catalogs in '${new_name}' to '[${new_name}]'? [Y/n]: ` using the `read -r` + empty-default idiom; on empty/`y`/`yes` it runs the rewrite loop.
- Re-scoped the in-folder rewrite to `rewrite_dirs=("$new_dir" "${new_dir}/archive")` (the MOVED folder only), reusing the pure-zsh 14-digit timestamp parse (`${base##*-}` + `=~ ^[0-9]{14}$`), the label-match-skip (`[[ "$file_label2" != "$old_name" ]]`), and the collision-skip (`[[ -e "$dest" ]]` -> warn + `((skipped_count++))` + continue, never overwrite).
- DROPPED the `renamed_count==0` abort gate (CRITICAL DIVERGENCE 1). `renamed_count`/`skipped_count` now feed only the closing summary; a folder move with zero rewrites (opt-out or all-collision) still updates the map and commits.
- Moved the atomic `.tmp` + `mv` map rewrite to run UNCONDITIONALLY after the opt-out branch — it rewrites every TAB-bearing data line whose value equals `old_name` to `new_name`, preserves `^#`/blank/no-TAB lines verbatim, and runs in BOTH Y and n modes.
- Reworked the git block into a single commit staging `git add -A "${old_name}/"` (deletions) + `git add -A "${new_name}/"` (adds) + `git add machine-labels.tsv`, kept the `git diff --cached --quiet` no-op guard, set the commit message to `Rename computer: '${old_name}' -> '${new_name}'`, and reworded the push-failure recovery to say the folder has ALREADY moved (do NOT re-run `--rename`).
- Reworked the `--no-commit` manual path to print the new folder paths (`git add -A '${old_name}/' && git add -A '${new_name}/' && git add machine-labels.tsv`) and the folder-centric commit message.
- Removed the legacy `old_label`/`new_label`/`dirs` shims and all 4-hardcoded-dir references; removed the Plan-01 temporary `return 0` stop.
- Built `test-rename-back-12-02.sh`: a mktemp-fixture + PTY harness with a local no-op `git()` stub (26 assertions) covering Y (main+archive rewritten to `[newpc]`, non-matching label untouched, collision skipped), opt-out (folder moves, old names kept, map STILL updates), and `--no-commit` (folder-centric manual instructions printed, no commit) — all in throwaway fixtures, never touching the repo's real `personal/`/`office/` trees or real git.

## Task Commits

1. **Task 1: Opt-out-gated in-folder rewrite; drop renamed_count==0 abort; unconditional atomic map update in both modes** - `1674df5` (feat)
2. **Task 2: Single commit staging old+new folder paths + map; --no-commit path; closing summary; full fixture test (incl. the bare-redirect hang fix)** - `927d049` (test)

## Files Created/Modified
- `update-list.sh` - Reworked the back half of `rename_machine`: opt-out-gated rewrite re-scoped to the moved folder + archive, unconditional atomic map update in both modes, single commit staging old+new folder paths + map, folder-centric `--no-commit` path, summary line. Removed the `renamed_count==0` abort, the legacy shims, and the `return 0` stop. Fixed the map rewrite's bare `> "$tmp_file"` to `: > "$tmp_file"`.
- `test-rename-back-12-02.sh` - New throwaway harness: mktemp fixtures + python3 PTY driver + a local no-op `git()` stub; asserts on output + on-disk folder/map state across Y, opt-out, and `--no-commit` cases.

## Decisions Made
- **Commit gated on the folder move, not on `renamed_count`.** Plan 01 already performed the folder `mv`, so a rename is commit-worthy even when zero filenames are rewritten (opt-out, or all-collision). The map update + commit are therefore unconditional; `renamed_count==0` aborting would have left the map pointing at a folder that no longer exists.
- **Map update placed after (not inside) the opt-out branch.** The folder name IS the computer identity, so every `hostname -> old_name` entry must repoint regardless of the rewrite choice.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Map rewrite hung forever on interactive `--rename`**
- **Found during:** Task 2 (PTY harness brought up — the map block never returned)
- **Issue:** The map-rewrite block (inherited shape from the analog) truncated its temp file with a bare `> "$tmp_file"`. In zsh a redirection with no command runs `$READNULLCMD` (`cat`), which reads from **stdin** — over the interactive `--rename` PTY this blocks forever, so the map was never written and the commit never reached.
- **Fix:** Changed to `: > "$tmp_file"` (the `:` builtin as the command), which truncates without invoking `$READNULLCMD`. Added a comment explaining the trap.
- **Files modified:** update-list.sh (in-scope map block, the region this plan owns)
- **Commit:** `927d049`

This fix was inside the back-half region this plan rewrites, so it is in scope.

## Deferred Issues
- **update-list.sh:570 (`upsert_machine_label`)** has the same bare `> "$tmp_file"` truncation pattern. It is pre-existing and outside this plan's task region, so it was NOT fixed; logged to `.planning/phases/12-computer-rename/deferred-items.md` with the same one-char (`: >`) fix recommended for a future maintenance pass.

## Issues Encountered
- **PTY drivers must consume exactly the scripted input.** A `read` that outruns the fed lines blocks on the open PTY; cases are sized so the function reaches its end (zsh exits, PTY closes) and the 5s `select` timeout backs out cleanly. This is the same constraint Plan 01 handled.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `rename_machine` is now complete end-to-end (front-half picker/guards/move from Plan 01 + this back-half rewrite/map/commit). RNM-02 (default-Y rewrite, opt-out leaves filenames) and RNM-03 (atomic map update in both modes, single commit honoring `--no-commit`) are satisfied.
- Both critical divergences hold: `renamed_count==0` abort removed (this plan); HARD refuse-clobber from Plan 01 intact (no soft collision warning reintroduced).
- `select_computer` / Phase 11 selection behavior and the main-block `--rename` short-circuit (`git_pull; rename_machine; exit 0`) were left untouched.

## Self-Check: PASSED
- update-list.sh: FOUND (reworked `rename_machine` back-half)
- test-rename-back-12-02.sh: FOUND
- Commit 1674df5: FOUND
- Commit 927d049: FOUND
- `zsh -n update-list.sh`: exits 0
- `zsh test-rename-back-12-02.sh`: 26/26 PASS
- `renamed_count==0` gate / `Map not updated.` text / `old_label`/`new_label` shims: 0 occurrences in rename_machine

---
*Phase: 12-computer-rename*
*Completed: 2026-06-14*
