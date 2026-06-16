# Phase 11: Computer Selection & CLI - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — recommendations grounded in approved design spec + Phase 10 decisions; all 4 grey areas accepted as recommended

<domain>
## Phase Boundary

Replace the v0.48.0 two-step selection (`get_target_location` personal/office menu +
separate `resolve_machine_label` label menu) with a single always-shown
`select_computer` menu, and add the `--computer` flag with back-compat aliases.

In scope:
- `select_computer` function: dynamic list of existing computer folders + "Create new
  computer" + "Quit"; remembered folder marked `(this machine — default)` and used as
  Enter-default; invalid input re-prompts; create-new prompts/validates/creates a folder;
  sets `TARGET_LOCATION` to the chosen folder and upserts the hostname→folder map.
- CLI: `--computer "Name"` (primary, non-interactive select-or-create), `--personal`/
  `--office`/`--machine "X"` as aliases; fail-fast on conflicting selecting-flags.
- Quit on the selection menu exits cleanly (status 0) — no catalog written, no commit.
- Main-block rewire: `select_computer` feeds `CURRENT_MACHINE`/`OUTPUT_FILENAME`.

Out of scope: the rename flow and rename picker (Phase 12 — RNM/QUIT-on-rename-picker);
catalog content; map filename change.

**Authoritative spec:** `docs/superpowers/specs/2026-06-14-computer-folder-model-design.md`
(Run flow — computer selection; CLI surface; Quit on all menus).
</domain>

<decisions>
## Implementation Decisions

### Computer Folder Discovery (Area 1)
- Discover existing computers as the **union** of: top-level dirs containing
  `mac-software-list-*.txt` catalogs, AND values appearing in `machine-labels.tsv`.
  Deduplicate.
- Fully dynamic — do NOT hardcode `personal`/`office` into the menu. They appear only
  if they exist as folders or map values. (Aliases still create them on demand.)
- Infra dirs (`.git`, `.planning`, `.claude`, `.opencode`, `.playwright-mcp`, `docs`)
  are excluded *naturally* by the discovery rule (they hold no catalogs and aren't map
  values) — no separate denylist needed.
- Menu ordering: the remembered "(this machine)" folder first, then the remaining
  computers **alphabetically**.

### Default & Selection Behavior (Area 2)
- "No remembered computer" = **absent** map entry for this hostname (no row). When
  absent there is no Enter-default — the user must pick a number, create, or quit.
- Default marker text is exactly `(this machine — default)`.
- Selecting any existing computer upserts the map to the chosen folder (remembers it
  for next run), even if it differs from the prior remembered folder.
- Non-interactive (no TTY) with no selecting-flag → fail-fast:
  `ERROR: ... pass --computer "Name"`, exit 1. (No auto-pick.)

### Quit & Re-prompt Semantics (Area 3)
- Quit is selectable by its menu number AND by typing `q`/`quit` (case-insensitive).
- Quit exits status 0, prints `No catalog written.`, makes no git commit.
- Invalid input re-prompts indefinitely (matches existing `while true` loops) — no cap.
- EOF (Ctrl-D / closed stdin) at a menu prompt is treated as a clean Quit (exit 0),
  not an infinite loop.

### CLI Flag Semantics (Area 4)
- `--computer "X"`: select existing folder `X`, or create it if missing; validate the
  name with the fatal `validate_computer_name` (exit 1 on invalid). Non-interactive
  (skips the menu).
- `--personal` / `--office`: thin aliases = `--computer personal` / `--computer office`
  (select-or-create).
- `--machine "X"`: silent deprecated alias for `--computer "X"` — no deprecation warning.
- Conflicting selecting-flags (e.g. `--personal --computer "X"`, or two of
  --personal/--office/--computer/--machine): fail-fast error, consistent with the
  existing `--rename`+`--machine` guard.
</decisions>

<code_context>
## Existing Code Insights

### Reusable / to-modify (single file `update-list.sh`, ~2431 lines)
- `validate_computer_name` (~line 118, fatal `exit 1`) + `validate_computer_name_quiet`
  (~line 157, returns 1 + echoes reason) — the shared rule from Phase 10. Use fatal for
  the flag path, quiet for the interactive create-new re-prompt.
- `parse_arguments` (~line 190): currently sets `TARGET_LOCATION` for `--personal`/
  `--office`, validates+stores `MACHINE_LABEL` for `--machine`, has `--rename` short-
  circuit and the `--rename`+`--machine` conflict guard. Extend with `--computer`; make
  the aliases route to a single resolved computer; add the multi-selecting-flag guard.
- `get_target_location` (~line 264): the hardcoded personal/office 2-option menu — to be
  REPLACED by `select_computer`. Has a `[[ ! -t 0 ]]` TTY guard and fail-fast pattern.
- `resolve_machine_label` (~line 439): the separate label menu (hostname-first, map +
  filename label sources, create-new) — to be REMOVED/folded into `select_computer`.
  Its `_label_in_list` dedupe helper and the four-dir glob discovery
  (`personal`, `personal/archive`, `office`, `office/archive`) are reusable patterns,
  but Phase 11 discovers *top-level folders*, not labels.
- `upsert_machine_label` (~line 372): writes `hostname<TAB>TARGET_LOCATION`, atomic
  `.tmp`+`mv`, preserves comments/blanks. Reuse as-is (already records the folder).
- Main block (~line 2374): calls `get_target_location` then `resolve_machine_label`,
  then sets `CURRENT_MACHINE="$TARGET_LOCATION"` / `OUTPUT_FILENAME`. Rewire to a single
  `select_computer` call; Quit must exit before catalog generation / commit.
- `git_commit_and_push` (~line 2297): stages `git add -A "${TARGET_LOCATION}/"` + the map.
  Already folder-scoped — works unchanged for a dynamically chosen folder.
- `display_usage` (~line 67): document `--computer` and the aliases.

### Established patterns
- `#!/bin/zsh`, macOS-only. snake_case, `local`, `[[ ]]`, double-quoted vars,
  `printf`+`read -r`, `[[ ! -t 0 ]]` TTY guard, fail-fast `echo "ERROR:"`+`exit 1`.
- Zsh arrays are 1-indexed — keep the existing 1-indexed menu idiom; avoid off-by-one.
- Source-guard at end of file (`[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`) enables
  isolated function testing via `source`.

### Current state
- `machine-labels.tsv` has header only — no host entries yet (so this Mac has no
  remembered computer; menu must handle the no-default case).
- Existing computer folders: `personal/` (8 catalogs), `office/` (11 catalogs).
</code_context>

<specifics>
## Specific Ideas

- Target menu shape (from spec):
  ```
  Select a computer:

    1) personal   (this machine — default)
    2) office
    3) Create new computer
    4) Quit

  Enter your choice [1-4, or Enter for 1]:
  ```
- When this Mac has no remembered folder: no `(this machine — default)` marker and no
  Enter-default — the prompt must not silently default to choice 1.
- Create-new: prompt for a name, re-prompt on invalid (via `validate_computer_name_quiet`),
  `mkdir -p` the folder, set it as `TARGET_LOCATION`, upsert the map.
</specifics>

<deferred>
## Deferred Ideas

- Rename flow + rename picker (with its own Quit) → Phase 12 (RNM-01/02/03).
- Retroactive filename alignment of existing `[hostname]` catalogs → Phase 12 rename.
</deferred>
