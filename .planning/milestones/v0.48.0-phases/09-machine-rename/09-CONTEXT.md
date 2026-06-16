# Phase 9: Machine Rename - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds a `--rename` execution mode that rewrites a machine label everywhere
it appears — every catalog file in `personal/`, `personal/archive/`, `office/`, and
`office/archive/` — in a single self-committing operation, and updates the
hostname→label map so other machines converge on `git pull`.

`--rename` is a SEPARATE mode, not a catalog run: it short-circuits the normal flow
(no location prompt, no retention prompt, no catalog generation, no retention/prune).
It only moves files and updates the map.

Scope: a `--rename` flag, a `rename_machine` function (enumerate old-label candidates →
interactive pick of OLD → validated prompt for NEW → rename across 4 dirs → update map →
single commit/push), reusing the Phase 8 `validate_machine_label` helper and the existing
git-add-all staging pattern. It does NOT change catalog generation or retention logic.

</domain>

<decisions>
## Implementation Decisions

### Invocation & Mode Flow
- New `--rename` flag in `parse_arguments` sets `RENAME_MODE=true`. The main block detects it,
  runs `rename_machine`, and exits — skipping `get_target_location`, `resolve_archive_retention`,
  `resolve_machine_label`, `generate_catalog`, `retain_newest_per_host`, and `prune_old_archives`.
- `--rename` does NOT require `--personal`/`--office`; it always operates on all four directories.
- Interactive: present a numbered menu to pick the OLD label, then prompt for the NEW label
  (matches SC #1). Non-interactive (no TTY) → fail fast with an actionable error.
- Run `git_pull` before mutating files, so the rename converges with remote first (consistent
  with the normal run's pull-first behavior).

### What Gets Renamed & Matching
- OLD-label candidates = the union of (a) labels present in `machine-labels.tsv` and (b) distinct
  `[...]` segments discovered across the four directories. This makes the two existing
  cryptic-hostname machines (`computer-one.local`, `computer-two.local`) renamable
  even though they predate the map (SC #4).
- File match → rename: `mac-software-list-[OLD]-<timestamp>.txt` →
  `mac-software-list-[NEW]-<timestamp>.txt`, preserving the 14-digit timestamp, in all four dirs.
- All four directories are scanned with null-glob guards (`setopt local_options null_glob`);
  missing or empty dirs are skipped gracefully (same pattern as `retain_newest_per_host`).
- Destination-filename collision (a `[NEW]-<ts>.txt` already exists): warn and skip THAT file
  (never overwrite), continue with the rest, and report the skipped count.

### Map Update & New-Label Validation
- Update every map entry whose label equals OLD to NEW (SC #2). Handles the case of multiple
  hostnames sharing the old label.
- Validate the NEW label by reusing the Phase 8 `validate_machine_label` helper (rejects `/`,
  `[`, `]`, interior TAB/newline, and leading/trailing whitespace; allows spaces, apostrophes,
  letters, digits, `-` `_` `.`).
- NEW == OLD: no-op — warn and exit without committing.
- NEW collides with a DIFFERENT existing machine's label: warn prominently but proceed (explicit
  user intent; per-file timestamps keep the merged history distinct, so no data loss).

### Git Commit & No-Match Safety
- Staging: `mv` files on disk, then `git add -A personal/ office/` plus
  `git add machine-labels.tsv` (handles tracked deletes/adds and any untracked files uniformly;
  reuses the existing `git_commit_and_push` staging pattern).
- All renames + the map update are staged together and pushed in ONE commit (REN-02, SC #3).
  The commit message states the OLD→NEW rename and the number of files renamed.
- No matching files in ANY of the four directories: print a clear warning and exit WITHOUT
  modifying the map and WITHOUT creating a commit (SC #5).
- Honor `--no-commit` when combined with `--rename`: perform the renames + map update on disk,
  skip the commit/push, and print the manual commit instructions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_arguments` (line ~150): `while`/`case` flag loop — add a `--rename)` case that sets
  `RENAME_MODE=true` (a value-less flag like `--no-commit`).
- `validate_machine_label` (line ~112, Phase 8): reuse verbatim for the NEW label.
- `resolve_machine_label`'s map read + menu code (Phase 8, lines ~397-478): the TSV read loop
  (`while IFS=$'\t' read -r h l || [[ -n "$h" ]]`) and numbered-menu pattern are the template for
  enumerating OLD-label candidates and the interactive picker.
- `retain_newest_per_host` (line ~498): the `[label]` extraction idiom
  (`local tmp="${filename#*\[}"; local host="${tmp%\]-*}"`) for parsing the label segment, and
  the `setopt local_options null_glob` + `for file in "$dir"/mac-software-list-*.txt` glob loop
  with `[[ -e "$file" ]] || continue` guards — the exact pattern to reuse across the 4 dirs.
- `git_commit_and_push` (line ~1928): `git add -A "${TARGET_LOCATION}/"` + `git add machine-labels.tsv`
  staging pattern, `git diff --cached --quiet` empty-check, commit + push with warn-on-failure.
  rename_machine needs its own scoped commit (all 4 dirs) — model on this function.
- `git_pull` (line ~1898 area): reuse before the rename.
- Main block (lines ~2003-2047): the orchestration sequence to short-circuit when RENAME_MODE.
- `display_usage` (line ~76): add `--rename` to the synopsis + flag list.

### Established Patterns
- Globals set in main / parse_arguments, consumed by functions. `local` for fn-scoped vars.
- Fatal errors: `echo "ERROR: ..."` + `exit 1`. `printf` + `read -r` prompts, `[[ ! -t 0 ]]` TTY guard.
- `[[ ]]` conditionals; double-quoted vars; null-glob guards in every glob loop.
- The four directories: `${SCRIPT_DIR}/personal`, `${SCRIPT_DIR}/personal/archive`,
  `${SCRIPT_DIR}/office`, `${SCRIPT_DIR}/office/archive`.

### Integration Points
- New `--rename` case in `parse_arguments` (sets `RENAME_MODE=true`, default false).
- New `rename_machine` function (enumerate → pick OLD → validate NEW → rename 4 dirs → update map → commit).
- Reads/writes `machine-labels.tsv` (shared with Phase 8).
- Main block: `if [[ "$RENAME_MODE" == "true" ]]; then git_pull; rename_machine; exit 0; fi` placed
  after `parse_arguments`, before `get_target_location`.

</code_context>

<specifics>
## Specific Ideas

- Four dirs as an array: `local dirs=("personal" "personal/archive" "office" "office/archive")`.
- The two existing cryptic machines to validate against (SC #4): `computer-one.local`
  and `computer-two.local` — renaming either must produce consistent `[NewLabel]` filenames in all
  locations where that machine's files exist.
- Reuse the map-write atomic pattern from Phase 8's `upsert_machine_label` (`.tmp` + `mv`,
  preserve comments/blank lines) when rewriting label entries.
- Commit message example: `Rename machine label: 'OLD' -> 'NEW' (N files across personal/office)`.

## ⚠️ Testing hazard (CRITICAL for planning + execution)
Running `update-list.sh` in `--rename` mode MOVES real catalog files across all four directories
and (without `--no-commit`) commits + pushes. Running it in normal mode generates catalogs and
HARD-DELETES archive files via the prune pass. Acceptance criteria MUST be source assertions and
`zsh -n` checks, NOT live `--rename` runs against the real repo. If a behavioral test of the rename
logic is needed, it must run against a throwaway temp fixture directory (a scratch copy with dummy
`mac-software-list-[...]*.txt` files), never the repo's real `personal/`/`office/` trees.

</specifics>

<deferred>
## Deferred Ideas

- No undo/rollback mode for a rename (git history is the recovery path).
- No batch rename of multiple machines in one invocation — one OLD→NEW per run.

</deferred>
