# Phase 12: Computer Rename - Pattern Map

**Mapped:** 2026-06-14
**Files analyzed:** 1 file, 7 code units (all modifications to `update-list.sh`)
**Analogs found:** 7 / 7 (6 in-file analogs + 1 NEW idiom from a related in-file `mv`)

> Single-file Zsh project. Every "file to create/modify" is a code unit inside
> `/Users/ken/dev/mac-software-list/update-list.sh`. The closest analog for each
> unit is ANOTHER function in the SAME file. There is no separate analog file —
> the planner copies from line ranges within `update-list.sh`.

---

## Code-Unit Classification

| Code Unit (in `rename_machine`, reworked) | Role | Data Flow | Closest In-File Analog | Match Quality |
|--------------------------------------------|------|-----------|------------------------|---------------|
| 1. Rename picker (folder list + Quit) | interactive-menu | request-response (read loop) | `select_computer` discovery + Quit (lines 342-463) | exact (reuse discovery; mirror Quit) |
| 2. New-name prompt (validate + re-prompt) | interactive-prompt | request-response | `rename_machine` NEW-label loop (lines 708-720) | exact (keep nearly as-is) |
| 3. Folder move (`mv old new`) | file-I/O | transform (move) | NEW — closest mv idiom: `rename_machine` per-file `mv` + collision skip (lines 762-769) | role-match (mv idiom only) |
| 4. In-folder filename rewrite | file-I/O | transform (batch rename) | `rename_machine` file-rename loop (lines 737-773) | exact (reuse, re-scope dirs) |
| 5. Map update (value==old → new, atomic) | file-I/O / config | transform | `rename_machine` map rewrite (lines 788-817) | exact (reuse, run in BOTH modes) |
| 6. Single commit + `--no-commit` path | git / side-effect | event-driven | `rename_machine` git block (lines 819-872) | exact (rework staged paths) |
| 7. `--rename` + selecting-flag guard | arg-validation | request-response | `parse_arguments` rename guard (lines 274-277) | exact (already correct — verify) |

**Source-guard note:** All function definitions MUST stay ABOVE the source-guard
at **line 2385**: `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`. This lets
tests `source update-list.sh` to load functions without running `main`. Do not
move any function below this line.

---

## Pattern Assignments

### Unit 1 — Rename picker: folder discovery + Quit (interactive-menu, request-response)

**Analog:** `select_computer`, `/Users/ken/dev/mac-software-list/update-list.sh` lines 342-463
**Replaces:** `rename_machine`'s label enumeration (lines 631-679) AND its OLD-label numbered picker (lines 686-706).

**Folder discovery to COPY** (lines 345-377) — union of catalog-bearing dirs + map values, deduped via `_name_in_list` helper:
```zsh
setopt local_options null_glob
typeset -a computers=()
local d

_name_in_list() {
    local candidate="$1"
    local existing
    for existing in "${computers[@]}"; do
        [[ "$existing" == "$candidate" ]] && return 0
    done
    return 1
}

# Source a: top-level dirs containing >=1 catalog ((/N) = dirs-only, null-glob)
for d in "${SCRIPT_DIR}"/*(/N); do
    local base="${d:t}"
    local f
    for f in "${d}"/mac-software-list-*.txt; do
        [[ -e "$f" ]] || continue
        _name_in_list "$base" || computers+=("$base")
        break
    done
done

# Source b: folders named as map values (even if empty / not yet on disk)
if [[ -f "$map_file" ]]; then
    while IFS=$'\t' read -r map_host map_label || [[ -n "$map_host" ]]; do
        [[ "$map_host" =~ ^# ]] && continue
        [[ -z "$map_host" || -z "$map_label" ]] && continue
        _name_in_list "$map_label" || computers+=("$map_label")
    done < "$map_file"
fi
```

**Ordering** — alphabetical only for the rename picker (CONTEXT Area 1: no
"this machine — default" marker). Use the sort from line 380, DROP the
remembered-default promotion (lines 381-392):
```zsh
computers=("${(@o)computers}")   # zsh (@o) = ascending sort, 1-indexed
```

**Empty-list guard** (CONTEXT Area 1) — replaces the `${#labels[@]} -eq 0`
guard at lines 681-684, new wording:
```zsh
if [[ ${#computers[@]} -eq 0 ]]; then
    echo "No computers found. Nothing to rename."
    exit 0
fi
```

**Menu + Quit input loop to MIRROR** — adapt `select_computer` lines 394-463,
DROPPING Create-new (rename has no create) and the Enter-default branch (rename
has no remembered default). Keep: numbered list, `quit_idx`, `q`/`quit`
case-insensitive via `${choice:l}`, EOF→Quit, invalid→re-prompt:
```zsh
local quit_idx=$(( ${#computers[@]} + 1 ))
echo ""
echo "Select the computer to rename:"
echo ""
local i=1
while (( i <= ${#computers[@]} )); do
    echo "  ${i}) ${computers[$i]}"
    ((i++))
done
echo "  ${quit_idx}) Quit"
echo ""

local choice
while true; do
    printf "Enter your choice [1-${quit_idx}]: "
    if ! read -r choice; then        # EOF (Ctrl-D) -> clean quit
        choice="$quit_idx"
    fi
    local lc="${choice:l}"           # zsh :l lowercase modifier
    if [[ "$lc" == "q" || "$lc" == "quit" ]]; then
        choice="$quit_idx"
    fi
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= quit_idx )); then
        break
    fi
    echo "ERROR: Invalid choice '${choice}'. Please enter 1-${quit_idx}."
done

if (( choice == quit_idx )); then
    echo "Nothing renamed."
    exit 0                           # clean quit — nothing moved, no commit
fi
local old_name="${computers[$choice]}"   # zsh arrays 1-indexed
```

> Note: the OLD picker at lines 698-705 used a bare `read -r choice` with NO
> EOF guard and NO Quit. The `select_computer` loop (lines 417-458) is the
> correct, current pattern — copy THAT shape, not the old one.

---

### Unit 2 — New-name prompt: validate + re-prompt (interactive-prompt, request-response)

**Analog:** `rename_machine` lines 708-720 — REUSE NEARLY VERBATIM (rename
`new_label`→`new_name`, `old_label`→`old_name`):
```zsh
echo ""
local new_name
local reason
while true; do
    printf "Enter new name for '${old_name}': "
    read -r new_name
    reason=$(validate_computer_name_quiet "$new_name")
    if [[ $? -eq 0 ]]; then
        break
    fi
    echo "$reason"
done
```

**Shared validator:** `validate_computer_name_quiet` (lines 156-175) — non-fatal
(`return 1` + reason on stdout), the re-prompt variant. Do NOT use
`validate_computer_name` (lines 117-141, `exit 1`) on the interactive path.

**new==old no-op guard** — KEEP from lines 722-726 (CONTEXT Area 4: warn +
exit 0, no commit), reworded for folders:
```zsh
if [[ "$new_name" == "$old_name" ]]; then
    echo "WARNING: New name is the same as the old name ('${old_name}'). Nothing to rename."
    exit 0
fi
```

---

### Unit 3 — Folder move `mv old new` (file-I/O, transform) — NEW, no direct analog

No existing function moves a whole directory. Closest mv idiom is the per-file
`mv` + collision-skip in `rename_machine` lines 762-769. Build the NEW move per
CONTEXT Area 2: refuse-clobber, single plain `mv` (archive/ rides along), move
FIRST then rewrite.

**Destination-exists refuse-clobber guard** (CONTEXT Area 2 — replaces the
old soft "collision warning" at lines 728-735, which only warned and proceeded):
```zsh
local old_dir="${SCRIPT_DIR}/${old_name}"
local new_dir="${SCRIPT_DIR}/${new_name}"

# Folder-not-found guard (CONTEXT Area 4: warn + exit 0, no commit)
if [[ ! -d "$old_dir" ]]; then
    echo "WARNING: Computer folder '${old_name}' not found. Nothing to rename."
    exit 0
fi
# Refuse to merge two computers — never clobber an existing folder.
if [[ -e "$new_dir" ]]; then
    echo "ERROR: A computer named '${new_name}' already exists. Refusing to merge. Nothing renamed."
    exit 1
fi

# Single plain mv — archive/ subfolder moves with it. (Not git mv; staged via git add -A later.)
mv "$old_dir" "$new_dir"
echo "  Renamed folder: ${old_name}/ -> ${new_name}/"
```

**Ordering (CONTEXT Area 2):** move folder FIRST, then run Unit 4 against
`new_dir` and `new_dir/archive`.

---

### Unit 4 — In-folder filename rewrite (file-I/O, batch transform)

**Analog:** `rename_machine` file-rename loop lines 737-773 — REUSE the body;
re-scope `dirs` to the NEW folder + its archive (NOT the 4 hardcoded dirs).
Keep the pure-zsh timestamp parse (`${base##*-}` + `=~ ^[0-9]{14}$`),
label-match-skip, and collision-skip exactly:
```zsh
local renamed_count=0
local skipped_count=0
# Scope: the moved folder's main dir + its archive (CONTEXT Area 2/3)
local rewrite_dirs=("$new_dir" "${new_dir}/archive")
local dir2
for dir2 in "${rewrite_dirs[@]}"; do
    [[ ! -d "$dir2" ]] && continue
    setopt local_options null_glob
    local file2
    for file2 in "${dir2}"/mac-software-list-*.txt; do
        [[ -e "$file2" ]] || continue
        [[ -d "$file2" ]] && continue
        local filename2="${file2:t}"
        local tmp2="${filename2#*\[}"
        local file_label2="${tmp2%\]-*}"
        # Only rewrite files whose [label] equals old_name (mixed-label files untouched)
        [[ "$file_label2" != "$old_name" ]] && continue
        # 14-digit timestamp via pure-zsh parameter expansion (zero forks)
        local base="${filename2%.txt}"
        local ts="${base##*-}"
        if [[ -z "$ts" || ! "$ts" =~ ^[0-9]{14}$ ]]; then
            echo "  WARNING: Could not parse timestamp from: ${filename2} — skipping"
            continue
        fi
        local new_filename="mac-software-list-[${new_name}]-${ts}.txt"
        local dest="${dir2}/${new_filename}"
        if [[ -e "$dest" ]]; then      # collision: warn + skip, never overwrite
            echo "  WARNING: Destination already exists, skipping: ${new_filename}"
            ((skipped_count++))
            continue
        fi
        mv "$file2" "$dest"
        echo "  Renamed: ${filename2} -> ${new_filename}"
        ((renamed_count++))
    done
done
```

> CRITICAL divergence from analog: the analog's `renamed_count == 0` gate at
> lines 779-786 aborted the whole rename (map + commit) when no files moved.
> In Phase 12 the **folder move already happened** and the map MUST update in
> BOTH modes (Unit 5), so do NOT reuse that abort gate. A folder rename with
> zero file rewrites (opt-out, or all-collision) is still a real, commit-worthy
> change. Use `renamed_count`/`skipped_count` only for the closing summary.

**Opt-out (CONTEXT Area 3):** gate this whole loop behind a `[Y/n]` prompt
(default Y). The prompt is a NEW small read; model it on the `read -r input` +
empty-default idiom in `resolve_archive_retention` (lines 522-538):
```zsh
printf "Rewrite all existing catalogs in '${new_name}' to '[${new_name}]'? [Y/n]: "
local rewrite_ans
read -r rewrite_ans
local lc_ans="${rewrite_ans:l}"
if [[ -z "$lc_ans" || "$lc_ans" == "y" || "$lc_ans" == "yes" ]]; then
    # ... run the rewrite loop above ...
fi
# else: opt-out — folder moved, filenames keep old [label]; map still updates + commit.
```
(Note the prompt says `new_name` because the folder is already moved.)

---

### Unit 5 — Map update: value==old → new, atomic .tmp+mv (file-I/O / config)

**Analog:** `rename_machine` map rewrite lines 788-817 — REUSE VERBATIM
(rename `old_label`→`old_name`, `new_label`→`new_name`). Keep the
TAB-required guard (`*$'\t'*`) so bare-hostname lines are never rewritten, and
the atomic `.tmp` + `mv`:
```zsh
local map_file="${SCRIPT_DIR}/machine-labels.tsv"
local tmp_file="${map_file}.tmp"
if [[ -f "$map_file" ]]; then
    > "$tmp_file"
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            printf '\n' >> "$tmp_file"; continue
        fi
        if [[ "$line" =~ ^# ]]; then
            printf '%s\n' "$line" >> "$tmp_file"; continue
        fi
        # Only a TAB-bearing data line can match; ${line#*\t} on a bare hostname
        # would wrongly match a host equal to old_name. Guard on the TAB.
        if [[ "$line" == *$'\t'* && "${line#*$'\t'}" == "$old_name" ]]; then
            printf '%s\t%s\n' "${line%%$'\t'*}" "$new_name" >> "$tmp_file"
        else
            printf '%s\n' "$line" >> "$tmp_file"
        fi
    done < "$map_file"
    mv "$tmp_file" "$map_file"
    echo "  Updated machine-labels.tsv: '${old_name}' -> '${new_name}'"
fi
```

**CRITICAL (CONTEXT Area 4):** this block runs in BOTH rewrite (Y) and opt-out
(n) modes — the folder name is the identity, so EVERY `hostname → old_name`
entry must point at `new_name`. Place it AFTER the opt-out branch (unconditional),
not inside the Y branch.

---

### Unit 6 — Single commit staging old+new folder paths; `--no-commit` path (git, event-driven)

**Analog:** `rename_machine` git block lines 819-872. REUSE the structure
(`cd` guard, `git rev-parse` guard, `git diff --cached --quiet` no-op guard,
push + push-failure recovery message, `--no-commit` manual instructions).
REWORK the staged paths: stage the OLD and NEW folder paths (old = deletions,
new = adds) + the map, instead of the fixed `personal`/`office` loop (lines 834-838).

Keep the per-path-exists idea so a missing path doesn't abort `git add` (the
old folder may be gone after `mv`; `git add -A` on a now-absent path stages its
deletions — pass the path string, guard the new one):
```zsh
if [[ "$AUTO_COMMIT" == "true" ]]; then
    cd "$SCRIPT_DIR" || {
        echo "  WARNING: Could not change to script directory. Skipping git operations."
        return
    }
    if ! git rev-parse --git-dir &>/dev/null; then
        echo "  WARNING: Not a git repository. Skipping git operations."
        return
    fi
    # Stage the old path (records the folder's deletion/move) and the new path
    # (records the renamed folder + rewritten filenames). git add -A on the old
    # path name is safe even though the dir no longer exists — it stages removals.
    git add -A "${old_name}/" 2>/dev/null || true
    git add -A "${new_name}/" 2>/dev/null || true
    git add machine-labels.tsv 2>/dev/null || true
    if git diff --cached --quiet; then
        echo "  No changes staged."
        return
    fi
    local commit_message="Rename computer: '${old_name}' -> '${new_name}'"
    if git commit -m "$commit_message" &>/dev/null; then
        echo "  Committed: $commit_message"
    else
        echo "  WARNING: Failed to create commit."
        return
    fi
    echo "  Pushing to remote..."
    if git push 2>&1; then
        echo "  Successfully pushed to remote."
    else
        # KEEP the push-failure recovery message shape from lines 853-863,
        # reworded: the folder has ALREADY moved on disk; do NOT re-run --rename.
        echo ""
        echo "  WARNING: Failed to push to remote repository."
        echo "  The commit is saved locally; the folder has ALREADY been renamed"
        echo "  ('${old_name}/' -> '${new_name}/'). Do NOT re-run --rename. Resolve with:"
        echo "    cd $SCRIPT_DIR && git pull --rebase && git push"
        echo ""
    fi
else
    echo ""
    echo "Git auto-commit is disabled (--no-commit flag was used)."
    echo "To commit manually, run:"
    echo "  cd $SCRIPT_DIR && git add -A '${old_name}/' && git add -A '${new_name}/' && git add machine-labels.tsv"
    echo "  git commit -m 'Rename computer: ${old_name} -> ${new_name}'"
    echo "  git push"
fi
```

> Cross-reference the per-run `--no-commit` manual path in the main block
> (lines 2453-2456) for the current `git add -A "${TARGET_LOCATION}/"` +
> `git add machine-labels.tsv 2>/dev/null` quoting idiom.

---

### Unit 7 — `--rename` + selecting-flag conflict guard (arg-validation)

**Analog:** `parse_arguments` lines 274-277 — ALREADY CORRECT and complete. It
rejects `--rename` combined with ANY selecting flag because `--personal`,
`--office`, `--computer`, and `--machine` ALL set `TARGET_LOCATION`, and the
guard tests `-n "$TARGET_LOCATION"`:
```zsh
if [[ "$RENAME_MODE" == "true" && -n "$TARGET_LOCATION" ]]; then
    echo "ERROR: --rename cannot be combined with a computer-selecting flag (--personal/--office/--computer/--machine). --rename prompts for old/new labels interactively."
    exit 1
fi
```
**Action for planner:** verify only — no change needed unless the error wording
should say "old/new computer" instead of "old/new labels". The
`selecting_flags_seen` mutual-exclusion guard (lines 263-268) already backs it.

**TTY guard** for the whole flow — KEEP from `rename_machine` lines 623-627
(identical idiom to `select_computer` lines 336-340 and
`resolve_archive_retention` lines 516-520):
```zsh
if [[ ! -t 0 ]]; then
    echo "ERROR: --rename requires an interactive terminal (stdin is not a TTY). Cannot prompt for computer names."
    exit 1
fi
```

---

## Shared Patterns (Zsh conventions to replicate across all units)

### Style conventions (CLAUDE.md + observed in-file)
**Source:** throughout `update-list.sh`
**Apply to:** every unit
- `#!/bin/zsh`, macOS-only.
- `snake_case` function and variable names; `local` for ALL function-scoped vars (never globals inside functions — see every `local` in `select_computer`/`rename_machine`).
- `[[ ]]` for all conditionals (never `[ ]`). `(( ))` for arithmetic.
- Double-quote every variable that could contain spaces/paths: `"${SCRIPT_DIR}/${new_name}"`.
- Zsh arrays are **1-indexed**: `computers[$choice]`, `labels[$i]` (lines 483, 706).
- `printf "...: "` for prompts (no trailing newline), then `read -r` (lines 419-423, 699-700, 713-714).
- Null-glob guard in every glob loop: `setopt local_options null_glob` + `[[ -e "$f" ]] || continue` (lines 345/364, 661-662, 744-747).
- `command -v tool &>/dev/null` for tool detection (not `which`).

### Atomic file write (.tmp + mv)
**Source:** `upsert_machine_label` lines 570-599; `rename_machine` map rewrite lines 789-815
**Apply to:** Unit 5 (map update)
Write to `${map_file}.tmp`, then `mv "$tmp_file" "$map_file"` — never edit in place. Preserve comment (`^#`) and blank lines verbatim.

### TTY guard for interactive flows
**Source:** `select_computer` 336-340, `rename_machine` 623-627, `resolve_archive_retention` 516-520
**Apply to:** Unit 7 (rename entry), and any new prompt — `[[ ! -t 0 ]]` → ERROR + `exit 1`.

### Quit / EOF handling on menus
**Source:** `select_computer` lines 423-463
**Apply to:** Unit 1 — `read -r` failure (EOF) → Quit index; `${choice:l}` lowercase for `q`/`quit`; Quit → `exit 0` with nothing changed.

### Pure-zsh 14-digit timestamp parse
**Source:** `rename_machine` lines 754-760 (`${base##*-}` + `=~ ^[0-9]{14}$`)
**Apply to:** Unit 4. Prefer this fork-free form over the `grep -oE | cut` form used in `retain_newest_per_host`/`prune_old_archives` (lines 919, 998) for the rename rewrite.

### Source-guard testability (CRITICAL)
**Source:** line 2385 `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0`
**Apply to:** ALL units — keep every function definition ABOVE line 2385 so tests can `source update-list.sh` and call `rename_machine` against a `mktemp -d` fixture without triggering `main`. Per the spec's "Testing constraints (CRITICAL)" and MEMORY: never live-run the script to verify; use `zsh -n`, source/grep, and throwaway fixtures.

---

## Integration Points

| Point | Location | Action |
|-------|----------|--------|
| Main-block short-circuit | lines 2399-2403 | KEEP AS-IS — `if RENAME_MODE: git_pull; rename_machine; exit 0`. Rename runs before catalog generation. |
| `parse_arguments` `--rename` flag set | line 251-254 | KEEP — sets `RENAME_MODE=true`. |
| `parse_arguments` conflict guard | lines 274-277 | KEEP (Unit 7) — already rejects `--rename` + any selecting flag. |
| `mutual-exclusion` guard | lines 263-268 | KEEP — backs the selecting-flag rejection. |
| `validate_computer_name_quiet` | lines 156-175 | REUSE (Unit 2) — non-fatal re-prompt validator. |
| `select_computer` discovery block | lines 342-392 | SOURCE to copy for Unit 1 (drop default-promotion). |
| `rename_machine` whole function | lines 622-877 | REWORK in place — replace units 1,3,6; reuse units 2,4,5; remove the `renamed_count==0` abort gate (779-786). |
| Source-guard | line 2385 | Definitions stay above. |

## No Analog Found

| Code Unit | Role | Reason |
|-----------|------|--------|
| Unit 3 folder `mv` (whole-dir move + refuse-clobber) | file-I/O | No existing function moves a top-level directory; only per-file `mv` exists (lines 769, 945). Build new per CONTEXT Area 2, borrowing the `[[ -e "$dest" ]]` collision idiom (lines 764-768). |

## Metadata

**Analog search scope:** single file `/Users/ken/dev/mac-software-list/update-list.sh` (2464 lines).
**Functions scanned in full:** `select_computer` (308-488), `rename_machine` (622-877), `parse_arguments` (189-278), `upsert_machine_label` (555-601), `resolve_archive_retention` (509-539), main block + source-guard (2385-2464).
**Pattern extraction date:** 2026-06-14
