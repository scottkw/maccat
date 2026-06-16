# Coding Conventions

**Analysis Date:** 2026-06-12

## Shell Environment

**Interpreter:** `zsh` — declared via `#!/bin/zsh` shebang (not `bash`)

**Safety flags:** `set -e` is **not used**. The script relies on conditional checks and explicit
`exit 1` calls for error handling rather than automatic exit-on-error. This is a deliberate
tradeoff that allows warnings to be printed without aborting execution (e.g., missing optional
tools like `mas`).

## Naming Patterns

**Functions:**
- `snake_case` with descriptive verb-noun pairs: `display_usage`, `parse_arguments`,
  `get_target_location`, `archive_old_catalogs`, `generate_catalog`, `git_pull`,
  `git_commit_and_push`, `write_section`

**Global variables (SCREAMING_SNAKE_CASE):**
- `SCRIPT_DIR`, `ARCHIVE_AGE_DAYS`, `AUTO_COMMIT`, `TARGET_LOCATION`, `CURRENT_DATE`,
  `CURRENT_MACHINE`, `OUTPUT_FILENAME`, `OUTPUT_FILE`

**Local variables (snake_case):**
- Declared with `local` keyword inside functions: `target_dir`, `full_path`,
  `archive_path`, `cutoff_date`, `archived_count`, `filename`, `timestamp`,
  `commit_message`

**Output files:**
- Pattern: `mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt`
- Hostname is wrapped in square brackets in the filename

## Variable Quoting

- Variables are consistently double-quoted when there is any chance of spaces or
  empty values: `"$1"`, `"$TARGET_LOCATION"`, `"$archive_path"`, `"$file"`.
- Paths constructed from variables are always quoted: `"${full_path}/archive"`,
  `"${SCRIPT_DIR}/${target_dir}"`.
- Parameter expansion uses braces for concatenation contexts:
  `"${TARGET_LOCATION}/${OUTPUT_FILENAME}"`, `"${SCRIPT_DIR}/${TARGET_LOCATION}"`.
- Bare `$var` (no quotes) is used only for arithmetic comparisons:
  `[[ $archived_count -eq 0 ]]`, `[[ $# -gt 0 ]]`.

## Control Flow Patterns

**Argument parsing:**
```zsh
while [[ $# -gt 0 ]]; do
    case "$1" in
        --personal) TARGET_LOCATION="personal"; shift ;;
        --no-commit) AUTO_COMMIT=false; shift ;;
        *) echo "ERROR: Invalid option '$1'"; exit 1 ;;
    esac
done
```

**Capability detection (prefer `command -v` over `which`):**
```zsh
if command -v brew &>/dev/null; then
    brew list --formula >> "$OUTPUT_FILE"
else
    echo "Homebrew is not installed." >> "$OUTPUT_FILE"
fi
```

**Directory existence guard:**
```zsh
if [[ ! -d "$archive_path" ]]; then
    mkdir -p "$archive_path"
fi
```

**File glob with null-glob guard:**
```zsh
for file in "${full_path}"/mac-software-list-*.txt; do
    [[ -e "$file" ]] || continue
    ...
done
```

## Error Handling

**Strategy:** Graceful degradation — missing optional tools produce a WARNING message
to stdout and a note in the output file, but do not abort the script.

**Fatal errors** use `exit 1` with an `ERROR:` prefix:
- Invalid CLI argument in `parse_arguments`
- Invalid interactive choice in `get_target_location`

**Non-fatal warnings** use `echo "  WARNING: ..."` and `return` (not `exit`):
- git pull/push/commit failures
- `cd` failure in git functions
- Unparseable filename timestamp in `archive_old_catalogs`

**Git operations** are wrapped in `if cmd; then ... else ... fi` to allow the script
to complete even when the network is unavailable.

**Exit code capture after piped commands:**
```zsh
mas list 2>/dev/null | awk '{print $2, $3}' >> "$OUTPUT_FILE"
if [[ $? -ne 0 ]]; then
    echo "Could not retrieve App Store list." >> "$OUTPUT_FILE"
fi
```
Note: this `$?` check captures the exit code of `awk`, not `mas`, due to piping. This
is a known subtle bug (see CONCERNS.md).

## Output Conventions

**Section headers** are written via the `write_section` helper:
```zsh
write_section() {
    echo "\n$1" >> "$OUTPUT_FILE"
    echo "------------------------------------" >> "$OUTPUT_FILE"
}
```

**Progress messages** go to stdout with 2-space indentation:
- `echo "  Collecting Homebrew formulae..."`
- `echo "  WARNING: ..."`
- `echo "  NOTE: ..."`

**Decorative banners** use `=` (80 chars) for top-level and `-` (78 chars) for subsections:
```zsh
echo "=============================================================================="
echo "------------------------------------------------------------------------------"
```

## Output Redirection

- Catalog data → `>> "$OUTPUT_FILE"` (append to the output file)
- Progress/status → stdout (implicit, no redirection)
- Suppressed stderr → `2>/dev/null` for noisy commands (`git rev-parse`, `mas list`,
  `git add` on optional paths)
- Combined stdout+stderr → `2>&1` only for commands where output is shown to the user
  (`git pull`, `git push`)

## Function Documentation Style

Every function has a structured comment block immediately above its definition:

```
# ------------------------------------------------------------------------------
# FUNCTION: function_name
# ------------------------------------------------------------------------------
# One-sentence description.
#
# Arguments:
#   $1 - Description
#
# Sets/Returns:
#   GLOBAL_VAR - What it sets
# ------------------------------------------------------------------------------
```

Top-level script sections use `=` dividers; subsections within functions use `-` dividers.

## String Extraction

Timestamps are extracted from filenames using a pipeline (no `sed` or `awk` extension syntax):
```zsh
local timestamp=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-8)
```

## Arithmetic

Counter increments use the `(( ))` arithmetic compound command:
```zsh
((archived_count++))
```

## Path Handling

The script resolves its own location at startup using zsh's `:A:h` parameter flags
(resolves symlinks then takes the directory component):
```zsh
SCRIPT_DIR="${0:A:h}"
```
All subsequent paths are built from `$SCRIPT_DIR` to make the script location-independent.

## Style Patterns to Follow

- Use `local` for all function-scoped variables — do not use globals inside functions
  unless the variable is intended to persist after the function returns.
- Use `[[ ]]` (double brackets) for all conditionals, not `[ ]`.
- Prefer `command -v` over `which` for tool detection.
- Always check that a directory exists before writing into it.
- Include a null-glob guard (`[[ -e "$file" ]] || continue`) in filename glob loops.
- Use `return` to exit a function on non-fatal errors; use `exit 1` only for fatal
  user-input errors.

---

*Convention analysis: 2026-06-12*
