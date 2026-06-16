# Phase 10: Computer-Folder Identity Foundation - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Decisions locked by approved design spec (no interactive discuss — see below)

<domain>
## Phase Boundary

Establish the computer-folder identity model in `update-list.sh`: the top-level
folder name IS the machine identity, every new catalog is named after its folder,
the name-validation rule is a single shared implementation, and `machine-labels.tsv`
is repurposed to map hostname→computer-folder.

This phase is the FOUNDATION for Phases 11 (selection menu + `--computer` flag) and
12 (rename). It lays the identity/validation/map groundwork; the new interactive
`select_computer` menu and CLI flags are Phase 11, and folder rename is Phase 12.

In scope: filename construction uses the resolved folder name as the `[label]`;
shared name-validation helper used by both a fatal (flag) path and a re-prompt
(interactive) path; `machine-labels.tsv` semantics become hostname→computer-folder
with upsert recording this Mac's chosen folder. Out of scope: the new menu UX,
`--computer` flag, and rename (later phases).
</domain>

<decisions>
## Implementation Decisions

**Authoritative source:** `docs/superpowers/specs/2026-06-14-computer-folder-model-design.md`
(approved by the user section-by-section). All decisions below are locked there; the
interactive discuss was intentionally skipped to avoid re-litigating settled choices.

### Identity = folder name (CID-01)
- A new catalog in computer folder `X` is named `mac-software-list-[X]-YYYYMMDDHHMMSS.txt`.
  The `[...]` segment equals the folder name; the raw hostname does not appear.
- Main-block wiring: the resolved computer-folder name feeds `CURRENT_MACHINE`, which is
  used to build `OUTPUT_FILENAME` (the folder name = `TARGET_LOCATION` going forward).

### Name validation (CID-02, CID-03 success criterion 3)
- A computer/folder name is an arbitrary user-chosen string (never hostname-derived).
- Validation rules: non-empty; reject `/`, `[`, `]`, tab, newline, and leading/trailing
  whitespace; allow spaces, apostrophes, letters, digits, `-`, `_`, `.`.
- ONE shared validation implementation backs both paths: the flag path fails fast
  (`exit 1`); the interactive path re-prompts (non-fatal). The existing
  `validate_machine_label` (fatal) + `validate_machine_label_quiet` (returns 1) pair
  already models this — reuse/rename rather than duplicate the rule.

### Map repurposed to hostname→computer-folder (CID-03)
- `machine-labels.tsv` keeps its filename and TSV format (`hostname<TAB>value`), but the
  value now means "the computer folder this Mac uses." Header comment updated to say so.
- On each run, after the computer is resolved, upsert records/updates this Mac's
  hostname→folder so a later run can mark it as the menu default (the default-marking
  itself is Phase 11).

### Transition
- Existing catalogs keep their old `[hostname]` labels; only NEW catalogs use `[folder]`.
  Retroactive alignment is via `--rename` (Phase 12), not this phase.
</decisions>

<code_context>
## Existing Code Insights

### Reusable / to-modify (single file `update-list.sh`)
- `validate_machine_label` (line ~118, fatal) + `validate_machine_label_quiet` (line ~157,
  returns 1) — the shared-validation pair from the v0.49.0-prep quick fix. Phase 10 makes
  these the single source of the rule (rename to `validate_computer_name`* if clearer).
- `upsert_machine_label` (line ~372): writes `${SCRIPT_DIR}/machine-labels.tsv`
  (`hostname<TAB>value`, `.tmp`+`mv` atomic, preserves comments/blanks). Repurpose value
  semantics to "computer folder"; update header comment text.
- Main block filename construction (~line where `CURRENT_MACHINE`/`OUTPUT_FILENAME` are set,
  currently `CURRENT_MACHINE="$MACHINE_LABEL"`): make the resolved folder name the label.
- `resolve_machine_label` (line ~439) / `get_target_location`: Phase 11 replaces these with
  `select_computer`; Phase 10 only needs the identity/filename/map plumbing in place. Keep
  the existing selection working enough that the filename reflects the chosen folder.

### Established patterns
- `#!/bin/zsh`, macOS-only. snake_case, `local`, `[[ ]]`, double-quoted vars,
  `printf`+`read -r`, `[[ ! -t 0 ]]` TTY guard, fail-fast `echo "ERROR:"`+`exit 1`.
- Zsh arrays are 1-indexed (do not introduce off-by-one).
</code_context>

<specifics>
## Specific Ideas

- Example target filename: `mac-software-list-[Example Computer]-YYYYMMDDHHMMSS.txt`.
- `machine-labels.tsv` header comment should describe it as hostname→computer-folder.
- Keep the validation regex idiom proven in the prior fix: reject set `'[][/]'` plus the
  TAB/newline and leading/trailing-whitespace checks.
</specifics>

<deferred>
## Deferred Ideas

- The always-shown `select_computer` menu, `--computer` flag, and Quit option → Phase 11.
- Folder rename + filename rewrite → Phase 12.
- Renaming `machine-labels.tsv` itself → out of scope (spec).
</deferred>
