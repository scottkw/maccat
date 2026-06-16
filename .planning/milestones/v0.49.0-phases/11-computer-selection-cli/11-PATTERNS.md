# Phase 11: Computer Selection & CLI - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 1 (single-file Zsh script `update-list.sh`, ~2431 lines — all changes are in-file)
**Analogs found:** 6 / 6 (every new/modified unit has a same-file analog)

> All work happens inside `/Users/ken/dev/mac-software-list/update-list.sh`. There are no
> new files. "Analog" below means the closest existing **function or block in the same file**
> whose structure the new code should copy. Line numbers are as of the read at mapping time.

## File Classification

| New/Modified Unit | Role | Data Flow | Closest Analog (same file) | Match Quality |
|-------------------|------|-----------|----------------------------|---------------|
| `select_computer` (NEW fn, replaces 2 fns) | interactive resolver / menu | request-response (read stdin → set globals) | `resolve_machine_label` (line 439) + `get_target_location` (line 264) | exact (folds both) |
| Computer-folder discovery (NEW block, inside `select_computer`) | discovery / dedupe | transform (filesystem + map → array) | label discovery in `resolve_machine_label` lines 478-519 | role-match (folders not labels) |
| `--computer` flag + aliases (modify `parse_arguments` line 190) | CLI arg parser | request-response | existing `--machine` / `--personal` / `--office` cases + `--rename`/`--machine` guard (lines 194-248) | exact |
| Map default-marking / lookup (inside `select_computer`) | persistence read | CRUD (read TSV) | map-lookup loop in `resolve_machine_label` lines 447-467 | exact |
| Map upsert on selection (inside `select_computer`) | persistence write | CRUD (write TSV) | `upsert_machine_label` (line 372) — **reuse as-is** | exact (no change) |
| Quit handling + EOF (inside `select_computer`) | control flow | event-driven (input → clean exit) | `while true` re-prompt loop lines 536-547 + `[[ ! -t 0 ]]` guards lines 274/470 | role-match (new clean-exit semantics) |
| Main-block rewire (line 2374-2391) | orchestration | sequence | current `get_target_location` → `resolve_machine_label` → `CURRENT_MACHINE=...` sequence | exact |

## Pattern Assignments

### `select_computer` (NEW function — replaces `get_target_location` + `resolve_machine_label`)

**Primary analog:** `resolve_machine_label` (lines 439-570). Copy its overall shape:
flag-path fast-exit → map-lookup → TTY guard → interactive menu (numbered, 1-indexed,
re-prompt loop) → create-new branch → upsert. **Secondary analog:** `get_target_location`
(lines 264-305) for the simple TTY-guard + arg-already-set short-circuit.

#### Pattern A — "value already set by flag" short-circuit (analog `get_target_location` lines 266-269, and `resolve_machine_label` lines 441-445)

```zsh
    # Flag path: --computer/alias resolved TARGET_LOCATION in parse_arguments.
    if [[ -n "$TARGET_LOCATION" ]]; then
        mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"   # select-or-create semantics
        upsert_machine_label
        echo "Computer: ${TARGET_LOCATION} (from command-line argument)"
        return
    fi
```
Note: Phase 11 spec says `--computer` is **select-or-create**, so the flag path must
`mkdir -p` the folder (the analog `resolve_machine_label` did not, because labels are not
folders). It must also `upsert_machine_label` to remember the choice (analog line 442).

#### Pattern B — map lookup to find this host's remembered folder (analog lines 447-467)

```zsh
    local map_file="${SCRIPT_DIR}/machine-labels.tsv"
    local current_host=$(hostname)
    local saved_folder=""

    if [[ -f "$map_file" ]]; then
        while IFS=$'\t' read -r map_host map_label || [[ -n "$map_host" ]]; do
            [[ "$map_host" =~ ^# ]] && continue    # skip comment lines
            [[ -z "$map_host" ]] && continue        # skip blank lines
            if [[ "$map_host" == "$current_host" ]]; then
                saved_folder="$map_label"
                break
            fi
        done < "$map_file"
    fi
```
Per CONTEXT Area 2: an **absent** row = no remembered computer ⇒ `saved_folder=""` ⇒ no
Enter-default and no `(this machine — default)` marker. Do NOT fast-exit on a found
map entry (the old `resolve_machine_label` lines 463-467 did — Phase 11 spec says the
menu is **always shown**; the saved folder is only the highlighted default).

#### Pattern C — TTY guard / fail-fast for non-interactive (analog lines 274-277 and 470-473)

```zsh
    if [[ ! -t 0 ]]; then
        echo "ERROR: No computer selected and stdin is not a TTY. Pass --computer \"Name\"."
        exit 1
    fi
```
Matches CONTEXT Area 2 fail-fast wording requirement (`pass --computer "Name"`).

#### Pattern D — discovery block: build the computer list (analog lines 476-519, generalized to FOLDERS)

The analog discovers *labels* from three sources (hostname, map labels, filename
`[label]` segments across four dirs). Phase 11 discovers **top-level folders** =
**union of** (a) top-level dirs containing `mac-software-list-*.txt`, (b) map values.
Reuse the `_label_in_list` dedupe helper verbatim (lines 482-490) and the null-glob +
`[[ -e ]]` guards (lines 508-512).

Analog helper to copy verbatim (lines 482-490):
```zsh
    _name_in_list() {
        local candidate="$1"
        local existing
        for existing in "${computers[@]}"; do
            [[ "$existing" == "$candidate" ]] && return 0
        done
        return 1
    }
```

Analog null-glob + entry guards to copy (lines 508-512) — but iterate **top-level dirs**
and test "does this dir contain catalogs", not "parse a label from each filename":
```zsh
    setopt local_options null_glob
    typeset -a computers=()
    local d
    for d in "${SCRIPT_DIR}"/*(/N); do          # (/N) = dirs only, null-glob — zsh glob qualifier
        local base="${d:t}"
        # include only if it holds at least one catalog
        local f
        for f in "${d}"/mac-software-list-*.txt; do
            [[ -e "$f" ]] || continue
            _name_in_list "$base" || computers+=("$base")
            break
        done
    done
    # Source b: folders named as map values (even if empty / not yet created on disk)
    if [[ -f "$map_file" ]]; then
        while IFS=$'\t' read -r map_host map_label || [[ -n "$map_host" ]]; do
            [[ "$map_host" =~ ^# ]] && continue
            [[ -z "$map_host" || -z "$map_label" ]] && continue
            _name_in_list "$map_label" || computers+=("$map_label")
        done < "$map_file"
    fi
```
Per CONTEXT Area 1: infra dirs (`.git`, `.planning`, `.claude`, `.opencode`,
`.playwright-mcp`, `docs`) are excluded **naturally** (they hold no catalogs and aren't
map values) — no denylist. The analog's four hardcoded dirs
(`personal`, `personal/archive`, `office`, `office/archive`, line 503) are **replaced**
by a dynamic top-level scan; do NOT hardcode `personal`/`office`.

**Ordering (CONTEXT Area 1):** remembered "(this machine)" folder first, then the rest
**alphabetically**. The analog put hostname at `labels[1]` unconditionally; Phase 11
instead sorts the discovered set and promotes `saved_folder` to front if present. Use
zsh array sort: `computers=("${(@on)computers}")` (`o`=sort, `n`=numeric-aware) or
`(@o)` for plain lexical, then move `saved_folder` to index 1 if non-empty.

#### Pattern E — numbered menu + default marker (analog lines 521-547)

```zsh
    local create_new_idx=$(( ${#computers[@]} + 1 ))
    local quit_idx=$(( ${#computers[@]} + 2 ))

    echo ""
    echo "Select a computer:"
    echo ""
    local i=1
    while (( i <= ${#computers[@]} )); do
        if [[ -n "$saved_folder" && "${computers[$i]}" == "$saved_folder" ]]; then
            echo "  ${i}) ${computers[$i]}   (this machine — default)"
        else
            echo "  ${i}) ${computers[$i]}"
        fi
        ((i++))
    done
    echo "  ${create_new_idx}) Create new computer"
    echo "  ${quit_idx}) Quit"
    echo ""
```
Marker text is exactly `(this machine — default)` (CONTEXT Area 2 — note the em-dash `—`,
matching the existing source-spec line). Arrays are **1-indexed** (analog comment line 564);
keep `local i=1`/`i=2` idioms and avoid off-by-one against `create_new_idx`/`quit_idx`.

#### Pattern F — input loop with Enter-default + Quit-by-word + EOF-as-quit (analog `while true` lines 536-547)

The analog loop (lines 536-547) re-prompts on invalid and treats empty input as choice 1
unconditionally. Phase 11 must: (1) only allow Enter-default when `saved_folder` is set;
(2) accept `q`/`quit` (case-insensitive) as Quit; (3) treat EOF (`read -r` returns
non-zero) as a clean Quit.

```zsh
    local choice
    while true; do
        if [[ -n "$saved_folder" ]]; then
            printf "Enter your choice [1-${quit_idx}, or Enter for the default]: "
        else
            printf "Enter your choice [1-${quit_idx}]: "
        fi
        if ! read -r choice; then        # EOF (Ctrl-D / closed stdin) → clean quit
            choice="$quit_idx"
        fi
        # case-insensitive q / quit
        local lc="${choice:l}"           # zsh :l = lowercase modifier
        if [[ "$lc" == "q" || "$lc" == "quit" ]]; then
            choice="$quit_idx"
        fi
        if [[ -z "$choice" ]]; then
            if [[ -n "$saved_folder" ]]; then
                # resolve default to its menu index
                local k=1
                while (( k <= ${#computers[@]} )); do
                    [[ "${computers[$k]}" == "$saved_folder" ]] && { choice="$k"; break; }
                    ((k++))
                done
                break
            fi
            echo "ERROR: No default for this machine — please enter a number."
            continue
        fi
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= quit_idx )); then
            break
        fi
        echo "ERROR: Invalid choice '${choice}'. Please enter 1-${quit_idx}."
    done
```
CONTEXT Area 3: invalid input re-prompts **indefinitely** (no cap — matches analog).
EOF and `q`/`quit` map to Quit. `${var:l}` is the zsh lowercase parameter modifier
(consistent with the file's use of `${file:t}` / `${0:A:h}` zsh modifiers).

#### Pattern G — branch on choice: Quit / Create-new / Select (analog lines 549-566)

```zsh
    if (( choice == quit_idx )); then
        echo "No catalog written."
        exit 0                                   # clean quit per CONTEXT Area 3
    elif (( choice == create_new_idx )); then
        # Create-new re-prompt loop — copy analog lines 549-562 verbatim in spirit
        local new_name reason
        while true; do
            printf "Enter a name for the new computer: "
            if ! read -r new_name; then          # EOF during create → clean quit
                echo "No catalog written."
                exit 0
            fi
            reason=$(validate_computer_name_quiet "$new_name")
            if [[ $? -eq 0 ]]; then
                break
            fi
            echo "$reason"
        done
        TARGET_LOCATION="$new_name"
        mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"
    else
        # Select existing (1-indexed)
        TARGET_LOCATION="${computers[$choice]}"
    fi

    echo "Computer: ${TARGET_LOCATION}"
    upsert_machine_label                          # remember choice for next run
```
Create-new re-prompt loop is a direct copy of analog lines 549-562 (uses
`validate_computer_name_quiet` + `$?` check + echo reason + loop). On any selection,
`upsert_machine_label` is called (CONTEXT Area 2: selecting any computer updates the map,
even if it differs from the prior remembered folder) — exactly the analog's line-569 call.

> **Removal note:** `get_target_location` (264-305) and `resolve_machine_label` (439-570)
> are both DELETED. `_label_in_list` only exists inside `resolve_machine_label`; if reused
> in `select_computer` give it a local copy (helper functions defined inside a removed
> function disappear with it).

---

### `--computer` flag + aliases (modify `parse_arguments`, lines 190-249)

**Analog:** the existing `case` arms (lines 194-238) and the post-loop conflict guard
(lines 245-248).

**Existing `--machine` arm to copy for value-taking flags (lines 220-229):**
```zsh
            --machine)
                if [[ -z "$2" || "$2" == --* ]]; then
                    echo "ERROR: --machine requires a value"
                    exit 1
                fi
                local val="$2"
                validate_computer_name "$val"
                MACHINE_LABEL="$val"
                shift 2
                ;;
```

**Existing alias arms to repoint (lines 194-201):**
```zsh
            --personal)
                TARGET_LOCATION="personal"
                shift
                ;;
            --office)
                TARGET_LOCATION="office"
                shift
                ;;
```

**Phase 11 changes (CONTEXT Area 4):**
- Add a `--computer` arm modeled on the `--machine` arm above: require a value, call the
  **fatal** `validate_computer_name "$val"` (line 226 pattern), then set
  `TARGET_LOCATION="$val"` (NOT `MACHINE_LABEL` — folder name is the identity now).
- `--personal` / `--office` already set `TARGET_LOCATION` — they become the aliases for
  free; keep them.
- `--machine "X"` becomes a **silent** alias: set `TARGET_LOCATION="$val"` (same body as
  `--computer`), no deprecation warning (CONTEXT Area 4). Keep the validation.
- Add a **multi-selecting-flag guard** modeled on the existing `--rename`+`--machine`
  guard (lines 245-248). Since `--personal`/`--office`/`--computer`/`--machine` now all
  write the SAME global (`TARGET_LOCATION`), detect conflicts by counting selecting-flags
  seen, e.g. a `local selecting_flags_seen=0` counter incremented in each selecting arm,
  then after the loop:
  ```zsh
      if (( selecting_flags_seen > 1 )); then
          echo "ERROR: --personal, --office, --computer, and --machine are mutually exclusive."
          exit 1
      fi
  ```
  (Mirrors the fail-fast style of lines 245-248: post-loop check, `echo "ERROR:"`, `exit 1`.)
- Update the invalid-option message (line 236) to add `--computer` to the valid list.

**Existing post-loop guard to extend (lines 245-248):**
```zsh
    if [[ "$RENAME_MODE" == "true" && -n "$MACHINE_LABEL" ]]; then
        echo "ERROR: --rename cannot be combined with --machine. ..."
        exit 1
    fi
```
Since `--machine` now sets `TARGET_LOCATION`, update this guard to check
`-n "$TARGET_LOCATION"` instead of `-n "$MACHINE_LABEL"` so `--rename --computer X`
(and the aliases) is also rejected.

---

### Main-block rewire (lines 2374-2391)

**Analog (current sequence to replace):**
```zsh
# Determine the target location (prompts if not set via arguments)
get_target_location

# Resolve archive retention period (flag or interactive prompt)
resolve_archive_retention

# Resolve machine label (flag, saved map, or interactive menu)
resolve_machine_label

...
CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
CURRENT_MACHINE="$TARGET_LOCATION"
OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"
```

**Phase 11 rewrite:** replace the two calls `get_target_location` + `resolve_machine_label`
with a single `select_computer` call. Order matters — Quit must exit (in `select_computer`,
Pattern G) **before** `generate_catalog` (line 2400) and `git_commit_and_push` (line 2419),
so place `select_computer` early. `resolve_archive_retention` (line 2378) stays. The
`CURRENT_MACHINE="$TARGET_LOCATION"` line (2390) is unchanged — `select_computer` sets
`TARGET_LOCATION` to the folder, and the folder name IS the label, so the filename
construction (line 2391) already produces `mac-software-list-[folder]-...txt`.

```zsh
# Select the computer folder (always-shown menu, or resolved from flags).
# Quit inside select_computer exits 0 before any catalog/commit work.
select_computer

resolve_archive_retention
git_pull
CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
CURRENT_MACHINE="$TARGET_LOCATION"
OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"
```

---

## Shared Patterns (established Zsh conventions to replicate)

### Validation (fatal vs. quiet) — already built in Phase 10
**Source:** `validate_computer_name` (line 118, `exit 1`) and `validate_computer_name_quiet`
(line 157, `return 1` + echoes reason to stdout).
**Apply to:** flag path (`--computer`/aliases) uses the **fatal** one (analog `--machine`
line 226); interactive create-new uses the **quiet** one in a re-prompt loop (analog
lines 556-560). Do not write a new validator.

### Map persistence — reuse unchanged
**Source:** `upsert_machine_label` (line 372). Writes `hostname<TAB>$TARGET_LOCATION`,
atomic `.tmp` + `mv` (lines 387-416), preserves comments/blank lines verbatim (lines 390-398),
splits host with `${line%%$'\t'*}` (line 400). **Already records the folder via
`TARGET_LOCATION`** — call it after any selection or create; no edits needed.

### Map read loop idiom
**Source:** lines 453-460 / 493-499. Always:
```zsh
while IFS=$'\t' read -r map_host map_label || [[ -n "$map_host" ]]; do
    [[ "$map_host" =~ ^# ]] && continue
    [[ -z "$map_host" ]] && continue
    ...
done < "$map_file"
```
The `|| [[ -n "$map_host" ]]` handles a final line lacking a trailing newline. Guard the
whole block with `[[ -f "$map_file" ]]`.

### Numbered-menu + re-prompt idiom
**Source:** `resolve_machine_label` lines 521-547. `local create_new_idx=$(( ${#arr[@]} + 1 ))`,
1-indexed `while (( i <= ${#arr[@]} ))` print loop, `while true` read loop with
`[[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= N ))` bounds test, `echo "ERROR:"`
+ continue on invalid. Phase 11 adds a `quit_idx` = `create_new_idx + 1`.

### null-glob + entry guards in glob loops
**Source:** lines 508-512: `setopt local_options null_glob`, then `[[ -e "$file" ]] || continue`
and `[[ -d "$file" ]] && continue`. Mandatory per CLAUDE.md ("null-glob guard in filename
glob loops"). For the top-level dir scan use the zsh glob qualifier `*(/N)` (dirs-only,
null-glob).

### TTY guard / fail-fast
**Source:** lines 274-277 (`get_target_location`) and 470-473 (`resolve_machine_label`).
`if [[ ! -t 0 ]]; then echo "ERROR: ... Pass --computer \"Name\"."; exit 1; fi`. Use for
the non-interactive-no-flag path (CONTEXT Area 2). Note: EOF *during* an interactive menu
is treated as Quit (exit 0), which is different from "no TTY at all" (exit 1) — keep both.

### General style (CLAUDE.md + file conventions)
- `#!/bin/zsh`, macOS-only. `snake_case` function/variable names.
- `local` for ALL function-scoped vars (analog uses it throughout); no globals inside fns
  except the documented state vars (`TARGET_LOCATION`, etc.).
- `[[ ]]` for every conditional, never `[ ]`.
- Double-quote every variable expansion that could contain spaces; braces for concatenation
  (`"${SCRIPT_DIR}/${TARGET_LOCATION}"`). Bare `$var` only inside `(( ))`.
- `printf "..."` for prompts, `read -r` for input (analog lines 537-538).
- Zsh arrays are **1-indexed** (analog comment line 564) — `arr[1]` is the first element.
- zsh parameter modifiers used in-file: `${0:A:h}` (line 42), `${file:t}` (line 513);
  Phase 11 may use `${var:l}` (lowercase) for case-insensitive `q`/`quit`.

### Source-guard testability
**Source:** line 2354: `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`. All new functions
MUST be defined ABOVE this line so tests can `source update-list.sh` and call
`select_computer` / `parse_arguments` in isolation against a `mktemp -d` fixture (per the
spec's CRITICAL testing constraint — the script is destructive to run live).

## No Analog Found

None. Every Phase 11 unit maps to an existing same-file pattern.

| Unit | Note |
|------|------|
| (none) | All new logic adapts `resolve_machine_label` / `get_target_location` / `parse_arguments` / `upsert_machine_label` / main-block patterns. |

## Metadata

**Analog search scope:** single file `update-list.sh` (functions `display_usage` L67,
`validate_computer_name` L118, `validate_computer_name_quiet` L157, `parse_arguments` L190,
`get_target_location` L264, `resolve_archive_retention` L308, `upsert_machine_label` L372,
`resolve_machine_label` L439, `rename_machine` L591, `git_commit_and_push` L2297, main block
L2354-2431, globals L42-59).
**Files scanned:** 1
**Pattern extraction date:** 2026-06-14
