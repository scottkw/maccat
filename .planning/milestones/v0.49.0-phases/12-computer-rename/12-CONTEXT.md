# Phase 12: Computer Rename - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — recommendations grounded in approved design spec + Phase 9/10/11 code; all 4 grey areas accepted as recommended

<domain>
## Phase Boundary

Rework the existing `rename_machine` function (built in Phase 9, currently label-only across 4
hardcoded dirs) into a **folder-centric** rename: rename a computer = rename its top-level folder,
optionally rewrite the `[label]` of every contained catalog (main + archive), update the
hostname→folder map, and commit it all in a single commit.

In scope:
- A `--rename` picker that lists existing **computer folders** (reuse Phase 11's discovery) + Quit.
- Prompt for a new name (validated via the shared helper, re-prompt on invalid).
- Rename the folder `old/` → `NewName/` (its `archive/` subfolder rides along with one `mv`).
- Default "rewrite" option: rewrite every catalog inside (main + archive) whose `[label]`==oldname
  to `[NewName]`, preserving the 14-digit timestamp, skipping destination collisions.
- Opt-out option: rename the folder only; leave existing filenames with the old label.
- Update hostname→folder map entries (old→new) in BOTH modes.
- Stage folder move + filename rewrites + map update in a single commit (honor `--no-commit`).
- No-op / not-found guards. Quit option in the picker.

Out of scope: the always-shown selection menu and `--computer` flag (Phase 11, done); catalog
*content*; renaming `machine-labels.tsv` itself.

**Authoritative spec:** `docs/superpowers/specs/2026-06-14-computer-folder-model-design.md`
(`--rename` section; Quit on all menus; Filenames/retention/transition).
</domain>

<decisions>
## Implementation Decisions

### Rename Picker & Discovery (Area 1)
- Discover existing computers with the SAME logic Phase 11's `select_computer` uses (union of
  top-level dirs containing `mac-software-list-*.txt` and `machine-labels.tsv` values, deduped).
  Do NOT reuse the old `rename_machine` label-from-filename enumeration across 4 hardcoded dirs.
- Picker ordering: alphabetical (no "this machine — default" marker; rename is not run-selection).
- Quit is selectable by number AND `q`/`quit` (case-insensitive); EOF at a prompt = clean Quit.
  Quit/EOF exit status 0 with NOTHING changed (no move, no map edit, no commit).
- Empty list (no computers discovered): warn `No computers found. Nothing to rename.` + exit 0.

### Folder Move Mechanics (Area 2)
- Move with a single plain `mv "$old_dir" "$new_dir"` (the `archive/` subfolder moves with it),
  then stage with `git add -A` on both old and new paths. (Not `git mv`.)
- If the destination folder name already exists (target is an existing computer): warn + exit,
  REFUSE to merge two computers (no clobber, no commit).
- Rewrite ordering: move the folder FIRST, then rewrite filenames inside the new path
  (`new_dir` + `new_dir/archive`).

### Filename Rewrite & Opt-out (Area 3)
- Prompt: `Rewrite all existing catalogs in 'X' to '[NewName]'? [Y/n]:` — default **Y**.
- Rewrite ONLY files whose `[label]` segment equals oldname; preserve the 14-digit timestamp;
  skip destination collisions (warn + skip, never overwrite). Reuse the existing timestamp-parse
  + collision-skip logic from `rename_machine`.
- Opt-out (n): rename the folder only; existing filenames keep their old `[label]`; still update
  the map and commit.
- Files inside the folder whose label does NOT match oldname (mixed-label transition files) are
  left untouched in both modes.

### Map Update, Commit & Guards (Area 4)
- Update EVERY `hostname → oldname` map entry to `hostname → newname` in BOTH rewrite and opt-out
  modes (the folder name IS the identity; the map must point at the new folder).
- Single commit: stage old folder path (deletions) + new folder path (adds) + `machine-labels.tsv`;
  honor `--no-commit` by printing manual instructions instead of committing.
- Guards (spec success criterion 4): new==old → warn + exit 0, no commit; folder-not-found →
  warn + exit 0, no commit; destination-exists → warn + exit, no commit (Area 2).
- Reject `--rename` combined with a selecting flag (`--computer`/`--personal`/`--office`/
  `--machine`) — fail-fast, consistent with the existing `--rename`+`--machine` guard.
</decisions>

<code_context>
## Existing Code Insights

### Reusable / to-modify (single file `update-list.sh`)
- `rename_machine` (~line 622): the function to REWORK. Currently:
  - TTY guard (keep).
  - Enumerates labels from map + filename `[segment]` across 4 hardcoded dirs (REPLACE with
    Phase-11-style folder discovery).
  - OLD-label numbered picker with `while true` re-prompt (rework into folder picker + Quit).
  - NEW-name prompt via `validate_computer_name_quiet` re-prompt loop (keep).
  - new==old no-op guard (keep); collision warning (rework into refuse-clobber for folders).
  - File rename loop with pure-zsh timestamp parse `${base##*-}` + `=~ ^[0-9]{14}$` + collision
    skip (reuse for the in-folder rewrite).
  - Atomic `.tmp`+`mv` map rewrite matching `${line#*\t}==old_label` (rework to fold value==oldname,
    and ensure it runs in BOTH modes).
  - Single git commit staging `personal/`/`office/` per-dir + map (rework to stage old+new folder
    paths; keep the per-path-exists guard idea so a missing dir doesn't abort `git add`).
  - `--no-commit` manual-instructions path (keep, update paths).
- Phase 11 `select_computer` (~line 308): its folder-discovery block (union of catalog dirs + map
  values, dedupe helper, zsh `*(/N)` glob, infra dirs excluded naturally) is the discovery pattern
  to reuse/extract for the rename picker. Its Quit (number/`q`/`quit`/EOF → exit 0) is the Quit
  pattern to mirror.
- `validate_computer_name_quiet` (~line 157): new-name validation (re-prompt path).
- `parse_arguments` (~line 190): the `--rename` short-circuit + the existing conflict guard live
  here; extend the guard so `--rename` rejects any selecting flag (not just `--machine`).
- Main block (~line 2366 region): `if [[ "$RENAME_MODE" == "true" ]]; then git_pull; rename_machine; exit 0; fi`
  — keep this short-circuit (rename runs before catalog generation).

### Established patterns
- `#!/bin/zsh`, macOS-only. snake_case, `local`, `[[ ]]`, double-quoted vars, 1-indexed arrays,
  `printf`+`read -r`, `[[ ! -t 0 ]]` TTY guard, fail-fast `echo "ERROR:"`/`WARNING:`.
- Source-guard at end of file enables isolated function testing via `source`.
- `mv` + atomic `.tmp`+`mv` for the map; null-glob guards in glob loops.
</code_context>

<specifics>
## Specific Ideas

- Target picker shape (from spec):
  ```
  Select the computer to rename:
    1) personal
    2) office
    3) Quit

  Enter your choice [1-3]:
  ```
  → new-name prompt → `Rewrite all existing catalogs in 'personal' to '[NewName]'? [Y/n]:`
- A no-match / no-op rename warns and exits WITHOUT committing or moving any files.
- Transition note (spec): existing `[hostname]` catalogs are aligned to `[folder]` only via the
  Y (rewrite-all) option of this rename — never auto-migrated on a normal run.
</specifics>

<deferred>
## Deferred Ideas

- Renaming `machine-labels.tsv` itself → out of scope (spec).
- Auto-migrating mixed-label files on a normal run → out of scope; only via this rename's Y option.
- Changing catalog content / software sections → out of scope.
</deferred>
