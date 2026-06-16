# Design: Computer-folder model for `update-list.sh`

**Date:** 2026-06-14
**Status:** Approved (design); pending implementation via a new GSD milestone
**Author:** brainstormed with Ken

## Problem

Today `personal/` and `office/` are treated as "save locations," and machine
identity is a separate concept layered on top (the `[label]` segment in each
filename, resolved via the `--machine` flag, the `machine-labels.tsv`
hostname→label map, and an interactive label menu added in v0.48.0). The user's
actual mental model is different: **each top-level folder represents a computer
being cataloged.** The user wants to choose an existing computer or designate a
new one, rename a computer (the folder), and have catalog filenames correspond
to the folder they live in. The separate machine-label concept is redundant with
this and should collapse into it.

## Approved Decisions

1. **Collapse to one concept (Q1-A).** The folder name *is* the computer
   identity. The filename `[label]` mirrors the folder name. The label
   menu/`--machine`/map system is repurposed to the folder model rather than
   kept as a parallel concept.
2. **Always show the computer menu, pre-selected (Q2-B).** Every interactive run
   shows the computer menu; the computer remembered for this Mac is the default
   (Enter accepts it). This replaces silent auto-resolution.
3. **Rename rewrites contained files by default, with an opt-out (Q3-A default,
   Q3-B offered).** Renaming a computer rewrites every catalog inside it to the
   new name by default; the user may choose to leave existing filenames and only
   apply the new name going forward.
4. **One `--computer` flag with back-compat aliases (Q4-A).** `--computer "Name"`
   is the primary flag; `--personal`/`--office` become thin aliases; `--machine`
   becomes a silent deprecated alias for `--computer`.

## Model

- A **computer** = a top-level folder under the repo root (`personal/`,
  `office/`, plus any the user creates). The folder name is the machine identity.
- **The folder/computer name is an arbitrary, user-chosen string** (e.g.
  `personal`, `office`, `Example Computer`, `Gaming Rig`) — it is NOT derived
  from, or required to match, the actual hostname. The script never auto-names a
  folder from the hostname; the user always types the name when creating or
  renaming a computer. The hostname→folder map only records which user-chosen
  folder a given physical Mac last used, to set the menu default.
- New catalogs in folder `X` are named `mac-software-list-[X]-YYYYMMDDHHMMSS.txt`
  — the `[label]` segment always equals the folder name.
- `machine-labels.tsv` is repurposed as a committed **hostname → computer-folder**
  map (same TSV format `hostname<TAB>computer`; header comment updated). It lets
  each physical Mac remember which computer it is, used to mark/select the menu
  default. **Filename kept** (`machine-labels.tsv`) to avoid extra churn.

## Run flow — computer selection (always interactive unless a flag is given)

```
Select a computer:

  1) personal   (this machine — default)
  2) office
  3) Create new computer
  4) Quit

Enter your choice [1-4, or Enter for 1]:
```

- Lists existing computer folders (the four-dir/location discovery generalizes to
  "top-level catalog folders"). The folder remembered for this hostname is marked
  `(this machine — default)` and is the Enter default. If this Mac has no
  remembered folder, there is no Enter default — the user must pick a number,
  create, or quit.
- **Create new computer** → prompt for a name (validated; re-prompt on invalid
  input, do not exit), create the folder, record hostname→folder in the map.
- **Quit** → exit cleanly (status 0); nothing written or committed.
- Invalid input → re-prompt (loop), never `exit 1` mid-menu.
- The chosen computer is saved as this Mac's remembered default for next time.
- Selecting an existing computer whose hostname mapping differs updates the map
  entry for this hostname to the chosen folder.

## `--rename` — rename a computer (the folder)

```
Select the computer to rename:
  1) personal
  2) office
  3) Quit

Enter your choice [1-3]:
```

→ enter new name (validated; re-prompt on invalid) →
`Rewrite all existing catalogs in 'personal' to '[NewName]'? [Y/n]:`

- Renames the folder `personal/` → `NewName/`; its `archive/` subfolder moves with it.
- **Y (default):** rewrite every catalog inside (main + `archive/`) so its
  `[label]` becomes `[NewName]`, preserving the 14-digit timestamp, skipping
  destination collisions (warn + skip, never overwrite).
- **n:** rename the folder only; existing filenames keep their old `[label]`.
- Update every `hostname → personal` entry in the map to `hostname → NewName`.
- Stage folder moves + filename rewrites + map update and commit/push in a
  **single commit** (honor `--no-commit`, print manual instructions).
- No-match / no-op guards: NEW == OLD → warn + exit; folder not found → warn + exit
  without committing.
- TTY-guarded (rename requires an interactive terminal). Quit option in the picker.

## CLI surface

- `--computer "Name"` — select or create that computer non-interactively (skips menu).
- `--personal` / `--office` — thin aliases for `--computer personal` / `--computer office`.
- `--machine "X"` — silent deprecated alias for `--computer "X"`.
- `--rename` — rename-a-computer mode (short-circuits before catalog generation).
- `--archive-days N`, `--no-commit` — unchanged.

## Name validation (shared)

A computer name is both a directory name and a filename `[segment]`, so it must be
safe for both. Rules (reuse/extend the existing `validate_machine_label`):
non-empty; reject `/`, `[`, `]`, tab, newline; reject leading/trailing whitespace;
allow spaces, apostrophes, letters, digits, `-`, `_`, `.`. Interactive prompts
re-prompt on violation; the `--computer`/alias flag paths fail fast (exit 1).
Creating a name that matches an existing computer simply selects it (no error).

## Quit on all menus (separate request)

Every interactive numbered menu (computer selection, rename picker) includes a
**Quit** option (numbered, and also accepts `q`/`quit`). Choosing it exits cleanly
(status 0) with nothing written or committed.

## Filenames, retention, transition

- New catalogs use `[folder]` as the label (the main-block sets
  `CURRENT_MACHINE` = selected computer name before constructing `OUTPUT_FILENAME`).
- Retention (`retain_newest_per_host`) and prune are unchanged mechanically; they
  group by the `[label]` segment. Once a folder's files all share `[folder]`,
  "newest per machine" keeps the single newest catalog per computer.
- **Transition:** existing catalogs keep their old `[hostname]` labels until aligned
  via a rename with the Y (rewrite-all) option — not auto-migrated. New catalogs
  immediately use `[folder]`. During the mixed period, retention treats each
  distinct label as its own "machine" (keeps newest of each) — documented, benign.

## Components touched (existing single file `update-list.sh`)

- `get_target_location` → replaced by a `select_computer` function (dynamic folder
  list + create-new + quit + remembered default).
- `resolve_machine_label` → removed/folded into `select_computer` (folder name is
  the label).
- `rename_machine` → reworked to rename a folder (+ optional filename rewrite +
  map update + single commit).
- `parse_arguments` → `--computer` plus aliases (`--personal`/`--office`/`--machine`);
  `--rename` short-circuit unchanged in spirit.
- Main block → folder selection feeds `CURRENT_MACHINE`/`OUTPUT_FILENAME`; folder
  is the `TARGET_LOCATION`.
- `git_commit_and_push` / rename commit → stage the selected computer folder (and,
  for rename, both the old and new folder paths) rather than the fixed
  `personal`/`office` pair.
- `display_usage`, README → updated for the new flags and model.
- Validation helper(s) shared between flag (fatal) and interactive (re-prompt) paths.

## Out of scope

- Auto-migrating existing mixed-label files on a normal run (only via explicit rename).
- Renaming the `machine-labels.tsv` file itself.
- Any change to catalog *content* (the software sections are untouched).

## Testing constraints (CRITICAL)

`update-list.sh` is destructive to run: a normal run generates catalogs and
hard-deletes archives; `--rename` moves real files and commits. All verification
must use `zsh -n`, source/grep assertions, and isolated function tests against
throwaway `mktemp -d` fixtures — **never** a live run against the repo's real
`personal/`/`office/` trees.
