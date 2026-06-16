# Phase 8: Machine Identity - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase replaces the raw `$(hostname)` value in the catalog filename's `[...]`
segment with a human-readable machine label chosen by the user, and makes each Mac
remember its label across runs via a committed hostname→label map.

Label resolution order: `--machine "Label"` flag → saved map entry for this hostname
→ interactive numbered menu (with a "create new" option) for machines not yet in the map.

Scope: new `--machine` flag + value validation; a committed map file at the repo root;
a `resolve_machine_label` function (flag/map/menu paths, TTY-guarded); and wiring the
resolved label into `OUTPUT_FILENAME`. It does NOT rename existing catalog files (that
is Phase 9) and does NOT change the retention/prune algorithms beyond confirming they
still parse a `[label]` segment that may contain spaces.

</domain>

<decisions>
## Implementation Decisions

### Map File
- Filename: `machine-labels.tsv` at the repo root, committed and git-tracked (this is the
  tool's first self-state file, distinct from catalogs).
- Format: one line per machine, `hostname<TAB>label` (TAB-delimited because labels contain
  spaces, e.g. `Example Computer`).
- Comments: lines beginning with `#` and blank lines are allowed and skipped when reading.
- A missing or empty map means "no machines known yet" — the first run on any machine
  prompts via the menu (does NOT error).

### Label Resolution & `--machine` Semantics
- Precedence: `--machine` flag > saved map entry for this hostname > interactive menu.
- `--machine "X"` PERSISTS: upsert this hostname→X into the map so subsequent runs
  auto-resolve without prompting (satisfies MID-04's "remembers automatically").
- If a saved entry already exists and `--machine` supplies a different label, update the
  map entry to the new label (a lightweight per-host rename; full multi-file rename is Phase 9).
- Non-interactive run (no TTY) with no `--machine` flag and no saved entry: fail fast with an
  actionable error (e.g. `ERROR: No machine label resolved and stdin is not a TTY. Pass --machine "Label".`).
  Do NOT silently fall back to the raw hostname.

### Interactive Menu & Label Validation
- Menu: numbered list of the distinct labels currently in the map, plus a "create new" option
  (satisfies MID-02).
- "Create new": prompt for the label text, then save hostname→label to the map.
- Label validation: non-empty; reject `/`, `[`, `]`, and leading/trailing whitespace; allow
  spaces, apostrophes, letters, digits, `-`, `_`, `.`. (These keep the `[...]` filename segment
  and the filesystem path safe while permitting natural labels like `Example Computer`.)
- Persist on every menu resolution — both "create new" and selecting an existing label for THIS
  hostname write the hostname→label mapping, so future runs on this machine auto-resolve.

### Filename Integration & Backward Compatibility
- A new `resolve_machine_label` function sets the run's label; the value flows into
  `OUTPUT_FILENAME` in place of the current `CURRENT_MACHINE=$(hostname)` usage. Resolution is
  front-loaded in the main block alongside the location and retention prompts (TTY-guarded), and
  runs before `git_pull`/filename construction.
- Existing raw-hostname-named catalog files are left untouched. Only NEW files use the label.
  Bulk renaming of historical files is explicitly Phase 9's job.
- The retention sweep (`retain_newest_per_host`) and prune must continue to parse the `[label]`
  segment generically as the host key, including labels that contain spaces. The existing
  `${tmp%\]-*}` / `${filename#*\[}` extraction already handles spaces — planning must confirm
  no regression (a label with spaces still groups correctly per machine).
- The menu read is TTY-guarded the same way the location and retention prompts are.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Main block (lines ~1777-1779): `CURRENT_DATE=$(date ...)`, `CURRENT_MACHINE=$(hostname)`,
  `OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"` — the single
  integration point for the label.
- `get_target_location` (line ~160) and `resolve_archive_retention` (line ~220, added in Phase 7)
  — established `printf` + `read -r` + `case`/validate prompt patterns, plus the `[[ ! -t 0 ]]`
  TTY guard idiom to mirror for the menu.
- `parse_arguments` (line ~108): `while`/`case` flag loop; add a `--machine)` case that consumes
  a value (needs a second `shift` and `[[ -z "$2" ]]` empty-check, exactly like `--archive-days`).
- `retain_newest_per_host` (line ~255): label/host extraction via `local tmp="${filename#*\[}"`,
  `local host="${tmp%\]-*}"` — the parser that must keep working with space-containing labels.
- `display_usage` (line ~76): synopsis + flag list to extend with `--machine`.

### Established Patterns
- Globals set in main, consumed by functions. Fatal arg errors: `echo "ERROR: ..."` + `exit 1`.
- `local` for function-scoped vars; `[[ ]]` conditionals; double-quoted variables; `command -v`.
- Zsh-specific: `${0:A:h}`, `${file:t}` modifiers, `setopt local_options null_glob` for glob loops.

### Integration Points
- New `--machine` case in `parse_arguments`.
- New `resolve_machine_label` function (flag/map/menu) invoked from the main block after
  `resolve_archive_retention`, before filename construction.
- New map file `machine-labels.tsv` at repo root — read by `resolve_machine_label`, written on
  upsert. Phase 9 will also read/write this same map.
- `OUTPUT_FILENAME` uses the resolved label instead of `$(hostname)`.

</code_context>

<specifics>
## Specific Ideas

- Map path: `${SCRIPT_DIR}/machine-labels.tsv` (SCRIPT_DIR is the repo root via `${0:A:h}`).
- The map is the shared data source for Phase 9's `--rename` enumeration — keep the read/parse
  logic in a form Phase 9 can reuse (e.g. a helper that lists labels, or a documented format).
- Commit the map whenever it changes (new mapping or updated label), as part of the run's normal
  git flow — the map is tracked so other machines converge on pull.
- Example target filename: `mac-software-list-[Example Computer]-YYYYMMDDHHMMSS.txt`.

</specifics>

<deferred>
## Deferred Ideas

- Bulk renaming existing catalog files across `personal/`, `personal/archive/`, `office/`,
  `office/archive/` — that is Phase 9 (`--rename`).
- No persisted config beyond the hostname→label map (retention period stays runtime-only per Phase 7).

</deferred>
