#!/bin/zsh

# ==============================================================================
# Mac Software List Generator
# ==============================================================================
#
# DESCRIPTION:
#   This script generates a comprehensive catalog of all software installed on
#   a macOS machine. It collects information from multiple sources including
#   Homebrew packages, Mac App Store applications, Setapp applications, and
#   other web-installed applications.
#
# FEATURES:
#   - Generates timestamped software catalogs
#   - Supports separate storage for personal and office machines
#   - Retains newest catalog per machine; archive is pruned after 30 days
#   - Accepts command-line arguments or interactive prompts for location
#   - Automatically commits and pushes changes to git (can be disabled)
#
# USAGE:
#   ./update-list.sh [--personal | --office] [--no-commit]
#
# OPTIONS:
#   --personal    Save the catalog to the personal/ directory
#   --office      Save the catalog to the office/ directory
#   --no-commit   Skip automatic git commit and push
#   (no option)   Interactive prompt to choose location
#
# OUTPUT:
#   Creates a file named: mac-software-list-[computer-folder]-YYYYMMDDHHMMSS.txt
#
# AUTHOR:
#   Ken's Mac Software List Repository
#
# ==============================================================================

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

# Get the directory where this script is located (handles symlinks too)
SCRIPT_DIR="${0:A:h}"

# Number of days after which catalog files should be archived
ARCHIVE_AGE_DAYS=30

# Sentinel: true when --archive-days was passed; suppresses the interactive prompt
ARCHIVE_DAYS_SET=false

# Flag to control automatic git commit and push (default: enabled)
AUTO_COMMIT=true

# Sentinel: true when --rename is passed; causes the main block to skip the
# normal catalog flow (location prompt, retention, generation, prune) and
# run rename_machine instead, then exit.
RENAME_MODE=false

# ------------------------------------------------------------------------------
# FUNCTION: display_usage
# ------------------------------------------------------------------------------
# Displays a title banner and usage information every time the script runs.
# This helps users understand what the script does and how to use it.
# ------------------------------------------------------------------------------
display_usage() {
    echo ""
    echo "=============================================================================="
    echo "                     Mac Software List Generator"
    echo "=============================================================================="
    echo ""
    echo "This script catalogs all software installed on your Mac, including:"
    echo "  - Homebrew packages (formulae and casks)"
    echo "  - Mac App Store applications"
    echo "  - Setapp applications"
    echo "  - Other web-installed applications"
    echo "  - AI CLI tooling (Claude Code, Codex, OpenCode, Gemini):"
    echo "      plugins, MCP servers (name + transport only), and skills/agents"
    echo "  - Editor extensions (VS Code, Cursor)"
    echo "  - Browser extensions (Google Chrome, Firefox) across all profiles"
    echo ""
    echo "USAGE:"
    echo "  ./update-list.sh [--computer \"Name\" | --personal | --office] [--no-commit] [--rename]"
    echo ""
    echo "OPTIONS:"
    echo "  --computer \"Name\"    Select or create the computer folder for this run,"
    echo "                       non-interactively (skips the menu)"
    echo "  --personal           Alias for --computer personal"
    echo "  --office             Alias for --computer office"
    echo "  --machine \"Name\"     Silent back-compat alias for --computer \"Name\""
    echo "  --no-commit          Skip automatic git commit and push"
    echo "  --archive-days N     Set archive retention period in days (default: 30)"
    echo "  --rename             Rename a machine label across all catalog files"
    echo "  (no option)          You will be shown an interactive menu of computers"
    echo ""
    echo "Each run keeps the newest catalog per machine; older catalogs are moved to"
    echo "archive/ and hard-deleted after ${ARCHIVE_AGE_DAYS} days."
    echo ""
    echo "By default, changes are automatically committed and pushed to git."
    echo ""
    echo "=============================================================================="
    echo ""
}

# ------------------------------------------------------------------------------
# FUNCTION: validate_computer_name
# ------------------------------------------------------------------------------
# Validates a candidate computer/folder name string.
# Exits with error code 1 and an actionable message if the name is invalid.
#
# Arguments:
#   $1 - The candidate computer/folder name to validate
#
# Validation rules:
#   - Must be non-empty
#   - Must not contain /, [, or ]
#   - Must not have leading or trailing whitespace
# ------------------------------------------------------------------------------
validate_computer_name() {
    local val="$1"
    if [[ -z "$val" ]]; then
        echo "ERROR: computer name must not be empty"
        exit 1
    fi
    if [[ "$val" =~ ^[[:space:]] ]] || [[ "$val" =~ [[:space:]]$ ]]; then
        echo "ERROR: computer name must not have leading or trailing whitespace (got '${val}')"
        exit 1
    fi
    # Reject /, [, ] — these corrupt the catalog filename and the host-split
    # logic in retain_newest_per_host. The bracket expression places ] first so
    # it is treated as a literal, and is single-quoted so zsh does not glob it.
    if [[ "$val" =~ '[][/]' ]]; then
        echo "ERROR: computer name must not contain /, [, or ] (got '${val}')"
        exit 1
    fi
    # Reject interior TAB and newline — TAB is the TSV column delimiter and a
    # newline splits one logical entry across multiple physical lines,
    # corrupting machine-labels.tsv.
    if [[ "$val" == *$'\t'* || "$val" == *$'\n'* ]]; then
        echo "ERROR: computer name must not contain tab or newline characters"
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: validate_computer_name_quiet
# ------------------------------------------------------------------------------
# Non-fatal variant of validate_computer_name. Applies the same four validation
# rules but uses return 1 instead of exit 1, and emits the error reason to
# stdout so the caller can display it and re-prompt the user.
#
# Arguments:
#   $1 - The candidate computer/folder name to validate
#
# Returns:
#   0 if valid; 1 with a reason string echoed to stdout if invalid.
# ------------------------------------------------------------------------------
validate_computer_name_quiet() {
    local val="$1"
    if [[ -z "$val" ]]; then
        echo "ERROR: computer name must not be empty"
        return 1
    fi
    if [[ "$val" =~ ^[[:space:]] ]] || [[ "$val" =~ [[:space:]]$ ]]; then
        echo "ERROR: computer name must not have leading or trailing whitespace (got '${val}')"
        return 1
    fi
    if [[ "$val" =~ '[][/]' ]]; then
        echo "ERROR: computer name must not contain /, [, or ] (got '${val}')"
        return 1
    fi
    if [[ "$val" == *$'\t'* || "$val" == *$'\n'* ]]; then
        echo "ERROR: computer name must not contain tab or newline characters"
        return 1
    fi
    return 0
}

# ------------------------------------------------------------------------------
# FUNCTION: parse_arguments
# ------------------------------------------------------------------------------
# Parses all command-line arguments and sets global variables accordingly.
#
# Arguments:
#   $@ - All command-line arguments
#
# Sets:
#   TARGET_LOCATION - "personal", "office", or empty (prompt user)
#   AUTO_COMMIT - true or false based on --no-commit flag
# ------------------------------------------------------------------------------
parse_arguments() {
    # Count selecting-flags (--personal/--office/--computer/--machine). They all
    # write the SAME global (TARGET_LOCATION), so passing more than one is
    # ambiguous and is rejected after the loop (fail-fast, mirrors the
    # --rename guard).
    local selecting_flags_seen=0

    # Process all command-line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --personal)
                TARGET_LOCATION="personal"
                (( selecting_flags_seen++ ))
                shift
                ;;
            --office)
                TARGET_LOCATION="office"
                (( selecting_flags_seen++ ))
                shift
                ;;
            --computer)
                if [[ -z "$2" || "$2" == --* ]]; then
                    echo "ERROR: --computer requires a value"
                    exit 1
                fi
                local val="$2"
                validate_computer_name "$val"
                TARGET_LOCATION="$val"
                (( selecting_flags_seen++ ))
                shift 2
                ;;
            --no-commit)
                AUTO_COMMIT=false
                shift
                ;;
            --archive-days)
                if [[ -z "$2" ]]; then
                    echo "ERROR: --archive-days requires a value"
                    exit 1
                fi
                local val="$2"
                if ! { [[ "$val" =~ ^[0-9]+$ ]] && (( val >= 1 )); }; then
                    echo "ERROR: --archive-days must be a positive integer (got '${val}')"
                    exit 1
                fi
                ARCHIVE_AGE_DAYS="$val"
                ARCHIVE_DAYS_SET=true
                shift 2
                ;;
            --machine)
                # Silent back-compat alias for --computer (no deprecation
                # warning per Phase 11). Routes to TARGET_LOCATION.
                if [[ -z "$2" || "$2" == --* ]]; then
                    echo "ERROR: --machine requires a value"
                    exit 1
                fi
                local val="$2"
                validate_computer_name "$val"
                TARGET_LOCATION="$val"
                (( selecting_flags_seen++ ))
                shift 2
                ;;
            --rename)
                RENAME_MODE=true
                shift
                ;;
            *)
                echo "ERROR: Invalid option '$1'"
                echo "Valid options are: --personal, --office, --computer, --no-commit, --archive-days, --machine, --rename"
                exit 1
                ;;
        esac
    done

    # Reject more than one computer-selecting flag — they all write
    # TARGET_LOCATION, so two of them is ambiguous (which folder wins?).
    if (( selecting_flags_seen > 1 )); then
        echo "ERROR: --personal, --office, --computer, and --machine are mutually exclusive."
        exit 1
    fi

    # --rename runs an interactive old/new label flow and exits before the
    # catalog selection; combining it with a selecting-flag would silently
    # discard the supplied folder. Reject the combination per fail-fast policy.
    # (--machine/--computer/--personal/--office all set TARGET_LOCATION now.)
    if [[ "$RENAME_MODE" == "true" && -n "$TARGET_LOCATION" ]]; then
        echo "ERROR: --rename cannot be combined with a computer-selecting flag (--personal/--office/--computer/--machine). --rename prompts for old/new labels interactively."
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: select_computer
# ------------------------------------------------------------------------------
# Resolves the computer folder for this run and sets TARGET_LOCATION.
#
# Replaces the legacy two-step selection (get_target_location personal/office
# menu + resolve_machine_label label menu) with a single always-shown
# computer-folder menu. The folder name IS the machine identity.
#
# Arguments:
#   None — reads/sets the TARGET_LOCATION global; reads SCRIPT_DIR and hostname.
#
# Sets:
#   TARGET_LOCATION — the chosen computer folder name
#
# Behavior:
#   1. Flag path: if TARGET_LOCATION is already set (--computer/--personal/
#      --office/--machine resolved it in parse_arguments), mkdir -p the folder
#      (select-or-create), upsert the map, and return.
#   2. Map lookup: find this hostname's remembered folder (saved_folder). An
#      absent row leaves saved_folder empty (no Enter-default). The menu is
#      ALWAYS shown — a found entry only marks the default; it does not fast-exit.
#   3. TTY guard: non-interactive with no flag fails fast (exit 1).
#   4. Discovery: build the computer list as the union of top-level dirs that
#      contain mac-software-list-*.txt catalogs and machine-labels.tsv values,
#      deduplicated, sorted (remembered-first then alphabetical).
#   5. Numbered menu + input loop + Quit/Create-new/Select branches (Task 2).
# ------------------------------------------------------------------------------
select_computer() {
    # 1. Flag path: --computer/alias resolved TARGET_LOCATION in parse_arguments.
    #    --computer is select-or-create, so mkdir -p the folder (unlike the label
    #    analog, because computer names ARE folders), then remember the choice.
    if [[ -n "$TARGET_LOCATION" ]]; then
        mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"   # select-or-create semantics
        upsert_machine_label
        echo "Computer: ${TARGET_LOCATION} (from command-line argument)"
        return
    fi

    # 2. Map lookup: find this host's remembered folder. Do NOT fast-exit on a
    #    found entry — the menu is always shown; saved_folder is only the default.
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

    # 3. Non-interactive TTY guard — no flag and no TTY cannot prompt.
    if [[ ! -t 0 ]]; then
        echo "ERROR: No computer selected and stdin is not a TTY. Pass --computer \"Name\"."
        exit 1
    fi

    # 4. Folder discovery: union of (a) top-level dirs containing catalogs and
    #    (b) machine-labels.tsv values. Infra dirs (.git, .planning, etc.) are
    #    excluded naturally — they hold no catalogs and are not map values.
    setopt local_options null_glob
    typeset -a computers=()
    local d

    # Helper: returns 0 if $1 is already in computers[], 1 otherwise
    _name_in_list() {
        local candidate="$1"
        local existing
        for existing in "${computers[@]}"; do
            [[ "$existing" == "$candidate" ]] && return 0
        done
        return 1
    }

    # Source a: top-level dirs that contain at least one catalog ((/N) = dirs-only, null-glob)
    for d in "${SCRIPT_DIR}"/*(/N); do
        local base="${d:t}"
        local f=""    # MUST assign: a bare `local f` re-run each loop iteration makes
                      # zsh echo `f=<value>` to stdout (typeset-query behavior), leaking
                      # internal paths into the interactive menu. Assigning keeps it silent.
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

    # Order: alphabetical, then promote the remembered folder to index 1 if present.
    computers=("${(@o)computers}")
    if [[ -n "$saved_folder" ]]; then
        local k=1
        local promoted=()
        while (( k <= ${#computers[@]} )); do
            [[ "${computers[$k]}" == "$saved_folder" ]] || promoted+=("${computers[$k]}")
            ((k++))
        done
        # Only promote if saved_folder is actually present in the discovered set.
        if _name_in_list "$saved_folder"; then
            computers=("$saved_folder" "${promoted[@]}")
        fi
    fi

    # 5. Numbered menu — 1-indexed list, Create-new and Quit appended.
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

    # 6. Input loop — Enter-default only when saved_folder is set; q/quit/EOF -> Quit;
    #    invalid input re-prompts indefinitely.
    local choice
    while true; do
        if [[ -n "$saved_folder" ]]; then
            printf "Enter your choice [1-${quit_idx}, or Enter for the default]: "
        else
            printf "Enter your choice [1-${quit_idx}]: "
        fi
        if ! read -r choice; then        # EOF (Ctrl-D / closed stdin) -> clean quit
            choice="$quit_idx"
        fi
        # case-insensitive q / quit
        local lc="${choice:l}"           # zsh :l = lowercase modifier
        if [[ "$lc" == "q" || "$lc" == "quit" ]]; then
            choice="$quit_idx"
        fi
        if [[ -z "$choice" ]]; then
            if [[ -n "$saved_folder" ]]; then
                # Empty input -> the remembered default; resolve it to its menu index.
                local k2=1
                while (( k2 <= ${#computers[@]} )); do
                    [[ "${computers[$k2]}" == "$saved_folder" ]] && { choice="$k2"; break; }
                    ((k2++))
                done
                # Guard the post-loop state explicitly instead of relying on the
                # upstream promotion invariant. If saved_folder was not found in
                # computers[] the loop leaves choice empty; breaking here would
                # fall through to computers[0] (empty in 1-indexed zsh) and write
                # a corrupt mac-software-list-[]-<ts>.txt at the repo root. Fail
                # loudly instead (no silent fallback — "let it crash").
                if [[ -z "$choice" ]]; then
                    echo "ERROR: saved default '${saved_folder}' is not in the computer list."
                    exit 1
                fi
                break
            fi
            echo "No default for this machine — please enter a number."
            continue
        fi
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= quit_idx )); then
            break
        fi
        echo "ERROR: Invalid choice '${choice}'. Please enter 1-${quit_idx}."
    done

    # 7. Branch on choice: Quit / Create-new / Select existing.
    if (( choice == quit_idx )); then
        echo "No catalog written."
        exit 0                                   # clean quit
    elif (( choice == create_new_idx )); then
        # Create-new re-prompt loop via the non-fatal validator.
        local new_name reason
        while true; do
            printf "Enter a name for the new computer: "
            if ! read -r new_name; then          # EOF during create -> clean quit
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
        # Select existing computer (Zsh arrays are 1-indexed)
        TARGET_LOCATION="${computers[$choice]}"
    fi

    echo "Computer: ${TARGET_LOCATION}"
    upsert_machine_label                          # remember choice for next run
}

# ------------------------------------------------------------------------------
# FUNCTION: resolve_archive_retention
# ------------------------------------------------------------------------------
# Determines the archive retention period in days and sets ARCHIVE_AGE_DAYS.
#
# Arguments:
#   None
#
# Sets:
#   ARCHIVE_AGE_DAYS - the resolved retention period in days
#
# Behavior:
#   - If --archive-days was passed (ARCHIVE_DAYS_SET=true): uses the value already
#     set by parse_arguments and returns immediately (no prompt needed).
#   - If stdin is not a TTY (non-interactive, e.g. cron or piped input): silently
#     uses the default value of 30 to avoid hanging on read.
#   - Otherwise (interactive, no flag): prompts the user for a value. Empty input
#     keeps the default (30). Non-empty input is validated; invalid input exits 1.
# ------------------------------------------------------------------------------
resolve_archive_retention() {
    # Flag path: value already validated and set in parse_arguments
    if [[ "$ARCHIVE_DAYS_SET" == "true" ]]; then
        echo "Archive retention: ${ARCHIVE_AGE_DAYS} days"
        return
    fi

    # Non-interactive path: no TTY, skip read to avoid hanging
    if [[ ! -t 0 ]]; then
        echo "Archive retention: ${ARCHIVE_AGE_DAYS} days (non-interactive, using default)"
        return
    fi

    # Interactive path: prompt the user
    printf "Archive retention period in days [30]: "
    local input
    read -r input

    if [[ -z "$input" ]]; then
        # Empty input: keep default
        echo "Archive retention: 30 days"
    else
        # Validate: must be a positive integer >= 1
        if ! { [[ "$input" =~ ^[0-9]+$ ]] && (( input >= 1 )); }; then
            echo "ERROR: Archive retention must be a positive integer (got '${input}')"
            exit 1
        fi
        ARCHIVE_AGE_DAYS="$input"
        echo "Archive retention: ${ARCHIVE_AGE_DAYS} days"
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: upsert_machine_label
# ------------------------------------------------------------------------------
# Writes or updates the hostname→computer-folder mapping in machine-labels.tsv.
# Reads TARGET_LOCATION from the calling scope (global). Creates the map file
# with header comments if it does not exist. Preserves comment and blank lines
# verbatim. Uses a .tmp file + atomic mv to avoid partial-write corruption.
#
# Arguments:
#   None — reads TARGET_LOCATION global
#
# Side effects:
#   Writes to ${SCRIPT_DIR}/machine-labels.tsv
# ------------------------------------------------------------------------------
upsert_machine_label() {
    local map_file="${SCRIPT_DIR}/machine-labels.tsv"
    local current_host=$(hostname)
    local tmp_file="${map_file}.tmp"
    local found=false

    # Create map file with header if it does not exist
    if [[ ! -f "$map_file" ]]; then
        printf '# Mac Software List — hostname to computer-folder map\n' > "$map_file"
        printf '# Format: hostname\tcomputer-folder\n' >> "$map_file"
        printf '# One entry per line. Lines beginning with # and blank lines are ignored.\n' >> "$map_file"
    fi

    # Rewrite the map file, replacing or appending the current host's entry.
    # Read raw lines to preserve comment and blank lines verbatim.
    # Use ': >' not bare '>': a bare redirect runs zsh NULLCMD (cat), which reads
    # stdin and hangs on an interactive TTY (the new always-shown menu leaves stdin
    # on the terminal when this runs). ': >' truncates without reading stdin.
    : > "$tmp_file"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Blank lines: preserve verbatim
        if [[ -z "$line" ]]; then
            printf '\n' >> "$tmp_file"
            continue
        fi
        # Comment lines: preserve verbatim
        if [[ "$line" =~ ^# ]]; then
            printf '%s\n' "$line" >> "$tmp_file"
            continue
        fi
        # Data line: split on TAB to get map_host
        local map_host="${line%%$'\t'*}"
        if [[ "$map_host" == "$current_host" ]]; then
            # Replace this host's entry with the computer-folder name
            printf '%s\t%s\n' "$current_host" "$TARGET_LOCATION" >> "$tmp_file"
            found=true
        else
            # Preserve other hosts verbatim
            printf '%s\n' "$line" >> "$tmp_file"
        fi
    done < "$map_file"

    # If host was not found in the map, append a new entry
    if [[ "$found" == "false" ]]; then
        printf '%s\t%s\n' "$current_host" "$TARGET_LOCATION" >> "$tmp_file"
    fi

    mv "$tmp_file" "$map_file"
    echo "  Saved computer folder mapping: ${current_host} -> ${TARGET_LOCATION}"
}

# ------------------------------------------------------------------------------
# FUNCTION: rename_machine
# ------------------------------------------------------------------------------
# Renames a computer = renames its top-level folder. The folder name IS the
# machine identity (Phase 12 / v0.49.0 folder-centric model). Discovery mirrors
# select_computer (union of catalog-bearing top-level dirs + machine-labels.tsv
# values, deduped, alphabetical) and offers a Quit entry. After picking a
# computer and a validated new name, the folder old_dir -> new_dir is moved with
# a single plain mv (its archive/ subfolder rides along). The contained-file
# rewrite, map update, and single commit are built in Plan 02.
#
# Arguments:
#   None — reads RENAME_MODE (already validated), AUTO_COMMIT, SCRIPT_DIR globals
#
# Sets:
#   Nothing — operates entirely through side effects (folder mv; later: TSV
#   rewrite, file renames, git commit in Plan 02)
#
# Side effects:
#   - Moves the chosen computer folder old_dir -> new_dir (archive/ moves with it)
#   - (Plan 02) rewrites contained catalog filenames, rewrites the map, commits
#
# Guards:
#   - empty list        -> warn + exit 0 (nothing moved, no commit)
#   - Quit / q / EOF     -> exit 0 (nothing moved, no commit)
#   - new == old        -> warn + exit 0 (nothing moved, no commit)
#   - folder not found   -> warn + exit 0 (nothing moved, no commit)
#   - destination exists -> ERROR + exit 1 (HARD refuse-clobber, never merge)
# ------------------------------------------------------------------------------
rename_machine() {
    # 1. TTY guard — rename requires interactive prompts
    if [[ ! -t 0 ]]; then
        echo "ERROR: --rename requires an interactive terminal (stdin is not a TTY). Cannot prompt for computer names."
        exit 1
    fi

    local map_file="${SCRIPT_DIR}/machine-labels.tsv"

    # 2. Folder discovery: union of (a) top-level dirs containing catalogs and
    #    (b) machine-labels.tsv values, deduped. Same logic as select_computer;
    #    the remembered-default promotion is dropped (rename is not run-selection).
    setopt local_options null_glob
    typeset -a computers=()
    local d

    # Helper: returns 0 if $1 is already in computers[], 1 otherwise
    _name_in_list() {
        local candidate="$1"
        local existing
        for existing in "${computers[@]}"; do
            [[ "$existing" == "$candidate" ]] && return 0
        done
        return 1
    }

    # Source a: top-level dirs that contain at least one catalog ((/N) = dirs-only, null-glob)
    for d in "${SCRIPT_DIR}"/*(/N); do
        local base="${d:t}"
        local f=""    # MUST assign: a bare `local f` re-run each loop iteration makes
                      # zsh echo `f=<value>` to stdout (typeset-query behavior), leaking
                      # internal paths into the interactive menu. Assigning keeps it silent.
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

    # Order: alphabetical only (no remembered-default marker on the rename picker).
    computers=("${(@o)computers}")

    # Empty-list guard
    if [[ ${#computers[@]} -eq 0 ]]; then
        echo "No computers found. Nothing to rename."
        exit 0
    fi

    # 3. Numbered picker + Quit. Mirror select_computer's loop shape, but with NO
    #    Create-new and NO Enter-default (rename has neither).
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
        if ! read -r choice; then        # EOF (Ctrl-D / closed stdin) -> clean quit
            choice="$quit_idx"
        fi
        local lc="${choice:l}"           # zsh :l = lowercase modifier
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

    # 4. NEW name prompt — validated, re-prompt on invalid input (non-fatal validator)
    echo ""
    local new_name
    local reason
    while true; do
        printf "Enter new name for '${old_name}': "
        if ! read -r new_name; then          # EOF (Ctrl-D / closed stdin) -> clean quit
            echo "Nothing renamed."
            exit 0                            # clean quit — nothing moved, no commit
        fi
        reason=$(validate_computer_name_quiet "$new_name")
        if [[ $? -eq 0 ]]; then
            break
        fi
        echo "$reason"
    done

    # No-op guard: new == old
    if [[ "$new_name" == "$old_name" ]]; then
        echo "WARNING: New name is the same as the old name ('${old_name}'). Nothing to rename."
        exit 0
    fi

    # 5. Folder move with refuse-clobber + folder-not-found guards.
    local old_dir="${SCRIPT_DIR}/${old_name}"
    local new_dir="${SCRIPT_DIR}/${new_name}"

    # Folder-not-found guard (warn + exit 0, no move, no commit)
    if [[ ! -d "$old_dir" ]]; then
        echo "WARNING: Computer folder '${old_name}' not found. Nothing to rename."
        exit 0
    fi
    # Refuse-clobber (HARD): never merge two computers into one folder.
    if [[ -e "$new_dir" ]]; then
        echo "ERROR: A computer named '${new_name}' already exists. Refusing to merge. Nothing renamed."
        exit 1
    fi

    # Single plain mv — archive/ subfolder moves with it. (Not git mv; staged via
    # git add -A below.) Move FIRST, before any contained-filename rewrite.
    mv "$old_dir" "$new_dir"
    echo "  Renamed folder: ${old_name}/ -> ${new_name}/"

    # 6. Opt-out-gated in-folder filename rewrite. The folder is ALREADY moved;
    #    these counters describe only the contained-file rewrites and feed the
    #    closing summary. They are initialized BEFORE the branch so they exist in
    #    both rewrite (Y) and opt-out (n) modes. There is intentionally NO
    #    renamed_count==0 abort here: the folder move already happened and the map
    #    MUST update + commit even when zero files are rewritten (opt-out, or all
    #    collisions / all-non-matching).
    local renamed_count=0
    local skipped_count=0

    printf "Rewrite all existing catalogs in '${new_name}' to '[${new_name}]'? [Y/n]: "
    local rewrite_ans
    read -r rewrite_ans
    local lc_ans="${rewrite_ans:l}"
    if [[ -z "$lc_ans" || "$lc_ans" == "y" || "$lc_ans" == "yes" ]]; then
        # Scope: the MOVED folder's main dir + its archive (only — not the old
        # 4-hardcoded-dir set). Rewrite only files whose [label] equals old_name.
        local rewrite_dirs=("$new_dir" "${new_dir}/archive")
        local dir2
        for dir2 in "${rewrite_dirs[@]}"; do
            [[ ! -d "$dir2" ]] && continue
            setopt local_options null_glob
            local file2=""    # assign (not bare `local`): a re-run bare `local` echoes
                              # `file2=<value>` to stdout on the 2nd+ dir iteration.
            for file2 in "${dir2}"/mac-software-list-*.txt; do
                [[ -e "$file2" ]] || continue
                [[ -d "$file2" ]] && continue
                local filename2="${file2:t}"
                local tmp2="${filename2#*\[}"
                local file_label2="${tmp2%\]-*}"
                # Only rewrite files whose [label] equals old_name exactly;
                # mixed-label transition files are left untouched.
                [[ "$file_label2" != "$old_name" ]] && continue
                # Extract 14-digit timestamp via pure-zsh parameter expansion (zero forks)
                local base="${filename2%.txt}"
                local ts="${base##*-}"
                if [[ -z "$ts" || ! "$ts" =~ ^[0-9]{14}$ ]]; then
                    echo "  WARNING: Could not parse timestamp from: ${filename2} — skipping"
                    continue
                fi
                local new_filename="mac-software-list-[${new_name}]-${ts}.txt"
                local dest="${dir2}/${new_filename}"
                # Collision guard: skip if destination already exists (never overwrite)
                if [[ -e "$dest" ]]; then
                    echo "  WARNING: Destination already exists, skipping: ${new_filename}"
                    ((skipped_count++))
                    continue
                fi
                mv "$file2" "$dest"
                echo "  Renamed: ${filename2} -> ${new_filename}"
                ((renamed_count++))
            done
        done
    fi
    # else: opt-out — folder is moved, filenames keep their old [label]; the map
    #       still updates and the change is still committed below.

    # 7. Map update — atomically rewrite machine-labels.tsv. UNCONDITIONAL: runs
    #    in BOTH rewrite (Y) and opt-out (n) modes because the folder name is the
    #    computer identity, so EVERY hostname -> old_name entry must repoint to
    #    new_name regardless of whether any filenames were rewritten.
    local tmp_file="${map_file}.tmp"
    if [[ -f "$map_file" ]]; then
        # `: > file` (colon builtin) truncates without invoking $NULLCMD. A bare
        # `> file` in zsh runs $READNULLCMD (cat) reading from stdin, which blocks
        # forever on an interactive --rename. Use the explicit no-op command.
        : > "$tmp_file"
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Blank lines: preserve verbatim
            if [[ -z "$line" ]]; then
                printf '\n' >> "$tmp_file"
                continue
            fi
            # Comment lines: preserve verbatim
            if [[ "$line" =~ ^# ]]; then
                printf '%s\n' "$line" >> "$tmp_file"
                continue
            fi
            # Data line: only treat as a label-bearing entry if it actually
            # contains a TAB. A no-tab line (bare hostname, hand-edited) must
            # never be rewritten — ${line#*\t} would otherwise fall back to the
            # whole line and wrongly match a hostname equal to old_name.
            if [[ "$line" == *$'\t'* && "${line#*$'\t'}" == "$old_name" ]]; then
                # Replace folder column with new_name
                printf '%s\t%s\n' "${line%%$'\t'*}" "$new_name" >> "$tmp_file"
            else
                # Preserve verbatim
                printf '%s\n' "$line" >> "$tmp_file"
            fi
        done < "$map_file"
        mv "$tmp_file" "$map_file"
        echo "  Updated machine-labels.tsv: '${old_name}' -> '${new_name}'"
    fi

    # 8. Single git commit (or --no-commit manual path). Stage the OLD folder path
    #    (records the move's deletions), the NEW folder path (records the moved
    #    folder + any rewritten filenames), and the map — all in ONE commit. The
    #    commit is gated on staged changes (the folder MOVED), not on renamed_count.
    if [[ "$AUTO_COMMIT" == "true" ]]; then
        cd "$SCRIPT_DIR" || {
            echo "  WARNING: Could not change to script directory. Skipping git operations."
            return
        }
        if ! git rev-parse --git-dir &>/dev/null; then
            echo "  WARNING: Not a git repository. Skipping git operations."
            return
        fi
        # git add -A on the old path name is safe even though the dir no longer
        # exists — it stages the folder's removals. The 2>/dev/null || true keeps
        # a missing path from aborting the staging. The `--` end-of-options marker
        # ensures a leading-dash folder name (e.g. '-foo') is treated as a pathspec,
        # not parsed as a git option — otherwise staging silently fails and a
        # partial/inconsistent commit (map updated, folder move unstaged) results.
        git add -A -- "${old_name}/" 2>/dev/null || true
        git add -A -- "${new_name}/" 2>/dev/null || true
        git add -- machine-labels.tsv 2>/dev/null || true
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
        echo "  cd $SCRIPT_DIR && git add -A -- '${old_name}/' && git add -A -- '${new_name}/' && git add -- machine-labels.tsv"
        echo "  git commit -m 'Rename computer: ${old_name} -> ${new_name}'"
        echo "  git push"
    fi

    # 9. Summary
    echo ""
    echo "Rename complete: folder '${old_name}/' -> '${new_name}/'; ${renamed_count} catalog(s) rewritten, ${skipped_count} skipped (destination collision)."
}

# ------------------------------------------------------------------------------
# FUNCTION: retain_newest_per_host
# ------------------------------------------------------------------------------
# Keeps the newest catalog per hostname in the main folder and moves all older
# catalogs for each host into the archive subfolder.
# "Newest" is determined by the 14-digit YYYYMMDDHHMMSS timestamp embedded in
# the filename — NOT by file mtime.
#
# Arguments:
#   $1 - The directory to process (e.g., "personal" or "office")
#
# The function:
#   1. Creates the archive folder if it doesn't exist
#   2. Pass 1: scans all catalog files, builds a per-host newest-timestamp map
#   3. Pass 2: moves any file whose timestamp is not the max for its host to archive/
#   4. Tied-newest files are ALL kept (data-loss-averse)
# ------------------------------------------------------------------------------
retain_newest_per_host() {
    local target_dir="$1"
    local full_path="${SCRIPT_DIR}/${target_dir}"
    local archive_path="${full_path}/archive"

    echo ""
    echo "Retaining newest catalog per machine in ${target_dir}/..."

    # Create archive directory if it doesn't exist
    if [[ ! -d "$archive_path" ]]; then
        mkdir -p "$archive_path"
        echo "  Created archive directory: ${archive_path}"
    fi

    # Pass 1: find the newest (max) timestamp per hostname
    setopt local_options null_glob
    typeset -A newest_ts
    for file in "${full_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local tmp="${filename#*\[}"
        local host="${tmp%\]-*}"    # %\]-* strips everything from the first "]-" onward; works for labels with spaces
        local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
        if [[ -z "$ts" || -z "$host" || "$host" == "$filename" ]]; then
            echo "  WARNING: Could not parse hostname/timestamp from: $filename"
            continue
        fi
        if [[ -z "${newest_ts[$host]}" || "$ts" > "${newest_ts[$host]}" ]]; then
            newest_ts[$host]="$ts"
        fi
    done

    # Pass 2: move any file that is NOT the newest for its host
    local moved_count=0
    for file in "${full_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local tmp="${filename#*\[}"
        local host="${tmp%\]-*}"    # %\]-* strips everything from the first "]-" onward; works for labels with spaces
        local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
        if [[ -z "$ts" || -z "$host" || "$host" == "$filename" ]]; then
            continue    # already warned in pass 1
        fi
        # ts == newest_ts[host]: keep it (includes tied-newest case)
        if [[ "$ts" == "${newest_ts[$host]}" ]]; then
            continue
        fi
        if mv "$file" "${archive_path}/"; then
            echo "  Archived: $filename"
            ((moved_count++))
        else
            echo "  WARNING: Could not archive: $filename — leaving in place"
        fi
    done

    if [[ $moved_count -eq 0 ]]; then
        echo "  No older catalogs to archive."
    else
        echo "  Archived $moved_count catalog(s) to ${target_dir}/archive/"
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: prune_old_archives
# ------------------------------------------------------------------------------
# Hard-deletes catalog files in the archive subfolder whose filename timestamp
# is older than ARCHIVE_AGE_DAYS. Uses BSD date -v arithmetic (macOS-only).
# Unparseable filenames are skipped with a warning — never deleted.
#
# Arguments:
#   $1 - The directory to process (e.g., "personal" or "office")
#
# The function:
#   1. Returns early if archive/ does not exist
#   2. Computes a cutoff date (today minus ARCHIVE_AGE_DAYS)
#   3. For each catalog file in archive/, extracts the 8-digit YYYYMMDD date
#   4. Hard-deletes files whose date is older than the cutoff
# ------------------------------------------------------------------------------
prune_old_archives() {
    local target_dir="$1"
    local full_path="${SCRIPT_DIR}/${target_dir}"
    local archive_path="${full_path}/archive"

    echo ""
    echo "Pruning archive catalogs older than ${ARCHIVE_AGE_DAYS} days..."

    # If archive doesn't exist, nothing to prune
    if [[ ! -d "$archive_path" ]]; then
        echo "  No archive directory found — nothing to prune."
        return
    fi

    local cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")
    local pruned_count=0
    setopt local_options null_glob

    for file in "${archive_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local timestamp=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-8)
        if [[ -z "$timestamp" ]]; then
            echo "  WARNING: Could not parse timestamp from: $filename — skipping"
            continue
        fi
        if [[ "$timestamp" -lt "$cutoff_date" ]]; then
            if rm "$file"; then
                echo "  Pruned: $filename"
                ((pruned_count++))
            else
                echo "  WARNING: Could not prune: $filename — leaving in place"
            fi
        fi
    done

    if [[ $pruned_count -eq 0 ]]; then
        echo "  No archive catalogs needed pruning."
    else
        echo "  Pruned $pruned_count catalog(s) from ${target_dir}/archive/"
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: write_section
# ------------------------------------------------------------------------------
# Writes a formatted section header to the output file.
# Used to visually separate different categories of software in the catalog.
#
# Arguments:
#   $1 - The section title to write
# ------------------------------------------------------------------------------
write_section() {
    echo "\n$1" >> "$OUTPUT_FILE"
    echo "------------------------------------" >> "$OUTPUT_FILE"
}

# ------------------------------------------------------------------------------
# FUNCTION: json_get
# ------------------------------------------------------------------------------
# Extracts a scalar value from a JSON file by dotted key path.
# Returns the value on stdout; returns empty string on miss or error.
# Never aborts — callers test for empty, matching the shell idiom used
# throughout this script.
#
# Arguments:
#   $1 - Path to the JSON file
#   $2 - Dotted key path (e.g. "name", "author.name", "a.b.c")
#
# Returns:
#   Echoes the string value to stdout; empty string on miss, error, or missing file
#
# Backend chain: jq (preferred, Homebrew) → plutil (always present on macOS since 10.4)
# python3 is NOT in the chain — on a clean macOS it is an xcrun stub that opens a
# GUI dialog and blocks the script.
# ------------------------------------------------------------------------------
json_get() {
    local file="$1"
    local key="$2"
    local value=""

    # Guard: file must exist and be readable
    [[ -f "$file" ]] || { echo ""; return; }
    # Guard: key must be non-empty (empty key causes jq getpath([]) to dump entire root object)
    [[ -n "$key" ]] || { echo ""; return; }

    if command -v jq &>/dev/null; then
        # jq: getpath with split(".") handles dotted nested paths
        # // "" coerces null to empty string; 2>/dev/null suppresses parse errors
        value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null) || value=""
    else
        # plutil: always present on macOS since 10.4
        # -extract <keypath> raw -o - writes value to stdout, exits 1 on miss
        # || value="" ensures we return empty string rather than propagating exit 1
        value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
    fi

    echo "$value"
}

# ------------------------------------------------------------------------------
# FUNCTION: chrome_ext_name
# ------------------------------------------------------------------------------
# Given a path to a Chrome extension manifest.json, returns the human-readable
# extension name. Resolves __MSG_<key>__ placeholder names via the extension's
# _locales/<default_locale>/messages.json using case-insensitive key matching.
#
# Arguments:
#   $1 - Absolute path to the extension's manifest.json
#
# Returns:
#   Echoes the resolved name to stdout.
#   Falls back to the 32-char extension ID (grandparent directory basename) when:
#     - name is empty in the manifest
#     - __MSG_ placeholder cannot be resolved (messages.json absent or key missing)
#   Never emits a blank name or a raw __MSG_ string.
#
# Chrome extension directory structure:
#   <ext_id>/            ← 32-char ID, grandparent of manifest.json
#     <version_dir>/     ← e.g. "2026.5.1_0"
#       manifest.json
#       _locales/
#         en/
#           messages.json
# ------------------------------------------------------------------------------
chrome_ext_name() {
    local manifest="$1"
    local name=""
    local locale=""
    local msg_key=""
    local messages_file=""
    local ext_id=""
    local resolved=""

    # Extension ID is the grandparent directory name (parent of the version dir)
    ext_id=$(basename "$(dirname "$(dirname "$manifest")")")

    name=$(json_get "$manifest" "name")

    # Plain name — return immediately (covers the common case)
    # ?* requires at least one character between prefix and suffix, matching Chrome spec
    if [[ "$name" != __MSG_?*__ ]]; then
        # If name is empty, fall back to extension ID
        [[ -n "$name" ]] && echo "$name" || echo "$ext_id"
        return
    fi

    # Extract message key: strip __MSG_ prefix and __ suffix
    msg_key="${name#__MSG_}"
    msg_key="${msg_key%__}"

    # Get default_locale from manifest; fall back to "en" if absent
    locale=$(json_get "$manifest" "default_locale")
    [[ -z "$locale" ]] && locale="en"

    # Construct path to the locale messages file (quoted to handle spaces in path)
    messages_file="$(dirname "$manifest")/_locales/${locale}/messages.json"

    if [[ ! -f "$messages_file" ]]; then
        echo "$ext_id"
        return
    fi

    # Case-insensitive key lookup in messages.json
    # jq: ascii_downcase both sides for reliable case-insensitive match
    # plutil fallback: try exact-case key first, then lowercase (covers common cases)
    if command -v jq &>/dev/null; then
        resolved=$(jq -r --arg k "${msg_key:l}" \
            'to_entries[] | select(.key | ascii_downcase == $k) | .value.message' \
            "$messages_file" 2>/dev/null | head -1)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
    else
        # plutil fallback: try exact-case key first (common case matches placeholder exactly)
        resolved=$(plutil -extract "${msg_key}.message" raw -o - "$messages_file" 2>/dev/null)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
        # Case mismatch: try lowercase key (handles extName → extname)
        resolved=$(plutil -extract "${msg_key:l}.message" raw -o - "$messages_file" 2>/dev/null)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
    fi

    # All lookups failed — use extension ID as fallback (never blank per CHR-01)
    echo "$ext_id"
}

# ------------------------------------------------------------------------------
# FUNCTION: emit_item
# ------------------------------------------------------------------------------
# Builds one catalog line from (name, version, id) and appends it to the
# _section_lines global array. Applies all FMT-01 degradation rules so every
# collector renders identically regardless of which fields are available.
#
# Arguments:
#   $1 - name    (display name; may be empty)
#   $2 - version (version string; may be empty)
#   $3 - id      (stable identifier, e.g. extension ID or bundle ID; may be empty)
#
# FMT-01 degradation rules:
#   name + version + id  →  "name (version) [id]"
#   name + version       →  "name (version)"
#   name + id            →  "name [id]"
#   name only            →  "name"
#   id only (no name)    →  "id"          (ID used as name, brackets suppressed)
#   id + version         →  "id (version)" (ID used as name, brackets suppressed)
#   all empty            →  (nothing emitted)
#
# NOTE: _section_lines is a script-global array. Each collector that calls emit_item
# MUST reset _section_lines=() at its top before the first emit_item call. This
# prevents lines from a prior section leaking into the current section's output.
# flush_section resets the buffer after writing, but a defensive reset at the
# collector top is required to handle early-exit paths that skip flush_section.
# ------------------------------------------------------------------------------
emit_item() {
    local name="$1"
    local version="$2"
    local id="$3"
    local line=""

    # Name unresolvable: use ID as name and suppress bracket duplication
    # (avoids emitting "id [id]" when only the ID is known)
    if [[ -z "$name" && -n "$id" ]]; then
        name="$id"
        id=""
    fi

    # Build line per FMT-01 rules
    if [[ -n "$name" && -n "$version" && -n "$id" ]]; then
        line="${name} (${version}) [${id}]"
    elif [[ -n "$name" && -n "$version" ]]; then
        line="${name} (${version})"
    elif [[ -n "$name" && -n "$id" ]]; then
        line="${name} [${id}]"
    elif [[ -n "$name" ]]; then
        line="$name"
    else
        return  # all fields empty — nothing to emit
    fi

    _section_lines+=("$line")
}

# ------------------------------------------------------------------------------
# FUNCTION: flush_section
# ------------------------------------------------------------------------------
# Sorts and deduplicates _section_lines[], appends the result to OUTPUT_FILE,
# then resets the buffer. Called once per section after all emit_item calls.
#
# Sort specification (FMT-04):
#   LC_ALL=C  — byte-stable ordering, immune to locale differences between machines
#   -f        — case-insensitive fold (human-readable ordering: 1Password < Bitwarden < Zed)
#   -u        — deduplicate identical lines (two consecutive no-change runs → empty diff)
#
# Empty buffer: writes "  (none found)" so the section is never silently blank.
#
# COLLECTOR CONTRACT: Each collector must reset _section_lines=() at its top
# before calling emit_item. flush_section resets the buffer after writing, but
# a defensive reset ensures correctness when a collector exits early without
# calling flush_section (e.g., when the source tool is not installed).
# ------------------------------------------------------------------------------
flush_section() {
    if [[ ${#_section_lines[@]} -eq 0 ]]; then
        echo "  (none found)" >> "$OUTPUT_FILE"
    else
        printf "%s\n" "${_section_lines[@]}" | LC_ALL=C sort -f -u >> "$OUTPUT_FILE"
    fi
    _section_lines=()
}

# ------------------------------------------------------------------------------
# FUNCTION: resolve_vsc_ext_name
# ------------------------------------------------------------------------------
# Resolves a VS Code / Cursor extension's human-readable display name from its
# package.json, with NLS placeholder resolution via package.nls.json.
#
# Arguments:
#   $1 - Absolute path to the extension's package.json
#   $2 - Extension ID (e.g. "ms-python.python") — used as fallback name
#
# Returns: echoes the resolved name to stdout; never blank, never raw %key%
#
# Schema note: package.nls.json stores FLAT STRING values (not {message:...}
# objects like Chrome's _locales/messages.json). Keys may contain literal dots
# (e.g. "extension.title") — use .[$k] in jq (NOT getpath), and backslash-escape
# dots for plutil ("extension\.title").
# ------------------------------------------------------------------------------
resolve_vsc_ext_name() {
    local pkg_json="$1"
    local ext_id="$2"
    local dn=""
    local nls_key=""
    local nls_file=""
    local escaped_key=""
    local resolved=""

    dn=$(json_get "$pkg_json" "displayName")

    # No displayName in package.json — fall back to extension ID
    [[ -z "$dn" ]] && { echo "$ext_id"; return; }

    # Plain string — return immediately (most extensions)
    # Pattern: %key% where key is at least 1 character
    if [[ "$dn" != %?*% ]]; then
        echo "$dn"
        return
    fi

    # NLS placeholder: strip leading % and trailing %
    nls_key="${dn#%}"
    nls_key="${nls_key%\%}"

    # NLS file lives alongside package.json in the extension root dir
    nls_file="$(dirname "$pkg_json")/package.nls.json"
    if [[ ! -f "$nls_file" ]]; then
        echo "$ext_id"
        return
    fi

    # package.nls.json uses FLAT string values (not {message:...} objects).
    # Keys may contain literal dots (e.g. "extension.title") — treat as flat keys.
    if command -v jq &>/dev/null; then
        # jq: .[$k] treats key as a flat top-level key (handles dots in key name)
        # NOT getpath($k | split(".")) — that would misinterpret dotted flat keys
        resolved=$(jq -r --arg k "$nls_key" '.[$k] // ""' "$nls_file" 2>/dev/null)
    else
        # plutil: escape literal dots with backslash before passing to -extract
        escaped_key="${nls_key//./\\.}"
        resolved=$(plutil -extract "$escaped_key" raw -o - "$nls_file" 2>/dev/null) || resolved=""
    fi

    if [[ -n "$resolved" ]]; then
        echo "$resolved"
        return
    fi

    # All lookups failed — fall back to extension ID (never blank, never raw %key%)
    echo "$ext_id"
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_vscode_extensions
# ------------------------------------------------------------------------------
# Catalogs installed VS Code extensions with human-readable display names,
# versions, and extension IDs.
#
# Source preference:
#   1. CLI (code --list-extensions --show-versions) when on PATH
#   2. ~/.vscode/extensions/extensions.json (file fallback — operative on this machine)
#
# Uses relativeLocation from extensions.json to locate each extension's
# package.json — never reconstructs the path from id+version (platform suffixes
# like -darwin-arm64 make naive reconstruction ambiguous).
#
# Display name resolution: resolve_vsc_ext_name (NLS-aware, with fallback to ID).
# Output: routed through emit_item -> flush_section (sorted, deduplicated).
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_vscode_extensions() {
    local ext_dir="$HOME/.vscode/extensions"
    local ext_json="$ext_dir/extensions.json"
    local id="" version="" rel_loc="" pkg_json="" display_name="" cli_output="" entry="" line=""
    local idx=0

    write_section "VS Code Extensions"
    _section_lines=()

    # CLI path (preferred when present)
    if command -v code &>/dev/null; then
        cli_output=$(code --list-extensions --show-versions 2>/dev/null)
        if [[ -n "$cli_output" ]]; then
            # CLI yields id@version; split on last @ for version
            while IFS= read -r line; do
                [[ -z "$line" ]] && continue
                id="${line%@*}"
                version="${line##*@}"
                # Guard: if no @ separator found, id and version equal the whole
                # line — skip malformed/non-extension output from the CLI
                [[ "$id" == "$version" ]] && continue
                # Still need extensions.json for relativeLocation -> package.json
                rel_loc=""
                if [[ -f "$ext_json" ]]; then
                    if command -v jq &>/dev/null; then
                        rel_loc=$(jq -r --arg i "$id" \
                            '.[] | select(.identifier.id == $i) | .relativeLocation // ""' \
                            "$ext_json" 2>/dev/null | head -1)
                    else
                        # plutil fallback: scan by index for matching identifier.id
                        local scan_idx=0
                        local scan_id=""
                        while true; do
                            scan_id=$(plutil -extract "${scan_idx}.identifier.id" raw -o - "$ext_json" 2>/dev/null) || break
                            if [[ "$scan_id" == "$id" ]]; then
                                rel_loc=$(plutil -extract "${scan_idx}.relativeLocation" raw -o - "$ext_json" 2>/dev/null) || rel_loc=""
                                break
                            fi
                            scan_idx=$((scan_idx + 1))
                        done
                    fi
                fi
                if [[ -n "$rel_loc" ]]; then
                    pkg_json="$ext_dir/$rel_loc/package.json"
                    display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
                else
                    display_name="$id"
                fi
                emit_item "$display_name" "$version" "$id"
            done <<< "$cli_output"
            flush_section
            return
        fi
        echo "  WARNING: code CLI returned empty list. Falling back to extensions.json."
    fi

    # File fallback path (always executes on this machine)
    if [[ ! -f "$ext_json" ]]; then
        echo "  NOTE: VS Code not installed or no extensions found."
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS= read -r entry; do
            id=$(echo "$entry" | jq -r '.identifier.id // ""' 2>/dev/null)
            version=$(echo "$entry" | jq -r '.version // ""' 2>/dev/null)
            rel_loc=$(echo "$entry" | jq -r '.relativeLocation // ""' 2>/dev/null)
            [[ -z "$id" ]] && continue
            pkg_json="$ext_dir/$rel_loc/package.json"
            display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
            emit_item "$display_name" "$version" "$id"
        done < <(jq -c '.[]' "$ext_json" 2>/dev/null)
    else
        # plutil fallback: iterate by index until miss
        idx=0
        while true; do
            id=$(plutil -extract "${idx}.identifier.id" raw -o - "$ext_json" 2>/dev/null) || break
            version=$(plutil -extract "${idx}.version" raw -o - "$ext_json" 2>/dev/null) || version=""
            rel_loc=$(plutil -extract "${idx}.relativeLocation" raw -o - "$ext_json" 2>/dev/null) || rel_loc=""
            [[ -z "$id" ]] && { ((idx++)); continue; }
            pkg_json="$ext_dir/$rel_loc/package.json"
            display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
            emit_item "$display_name" "$version" "$id"
            ((idx++))
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_cursor_extensions
# ------------------------------------------------------------------------------
# Catalogs installed Cursor extensions with human-readable display names,
# versions, and extension IDs.
#
# Identical to collect_vscode_extensions with three substitutions:
#   - ext_dir: ~/.cursor/extensions
#   - CLI: cursor --list-extensions --show-versions
#   - Section title: "Cursor Extensions"
#
# Uses relativeLocation from extensions.json to locate each extension's
# package.json — never reconstructs the path from id+version.
# Display name resolution: resolve_vsc_ext_name (editor-agnostic).
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_cursor_extensions() {
    local ext_dir="$HOME/.cursor/extensions"
    local ext_json="$ext_dir/extensions.json"
    local id="" version="" rel_loc="" pkg_json="" display_name="" cli_output="" entry="" line=""
    local idx=0

    write_section "Cursor Extensions"
    _section_lines=()

    # CLI path (preferred when present)
    if command -v cursor &>/dev/null; then
        cli_output=$(cursor --list-extensions --show-versions 2>/dev/null)
        if [[ -n "$cli_output" ]]; then
            # CLI yields id@version; split on last @ for version
            while IFS= read -r line; do
                [[ -z "$line" ]] && continue
                id="${line%@*}"
                version="${line##*@}"
                # Guard: if no @ separator found, id and version equal the whole
                # line — skip malformed/non-extension output from the CLI
                [[ "$id" == "$version" ]] && continue
                # Still need extensions.json for relativeLocation -> package.json
                rel_loc=""
                if [[ -f "$ext_json" ]]; then
                    if command -v jq &>/dev/null; then
                        rel_loc=$(jq -r --arg i "$id" \
                            '.[] | select(.identifier.id == $i) | .relativeLocation // ""' \
                            "$ext_json" 2>/dev/null | head -1)
                    else
                        # plutil fallback: scan by index for matching identifier.id
                        local scan_idx=0
                        local scan_id=""
                        while true; do
                            scan_id=$(plutil -extract "${scan_idx}.identifier.id" raw -o - "$ext_json" 2>/dev/null) || break
                            if [[ "$scan_id" == "$id" ]]; then
                                rel_loc=$(plutil -extract "${scan_idx}.relativeLocation" raw -o - "$ext_json" 2>/dev/null) || rel_loc=""
                                break
                            fi
                            scan_idx=$((scan_idx + 1))
                        done
                    fi
                fi
                if [[ -n "$rel_loc" ]]; then
                    pkg_json="$ext_dir/$rel_loc/package.json"
                    display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
                else
                    display_name="$id"
                fi
                emit_item "$display_name" "$version" "$id"
            done <<< "$cli_output"
            flush_section
            return
        fi
        echo "  WARNING: cursor CLI returned empty list. Falling back to extensions.json."
    fi

    # File fallback path (always executes on this machine)
    if [[ ! -f "$ext_json" ]]; then
        echo "  NOTE: Cursor not installed or no extensions found."
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS= read -r entry; do
            id=$(echo "$entry" | jq -r '.identifier.id // ""' 2>/dev/null)
            version=$(echo "$entry" | jq -r '.version // ""' 2>/dev/null)
            rel_loc=$(echo "$entry" | jq -r '.relativeLocation // ""' 2>/dev/null)
            [[ -z "$id" ]] && continue
            pkg_json="$ext_dir/$rel_loc/package.json"
            display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
            emit_item "$display_name" "$version" "$id"
        done < <(jq -c '.[]' "$ext_json" 2>/dev/null)
    else
        # plutil fallback: iterate by index until miss
        idx=0
        while true; do
            id=$(plutil -extract "${idx}.identifier.id" raw -o - "$ext_json" 2>/dev/null) || break
            version=$(plutil -extract "${idx}.version" raw -o - "$ext_json" 2>/dev/null) || version=""
            rel_loc=$(plutil -extract "${idx}.relativeLocation" raw -o - "$ext_json" 2>/dev/null) || rel_loc=""
            [[ -z "$id" ]] && { ((idx++)); continue; }
            pkg_json="$ext_dir/$rel_loc/package.json"
            display_name=$(resolve_vsc_ext_name "$pkg_json" "$id")
            emit_item "$display_name" "$version" "$id"
            ((idx++))
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_claude_plugins
# ------------------------------------------------------------------------------
# Catalogs installed Claude Code plugins from:
#   ~/.claude/plugins/installed_plugins.json
# The plugins object is keyed by "name@marketplace"; value[0].version holds the
# version string. Emits: name (version) [name@marketplace]
# Graceful degradation: absent file or malformed JSON → "(none found)"
# ------------------------------------------------------------------------------
collect_claude_plugins() {
    local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
    local name="" version="" key="" ver=""

    write_section "Claude Code Plugins"
    _section_lines=()

    if [[ ! -f "$plugins_file" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r key version; do
            [[ -z "$key" ]] && continue
            name="${key%%@*}"
            emit_item "$name" "$version" "$key"
        done < <(jq -r '.plugins | to_entries[] | .key + "\t" + (.value[0].version // "")' \
                     "$plugins_file" 2>/dev/null)
    else
        # plutil fallback: enumerate plugin keys via xml1 parsing
        while IFS= read -r key; do
            [[ -z "$key" ]] && continue
            name="${key%%@*}"
            ver=""
            ver=$(plutil -extract "plugins.${key}.0.version" raw -o - "$plugins_file" 2>/dev/null) || ver=""
            emit_item "$name" "$ver" "$key"
        done < <(plutil -extract "plugins" xml1 -o - "$plugins_file" 2>/dev/null \
                     | grep '<key>' | sed 's/.*<key>//;s/<\/key>//')
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_claude_mcp
# ------------------------------------------------------------------------------
# Catalogs configured Claude Code MCP servers from ~/.claude.json .mcpServers.
# FMT-03 COMPLIANCE: reads ONLY .key (server name) and .value.type (transport).
# NEVER reads .value.env, .value.command, .value.args, .value.url, .value.headers.
# Transport label is clamped to stdio|http|sse whitelist.
# Emits: name [transport]
# Graceful degradation: absent config → "(none found)"
# ------------------------------------------------------------------------------
collect_claude_mcp() {
    local claude_config="$HOME/.claude.json"
    local name="" transport=""

    write_section "Claude Code MCP Servers"
    _section_lines=()

    if [[ ! -f "$claude_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r name transport; do
            [[ -z "$name" ]] && continue
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "${transport:-stdio}"
        done < <(jq -r '.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")' \
                     "$claude_config" 2>/dev/null)
    else
        # plutil fallback: enumerate server names, then extract type per server (ONLY .type scalar)
        local server_names=()
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            server_names+=("$name")
        done < <(plutil -extract "mcpServers" raw -o - "$claude_config" 2>/dev/null)

        for name in "${server_names[@]}"; do
            transport=$(plutil -extract "mcpServers.${name}.type" raw -o - \
                            "$claude_config" 2>/dev/null) || transport="stdio"
            [[ -z "$transport" ]] && transport="stdio"
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "$transport"
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_claude_skills_agents
# ------------------------------------------------------------------------------
# Catalogs Claude Code skills and agents into a single combined section.
# Skills:  ~/.claude/skills/ — one subdir per skill; name from SKILL.md frontmatter
# Agents:  ~/.claude/agents/*.md — name from YAML frontmatter name: field
# Both directories are null-glob-guarded for safe iteration.
# No version or ID is available; emits bare name.
# ------------------------------------------------------------------------------
collect_claude_skills_agents() {
    local skills_dir="$HOME/.claude/skills"
    local agents_dir="$HOME/.claude/agents"
    local name=""

    write_section "Claude Code Skills & Agents"
    _section_lines=()

    setopt local_options null_glob   # one call covers both loops below

    # Skills: one subdir per skill
    if [[ -d "$skills_dir" ]]; then
        for skill_dir in "$skills_dir"/*/; do
            [[ -e "$skill_dir" ]] || continue
            name=""                                   # reset at start of each iteration
            local skill_md="${skill_dir}SKILL.md"
            if [[ -f "$skill_md" ]]; then
                name=$(grep '^name:' "$skill_md" | head -1 \
                           | sed 's/^name:[[:space:]]*//' | tr -d '"')
            fi
            [[ -z "$name" ]] && name=$(basename "$skill_dir")
            emit_item "$name" "" ""
            name=""                                   # keep end reset for symmetry
        done
    fi

    # Agents: *.md files in agents dir
    if [[ -d "$agents_dir" ]]; then
        for f in "$agents_dir"/*.md; do
            [[ -e "$f" ]] || continue
            name=$(grep '^name:' "$f" | head -1 \
                       | sed 's/^name:[[:space:]]*//' | tr -d '"')
            [[ -z "$name" ]] && name=$(basename "$f" .md)
            emit_item "$name" "" ""
            name=""
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_codex_mcp
# ------------------------------------------------------------------------------
# Catalogs configured Codex MCP servers from the CLI or TOML config.
# FMT-03 COMPLIANCE: reads ONLY server name and transport type.
# NEVER reads .command, .env, .args, .url, .headers from CLI output or TOML.
#
# Primary path:  codex mcp list --json  (returns [] on this machine — no servers)
# Fallback path: grep [mcp_servers.*] section headers from ~/.codex/config.toml
#                — reads section header names ONLY; value lines never touched.
# Transport defaults to "stdio" in TOML fallback (CLI is canonical source).
# Emits: name [transport]
# Graceful degradation: CLI absent + no config → "(none found)"
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_codex_mcp() {
    local codex_config="$HOME/.codex/config.toml"
    local name="" transport=""

    write_section "Codex MCP Servers"
    _section_lines=()

    # Preferred: CLI (codex mcp list --json)
    if command -v codex &>/dev/null; then
        local cli_out=""
        cli_out=$(codex mcp list --json 2>/dev/null)
        if [[ -n "$cli_out" && "$cli_out" != "[]" ]]; then
            if command -v jq &>/dev/null; then
                while IFS=$'\t' read -r name transport; do
                    [[ -z "$name" ]] && continue
                    case "$transport" in
                        stdio|http|sse) : ;;
                        *) transport="stdio" ;;
                    esac
                    emit_item "$name" "" "${transport:-stdio}"
                done < <(jq -r '.[] | .name + "\t" + (.type // "stdio")' \
                              <<< "$cli_out" 2>/dev/null)
                flush_section
                return
            fi
            # jq absent: fall through to TOML fallback (plutil can't parse CLI JSON inline)
        fi
    fi

    # Fallback: TOML grep — section header names only; transport defaults to stdio
    # KEY RULE (FMT-03): only [mcp_servers.<name>] section headers are read;
    # value lines (command, env, args, url, headers) are never touched.
    if [[ -f "$codex_config" ]]; then
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            emit_item "$name" "" "stdio"
        done < <(grep '^\[mcp_servers\.' "$codex_config" 2>/dev/null \
                     | sed 's/[[:space:]]*#.*$//' \
                     | sed 's/^\[mcp_servers\.\(.*\)\]$/\1/' | tr -d '"')
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_opencode_plugins
# ------------------------------------------------------------------------------
# Catalogs installed OpenCode plugins from ~/.config/opencode/opencode.json .plugin
# The .plugin field is a JSON string array of "name@source" entries.
# Name is extracted as the substring before the first @ (Pitfall 3 guard).
# No version is available for OpenCode plugins — emits bare name only.
# Graceful degradation: absent config or null .plugin field → "(none found)"
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_opencode_plugins() {
    local oc_config="$HOME/.config/opencode/opencode.json"
    local name="" entry=""

    write_section "OpenCode Plugins"
    _section_lines=()

    if [[ ! -f "$oc_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS= read -r entry; do
            [[ -z "$entry" ]] && continue
            name="${entry%%@*}"
            # Guard: if no '@' was found and the entry contains '/', it is a filesystem
            # path or URL — skip it with a warning to avoid leaking machine-specific paths.
            if [[ "$name" == "$entry" && "$entry" == */* ]]; then
                echo "  WARNING: OpenCode plugin entry has no '@' separator and looks like a path/URL — skipping: ${entry}" >&2
                continue
            fi
            [[ -z "$name" ]] && continue
            emit_item "$name" "" ""
        done < <(jq -r '.plugin[]?' "$oc_config" 2>/dev/null)
    else
        # plutil fallback: extract each array element by index
        local idx=0
        while true; do
            entry=$(plutil -extract "plugin.${idx}" raw -o - "$oc_config" 2>/dev/null) || break
            [[ -z "$entry" ]] && break
            name="${entry%%@*}"
            # Same guard as jq path: skip path/URL entries that have no '@' separator.
            if [[ "$name" == "$entry" && "$entry" == */* ]]; then
                echo "  WARNING: OpenCode plugin entry has no '@' separator and looks like a path/URL — skipping: ${entry}" >&2
                ((idx++))
                continue
            fi
            [[ -z "$name" ]] && { ((idx++)); continue; }
            emit_item "$name" "" ""
            ((idx++))
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_opencode_mcp
# ------------------------------------------------------------------------------
# Catalogs configured OpenCode MCP servers from ~/.config/opencode/opencode.json .mcp
# FMT-03 COMPLIANCE: reads ONLY object key (server name) and .value.type (transport).
# NEVER reads .command, .env, .args, .url, .headers.
# On this machine .mcp is null → section writes "(none found)" via flush_section.
# Transport label is clamped to stdio|http|sse whitelist.
# Emits: name [transport]
# Graceful degradation: absent config or null .mcp field → "(none found)"
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_opencode_mcp() {
    local oc_config="$HOME/.config/opencode/opencode.json"
    local name="" transport=""

    write_section "OpenCode MCP Servers"
    _section_lines=()

    if [[ ! -f "$oc_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        # Check if .mcp is non-null; if null/empty, skip to flush_section
        local mcp_check=""
        mcp_check=$(jq -r '.mcp // empty' "$oc_config" 2>/dev/null)
        if [[ -z "$mcp_check" ]]; then
            flush_section
            return
        fi
        # .mcp is populated: extract name + transport (FMT-03 safe — key + .value.type only)
        while IFS=$'\t' read -r name transport; do
            [[ -z "$name" ]] && continue
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "${transport:-stdio}"
        done < <(jq -r '.mcp | to_entries[] | .key + "\t" + (.value.type // "stdio")' \
                     "$oc_config" 2>/dev/null)
    else
        # plutil fallback: enumerate server names in one call; empty = null/absent .mcp
        local server_names=()
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            server_names+=("$name")
        done < <(plutil -extract "mcp" raw -o - "$oc_config" 2>/dev/null)

        if [[ ${#server_names[@]} -eq 0 ]]; then
            flush_section
            return
        fi

        for name in "${server_names[@]}"; do
            transport=$(plutil -extract "mcp.${name}.type" raw -o - \
                            "$oc_config" 2>/dev/null) || transport="stdio"
            [[ -z "$transport" ]] && transport="stdio"
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "$transport"
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_opencode_agents
# ------------------------------------------------------------------------------
# Catalogs OpenCode agents from ~/.config/opencode/agents/*.md
# Name is extracted from YAML frontmatter name: field (same pattern as Claude agents).
# Fallback: filename without .md extension.
# Null-glob guard prevents Zsh "no match" errors on empty or absent directory.
# No version or ID available — emits bare name only.
# Graceful degradation: absent agents directory → "(none found)"
# NOT called from generate_catalog — wired in Phase 5.
# ------------------------------------------------------------------------------
collect_opencode_agents() {
    local agents_dir="$HOME/.config/opencode/agents"
    local name=""

    write_section "OpenCode Agents"
    _section_lines=()

    if [[ ! -d "$agents_dir" ]]; then
        flush_section
        return
    fi

    setopt local_options null_glob
    for f in "$agents_dir"/*.md; do
        [[ -e "$f" ]] || continue
        name=$(grep '^name:' "$f" | head -1 \
                   | sed 's/^name:[[:space:]]*//' | tr -d '"')
        [[ -z "$name" ]] && name=$(basename "$f" .md)
        emit_item "$name" "" ""
        name=""
    done

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_gemini_extensions
# ------------------------------------------------------------------------------
# Collects installed Gemini CLI extensions (GEM-01).
#
# Source: ~/.gemini/extensions/*/gemini-extension.json
# Fields: name + version (from manifest)
# Output format: name (version)
#
# Each subdirectory under ~/.gemini/extensions/ that contains a
# gemini-extension.json manifest is treated as an installed extension.
# The extension-enablement.json file (also in that directory) is
# informational only — all installed extensions are cataloged, not
# just enabled ones.
# ------------------------------------------------------------------------------
collect_gemini_extensions() {
    local ext_base="$HOME/.gemini/extensions"
    local name="" version=""

    write_section "Gemini CLI Extensions"
    _section_lines=()

    if [[ ! -d "$ext_base" ]]; then
        flush_section
        return
    fi

    setopt local_options null_glob
    for ext_dir in "$ext_base"/*/; do
        [[ -e "$ext_dir" ]] || continue
        local manifest="${ext_dir}gemini-extension.json"
        [[ -f "$manifest" ]] || continue
        name=$(json_get "$manifest" "name")
        version=$(json_get "$manifest" "version")
        [[ -z "$name" ]] && name=$(basename "$ext_dir")
        emit_item "$name" "$version" ""
        name=""
        version=""
    done

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_gemini_mcp
# ------------------------------------------------------------------------------
# Collects configured Gemini CLI MCP servers (GEM-02).
#
# Source: ~/.gemini/config/mcp_config.json
# Fields: server name (key) + transport type (.value.type) ONLY — FMT-03
# Output format: name [transport]
#
# CRITICAL: mcp_config.json may exist but be 0 bytes (empty file).
# A bare -f guard returns true for an empty file, causing jq to error.
# The [[ -s ]] guard (file exists AND has nonzero size) handles both
# absent and empty-file cases gracefully, writing (none found) for both.
#
# FMT-03: ONLY reads .key (server name) and .value.type (transport).
# NEVER reads .value.env, .value.command, .value.args, .value.url,
# or .value.headers — these are secret-bearing fields.
# ------------------------------------------------------------------------------
collect_gemini_mcp() {
    local mcp_config="$HOME/.gemini/config/mcp_config.json"
    local name="" transport=""

    write_section "Gemini CLI MCP Servers"
    _section_lines=()

    if [[ ! -s "$mcp_config" ]]; then
        flush_section
        return
    fi

    if command -v jq &>/dev/null; then
        while IFS=$'\t' read -r name transport; do
            [[ -z "$name" ]] && continue
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "$transport"
        done < <(jq -r '.mcpServers | to_entries[] | .key + "\t" + (.value.type // "stdio")' \
                     "$mcp_config" 2>/dev/null)
    else
        # plutil fallback: enumerate server names, then extract type per server
        local server_names=()
        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            server_names+=("$name")
        done < <(plutil -extract "mcpServers" raw -o - "$mcp_config" 2>/dev/null)

        for name in "${server_names[@]}"; do
            transport=$(plutil -extract "mcpServers.${name}.type" raw -o - \
                            "$mcp_config" 2>/dev/null) || transport="stdio"
            [[ -z "$transport" ]] && transport="stdio"
            case "$transport" in
                stdio|http|sse) : ;;
                *) transport="stdio" ;;
            esac
            emit_item "$name" "" "$transport"
        done
    fi

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_chrome_extensions
# ------------------------------------------------------------------------------
# Catalogs user-installed Google Chrome extensions across all profiles.
# Profiles enumerated: Default + Profile */ dirs under the Chrome base dir.
# Version selection: sort -V | tail -1 (numeric version sort, not lexical).
# Name resolution: chrome_ext_name helper (Phase 1) — resolves __MSG_* via
#   _locales/<default_locale>/messages.json; falls back to the 32-char ID.
# Component exclusion: 10-ID denylist via case statement.
# Output: "Google Chrome Extensions" section via emit_item -> flush_section.
# Graceful degradation: Chrome not installed -> (none found) written.
# NOT called from generate_catalog — Phase 5 wires this.
# ------------------------------------------------------------------------------
collect_chrome_extensions() {
    local chrome_base="$HOME/Library/Application Support/Google/Chrome"
    local profile_dir="" ext_dir="" ext_id="" ver_dir="" manifest="" name="" version=""

    write_section "Google Chrome Extensions"
    _section_lines=()

    if [[ ! -d "$chrome_base" ]]; then
        echo "  NOTE: Google Chrome not installed."
        flush_section
        return
    fi

    setopt local_options null_glob

    for profile_dir in "$chrome_base/Default" "$chrome_base"/Profile\ */; do
        [[ -d "${profile_dir}/Extensions" ]] || continue

        for ext_dir in "${profile_dir}/Extensions"/*/; do
            [[ -e "$ext_dir" ]] || continue

            ext_id=$(basename "$ext_dir")

            # Skip Chrome's in-progress download directory
            [[ "$ext_id" == "Temp" ]] && continue

            # Skip Chrome internal directories (prefixed with underscore, e.g. _metadata)
            [[ "$ext_id" == _* ]] && continue

            # Skip Google component / pre-installed extensions (not user choices)
            case "$ext_id" in
                nmmhkkegccagdldgiimedpiccmgmieda|\
                ghbmnnjooekpmoecnnnilnnbdlolhkhi|\
                aapocclcgogkmnckokdopfmhonfmgoek|\
                blpcfgokakmgnkcojhhkbfbldkacnbeo|\
                felcaaldnbdncclmgdcncolpebgiejap|\
                aohghmighlieiainnegkcijnfilokake|\
                apdfllckaahabafndbhieahigkjlhalf|\
                pjkljhegncpnkpknbcohdijeoejaedia|\
                mhjfbmdgcfjbbpaeojofohoefgiehjai|\
                pkedcjkdefgpdelpbcmbmeomcjbeemfm)
                    continue ;;
            esac

            # Pick highest version dir; Chrome dirs are named <semver>_<N>
            # grep -E '^[0-9]' restricts candidates to version-like entries (start with digit)
            # so non-version files/dirs (e.g. _crx_invalidation_map) can't steal the slot.
            # sort -V handles numeric comparison correctly (e.g. 14.x > 3.x > 2.x)
            ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | grep -E '^[0-9]' | sort -V | tail -1)
            [[ -z "$ver_dir" ]] && continue

            manifest="${ext_dir}${ver_dir}/manifest.json"
            [[ -f "$manifest" ]] || continue

            # chrome_ext_name resolves __MSG_<key>__ via _locales/; falls back to ext_id
            name=$(chrome_ext_name "$manifest")
            version=$(json_get "$manifest" "version")

            emit_item "$name" "$version" "$ext_id"
        done
    done

    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: collect_firefox_extensions
# ------------------------------------------------------------------------------
# Catalogs user-installed Firefox extensions across all profiles.
# Profile discovery: parses profiles.ini Path= entries (relative to Firefox dir).
# Location filter: keeps only location == "app-profile" (user-installed extensions
#   and user themes); excludes app-builtin and app-builtin-addons (system add-ons).
# Primary path: jq with tab-delimited IFS=$'\t' read to handle spaces in names.
# Fallback path: plutil index-loop (addons.N.*) when jq is absent.
# Cross-profile dedup: flush_section (LC_ALL=C sort -f -u) called ONCE after the
#   outer profile loop — accumulates all profiles before deduplication.
# Output: "Firefox Extensions" section via emit_item -> flush_section.
# Graceful degradation: profiles.ini absent (Firefox not installed) -> (none found).
# NOT called from generate_catalog — Phase 5 wires this.
# ------------------------------------------------------------------------------
collect_firefox_extensions() {
    local ff_dir="$HOME/Library/Application Support/Firefox"
    local profiles_ini="${ff_dir}/profiles.ini"
    local rel_path="" ext_json="" name="" version="" id="" idx=0 loc=""

    write_section "Firefox Extensions"
    _section_lines=()

    if [[ ! -f "$profiles_ini" ]]; then
        echo "  NOTE: Firefox not installed."
        flush_section
        return
    fi

    # Iterate profiles from profiles.ini (Path= entries are relative to $ff_dir)
    while IFS= read -r rel_path; do
        [[ -z "$rel_path" ]] && continue
        ext_json="${ff_dir}/${rel_path}/extensions.json"
        [[ -f "$ext_json" ]] || continue

        if command -v jq &>/dev/null; then
            # jq path: array iteration + location filter in one pass
            # Tab-separated to handle spaces in addon names (Pitfall 4)
            while IFS=$'\t' read -r name version id; do
                [[ -z "$id" || "$id" == "null" ]] && continue
                [[ -z "$name" || "$name" == "null" ]] && name="$id"
                emit_item "$name" "$version" "$id"
            done < <(jq -r '.addons[] | select(.location == "app-profile") |
                "\(.defaultLocale.name // .id // "")\t\(.version // "")\t\(.id // "")"' \
                "$ext_json" 2>/dev/null)
        else
            # plutil fallback: index-based iteration; filter location == app-profile
            # plutil -extract "addons.N.location" breaks on out-of-bounds — used as loop sentinel
            idx=0
            while true; do
                loc=$(plutil -extract "addons.${idx}.location" raw -o - "$ext_json" 2>/dev/null) || break
                if [[ "$loc" == "app-profile" ]]; then
                    name=$(plutil -extract "addons.${idx}.defaultLocale.name" raw -o - "$ext_json" 2>/dev/null) || name=""
                    version=$(plutil -extract "addons.${idx}.version" raw -o - "$ext_json" 2>/dev/null) || version=""
                    id=$(plutil -extract "addons.${idx}.id" raw -o - "$ext_json" 2>/dev/null) || id=""
                    [[ -z "$id" ]] && { ((idx++)); continue; }
                    [[ -z "$name" ]] && name="$id"
                    emit_item "$name" "$version" "$id"
                fi
                ((idx++))
            done
        fi

    done < <(grep '^Path=' "$profiles_ini" 2>/dev/null | sed 's/^Path=//' | tr -d '\r')

    # flush_section called ONCE after all profiles — cross-profile dedup via LC_ALL=C sort -f -u
    flush_section
}

# ------------------------------------------------------------------------------
# FUNCTION: generate_catalog
# ------------------------------------------------------------------------------
# Generates the software catalog by collecting information from various sources.
# This is the main cataloging function that queries:
#   - Homebrew (formulae and casks)
#   - Mac App Store (via mas CLI)
#   - Setapp applications
#   - Other applications in /Applications
#
# The output is written to the globally defined OUTPUT_FILE.
# ------------------------------------------------------------------------------
generate_catalog() {
    echo ""
    echo "Generating software list... Please wait."
    echo ""

    # Initialize the output file with the main header
    write_section "Installed Mac Software List"

    # ----------------------------------
    # Section: Homebrew Packages
    # ----------------------------------
    # Lists all packages installed via Homebrew, including both
    # command-line tools (formulae) and GUI applications (casks)
    write_section "Homebrew Packages"
    if command -v brew &>/dev/null; then
        echo "  Collecting Homebrew formulae..."
        brew list --formula >> "$OUTPUT_FILE"
        echo "  Collecting Homebrew casks..."
        brew list --cask >> "$OUTPUT_FILE"
    else
        echo "Homebrew is not installed." >> "$OUTPUT_FILE"
        echo "  WARNING: Homebrew is not installed on this system."
    fi

    # ----------------------------------
    # Section: App Store Applications
    # ----------------------------------
    # Lists applications installed from the Mac App Store
    # Requires the 'mas' CLI tool (brew install mas)
    write_section "App Store Applications"
    if command -v mas &>/dev/null; then
        echo "  Collecting App Store applications..."
        mas list 2>/dev/null | awk '{print $2, $3}' >> "$OUTPUT_FILE"
        if [[ $? -ne 0 ]]; then
            echo "Could not retrieve App Store list." >> "$OUTPUT_FILE"
        fi
    else
        echo "mas (Mac App Store CLI) is not installed." >> "$OUTPUT_FILE"
        echo "Install it with Homebrew: brew install mas" >> "$OUTPUT_FILE"
        echo "  WARNING: mas CLI is not installed. Install with: brew install mas"
    fi

    # ----------------------------------
    # Section: Setapp Applications
    # ----------------------------------
    # Lists applications installed via the Setapp subscription service
    # These are typically located in /Applications/Setapp/
    write_section "Setapp Applications"
    if [[ -d "/Applications/Setapp" ]]; then
        echo "  Collecting Setapp applications..."
        find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} \; | sort >> "$OUTPUT_FILE"
    else
        echo "Setapp is not installed or detected." >> "$OUTPUT_FILE"
        echo "  NOTE: Setapp is not installed on this system."
    fi

    # ----------------------------------
    # Section: Web-installed Applications
    # ----------------------------------
    # Lists applications installed directly from the web (DMG, PKG, etc.)
    # Excludes Setapp apps and system apps to avoid duplicates
    write_section "Web-installed Applications"
    echo "  Collecting other applications..."
    find "/Applications" -maxdepth 1 -type d -not -path "/Applications/Setapp*" -not -path "/Applications/*App Store*" \
        -exec basename {} \; | sort >> "$OUTPUT_FILE"

    # ----------------------------------
    # AI CLI Extensions & Plugins
    # ----------------------------------
    echo "  Collecting AI CLI extensions..."
    collect_claude_plugins
    collect_claude_mcp
    collect_claude_skills_agents
    collect_codex_mcp
    collect_opencode_plugins
    collect_opencode_mcp
    collect_opencode_agents
    collect_gemini_extensions
    collect_gemini_mcp

    # ----------------------------------
    # Editor Extensions
    # ----------------------------------
    echo "  Collecting editor extensions..."
    collect_vscode_extensions
    collect_cursor_extensions

    # ----------------------------------
    # Browser Extensions
    # ----------------------------------
    echo "  Collecting browser extensions..."
    collect_chrome_extensions
    collect_firefox_extensions
}

# ------------------------------------------------------------------------------
# FUNCTION: git_pull
# ------------------------------------------------------------------------------
# Pulls the latest changes from the remote repository before making local changes.
# This ensures the repository is up-to-date when running the script from different
# machines (e.g., personal and office Macbooks).
#
# This function:
#   1. Checks if the script directory is a git repository
#   2. Pulls the latest changes from the remote
#   3. Warns but continues if pull fails (e.g., network issues)
# ------------------------------------------------------------------------------
git_pull() {
    echo ""
    echo "------------------------------------------------------------------------------"
    echo "Git: Pulling latest changes from remote..."
    echo "------------------------------------------------------------------------------"

    # Change to the script directory for git operations
    cd "$SCRIPT_DIR" || {
        echo "  WARNING: Could not change to script directory. Skipping git pull."
        return
    }

    # Check if this is a git repository
    if ! git rev-parse --git-dir &>/dev/null; then
        echo "  WARNING: Not a git repository. Skipping git pull."
        return
    fi

    # Pull latest changes
    if git pull 2>&1; then
        echo "  Successfully pulled latest changes."
    else
        echo ""
        echo "  WARNING: Failed to pull from remote repository."
        echo "  Continuing with local state. You may need to resolve conflicts later."
        echo ""
    fi
}

# ------------------------------------------------------------------------------
# FUNCTION: git_commit_and_push
# ------------------------------------------------------------------------------
# Automatically adds, commits, and pushes the new catalog file to git.
# Also commits any archived files that were moved during this run.
#
# This function:
#   1. Checks if the script directory is a git repository
#   2. Adds the new catalog file and any archived files to staging
#   3. Creates a commit with a detailed message
#   4. Pushes to the remote repository
#   5. Warns but continues if push fails (e.g., network issues)
#
# The commit message includes:
#   - The target location (personal/office)
#   - The hostname of the machine
#   - The timestamp of the catalog
# ------------------------------------------------------------------------------
git_commit_and_push() {
    echo ""
    echo "------------------------------------------------------------------------------"
    echo "Git: Committing and pushing changes..."
    echo "------------------------------------------------------------------------------"

    # Change to the script directory for git operations
    cd "$SCRIPT_DIR" || {
        echo "  WARNING: Could not change to script directory. Skipping git operations."
        return
    }

    # Check if this is a git repository
    if ! git rev-parse --git-dir &>/dev/null; then
        echo "  WARNING: Not a git repository. Skipping git operations."
        return
    fi

    # Stage all working-tree changes in the targeted location:
    # - new catalog (A), moved-to-archive files (D from main + A in archive/), pruned files (D)
    echo "  Staging all changes in ${TARGET_LOCATION}/..."
    # Use '--' so a user-chosen folder name beginning with '-' is treated as a
    # pathspec, not a git option (the validators permit a leading dash).
    git add -A -- "${TARGET_LOCATION}/"

    # Stage map file if it changed (new mapping or updated label)
    git add -- machine-labels.tsv 2>/dev/null || true

    # Check if there are changes to commit
    if git diff --cached --quiet; then
        echo "  No changes to commit."
        return
    fi

    # Create commit message with detailed information
    # Format: "Added [location] catalog for [hostname] at YYYYMMDDHHMMSS"
    local commit_message="Added [${CURRENT_MACHINE}] catalog at ${CURRENT_DATE}"

    echo "  Creating commit..."
    if git commit -m "$commit_message" &>/dev/null; then
        echo "  Committed: $commit_message"
    else
        echo "  WARNING: Failed to create commit."
        return
    fi

    # Push to remote
    echo "  Pushing to remote..."
    if git push 2>&1; then
        echo "  Successfully pushed to remote."
    else
        echo ""
        echo "  WARNING: Failed to push to remote repository."
        echo "  The commit has been saved locally. You can push manually later with:"
        echo "    cd $SCRIPT_DIR && git push"
        echo ""
    fi
}

[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0

# ==============================================================================
# MAIN SCRIPT EXECUTION
# ==============================================================================

# Display the usage banner
display_usage

# Parse command-line arguments (sets TARGET_LOCATION and AUTO_COMMIT)
parse_arguments "$@"

# --rename mode: pull latest, rename files + map, commit, then exit.
# Skips location/retention prompts, catalog generation, and prune.
if [[ "$RENAME_MODE" == "true" ]]; then
    git_pull
    rename_machine
    exit 0
fi

# Select the computer folder for this run (always-shown menu, or resolved
# non-interactively from --computer/--personal/--office/--machine). The folder
# name IS the machine identity. A Quit inside select_computer does `exit 0`
# here, BEFORE any retention sweep, catalog generation, prune, or git commit —
# so quitting never writes a catalog or makes a commit.
select_computer

# Resolve archive retention period (flag or interactive prompt)
resolve_archive_retention

# Pull latest changes from remote to ensure we're up-to-date
# (important when running from multiple machines)
git_pull

# Generate the output filename with current timestamp and computer folder name
# Format: mac-software-list-[computer-folder]-YYYYMMDDHHMMSS.txt
CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
CURRENT_MACHINE="$TARGET_LOCATION"
OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"

# Set the full output path within the target directory
OUTPUT_FILE="${SCRIPT_DIR}/${TARGET_LOCATION}/${OUTPUT_FILENAME}"

# Ensure the target directory exists
mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"

# Generate the software catalog
generate_catalog

# Display completion message
echo ""
echo "=============================================================================="
echo "CATALOG COMPLETE!"
echo "=============================================================================="
echo ""
echo "Software catalog has been saved to:"
echo "  ${OUTPUT_FILE}"

# Retention sweep: keep newest per host in main/; move others to archive/
retain_newest_per_host "$TARGET_LOCATION"

# N-day prune: hard-delete old archive catalogs (period set by --archive-days or prompt)
prune_old_archives "$TARGET_LOCATION"

# Automatically commit and push if enabled
if [[ "$AUTO_COMMIT" == "true" ]]; then
    git_commit_and_push
else
    echo ""
    echo "Git auto-commit is disabled (--no-commit flag was used)."
    echo "To commit manually, run:"
    echo "  cd $SCRIPT_DIR && git add -A -- \"${TARGET_LOCATION}/\" && git add -- machine-labels.tsv 2>/dev/null; git commit -m 'Added catalog' && git push"
fi

echo ""
echo "=============================================================================="
echo "ALL DONE!"
echo "=============================================================================="
echo ""
