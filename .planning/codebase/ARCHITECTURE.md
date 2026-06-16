<!-- refreshed: 2026-06-12 -->
# Architecture

**Analysis Date:** 2026-06-12

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│                  `update-list.sh`                            │
│         (invoked by user or scheduled task)                  │
└───┬──────────────┬──────────────────┬───────────────────────┘
    │              │                  │
    ▼              ▼                  ▼
┌────────┐  ┌───────────┐  ┌─────────────────────────────────┐
│ Arg    │  │ Git Pull  │  │ Archive Old Catalogs             │
│ Parse  │  │ (sync)    │  │ (files older than 60 days →      │
│        │  │           │  │  `[location]/archive/`)          │
└────────┘  └───────────┘  └─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│               Data Collection (generate_catalog)             │
├──────────────┬──────────────────┬──────────┬────────────────┤
│  brew list   │   mas list       │ /Apps/   │ /Apps/Setapp/  │
│  --formula   │  (App Store)     │ Setapp   │                │
│  --cask      │                  │ excluded │                │
└──────┬───────┴──────────────────┴──────────┴────────────────┘
       │  (appended via >> to OUTPUT_FILE)
       ▼
┌─────────────────────────────────────────────────────────────┐
│               Output File                                    │
│  `[personal|office]/mac-software-list-[hostname]-TS.txt`    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Git Commit & Push                              │
│  Stages: new catalog + archive/ changes                      │
│  Commit msg: "Added [location] catalog for [host] at TS"    │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Location in `update-list.sh` |
|-----------|----------------|-------------------------------|
| `display_usage` | Prints banner and usage help | Line 56 |
| `parse_arguments` | Parses `--personal`, `--office`, `--no-commit` flags | Line 98 |
| `get_target_location` | Resolves target dir (arg or interactive prompt) | Line 136 |
| `archive_old_catalogs` | Moves catalog files older than 60 days to `archive/` | Line 187 |
| `write_section` | Writes formatted section headers to the output file | Line 254 |
| `generate_catalog` | Collects software data from all sources and appends to file | Line 271 |
| `git_pull` | Pulls latest from remote before local changes | Line 350 |
| `git_commit_and_push` | Stages, commits, and pushes new catalog + archived files | Line 397 |
| Main block | Orchestrates function calls in sequence | Line 454 |

## Pattern Overview

**Overall:** Linear shell-script pipeline

**Key Characteristics:**
- Single-file, single-process — no background jobs or subshells for data collection
- All state held in global shell variables (`TARGET_LOCATION`, `OUTPUT_FILE`, `OUTPUT_FILENAME`, `CURRENT_DATE`, `CURRENT_MACHINE`, `AUTO_COMMIT`)
- Functions operate by side effects (appending to `OUTPUT_FILE`, moving files, calling `git`) rather than returning values
- Graceful degradation: each optional data source (Homebrew, `mas`, Setapp) checks for availability and writes a fallback message rather than aborting
- Git operations warn-and-continue on failure; the catalog file is always produced regardless of git success

## Layers

**Configuration / Init Layer:**
- Purpose: Resolve runtime parameters and print usage
- Functions: `display_usage`, `parse_arguments`, `get_target_location`
- Depends on: command-line args (`$@`)
- Used by: main block

**Pre-run Maintenance Layer:**
- Purpose: Sync repo state and clean stale files before generating a new catalog
- Functions: `git_pull`, `archive_old_catalogs`
- Depends on: `SCRIPT_DIR`, `TARGET_LOCATION`, `ARCHIVE_AGE_DAYS`
- Used by: main block

**Data Collection Layer:**
- Purpose: Query installed-software sources and write catalog sections to disk
- Functions: `generate_catalog`, `write_section`
- Depends on: system tools (`brew`, `mas`, `find`), global `OUTPUT_FILE`
- Used by: main block

**Persistence Layer:**
- Purpose: Commit and push the generated artifact to git remote
- Functions: `git_commit_and_push`
- Depends on: `TARGET_LOCATION`, `OUTPUT_FILENAME`, `CURRENT_MACHINE`, `CURRENT_DATE`
- Used by: main block (conditionally — skipped when `AUTO_COMMIT=false`)

## Data Flow

### Primary Execution Path

1. **Argument parsing** — `parse_arguments "$@"` sets `TARGET_LOCATION` and `AUTO_COMMIT` (line 462)
2. **Location resolution** — `get_target_location` confirms or interactively prompts for `personal` or `office` (line 465)
3. **Git sync** — `git_pull` fetches remote changes so multi-machine runs stay consistent (line 469)
4. **Archiving** — `archive_old_catalogs "$TARGET_LOCATION"` moves files with embedded timestamp < cutoff date into `[location]/archive/` (line 472)
5. **Filename generation** — `OUTPUT_FILENAME` is set to `mac-software-list-[$(hostname)]-$(date "+%Y%m%d%H%M%S").txt` (line 476–478)
6. **Catalog generation** — `generate_catalog` runs four collection sub-steps in sequence, each appending to `OUTPUT_FILE` (line 487)
   - `brew list --formula` and `brew list --cask`
   - `mas list | awk '{print $2, $3}'`
   - `find /Applications/Setapp -maxdepth 1 -type d`
   - `find /Applications -maxdepth 1 -type d` (excluding Setapp and App Store paths)
7. **Git commit** — `git_commit_and_push` stages `[location]/output.txt` and `[location]/archive/`, commits, and pushes (line 499)

### Archive Flow (within step 4)

1. Compute cutoff: `date -v-60d "+%Y%m%d"` (macOS `date` syntax)
2. Glob all `mac-software-list-*.txt` files in the target directory (not in `archive/`)
3. Extract the 8-digit date prefix from the 14-digit timestamp in the filename using `grep -oE '[0-9]{14}\.txt$' | cut -c1-8`
4. Integer-compare the extracted date string with the cutoff; move if less (older)

## Key Abstractions

**Catalog File:**
- Purpose: Timestamped, human-readable plain-text snapshot of installed software on one machine
- Naming: `mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt` where brackets are literal characters surrounding the hostname
- Sections: `Installed Mac Software List`, `Homebrew Packages`, `App Store Applications`, `Setapp Applications`, `Web-installed Applications`
- Location: `personal/` or `office/` at repo root; moved to `[location]/archive/` after 60 days

**Target Location:**
- Two valid values: `personal` and `office`
- Maps directly to directories at repo root: `personal/`, `office/`
- Determines both where the output file is written and which archive sub-directory is managed

## Entry Points

**Primary:**
- Location: `update-list.sh` (repo root)
- Invocation: `./update-list.sh [--personal | --office] [--no-commit]`
- Shell: `/bin/zsh` (shebang line 1)
- Triggers: Manual invocation or any cron/launchd scheduled task

## Architectural Constraints

- **macOS-only:** Uses `date -v-Nd` syntax (macOS BSD date), `hostname`, `/Applications/`, and `mas` — not portable to Linux
- **Zsh-only:** Shebang is `#!/bin/zsh`; uses zsh parameter expansion `${0:A:h}` and `${file:t}` modifiers
- **Global state:** All runtime variables (`TARGET_LOCATION`, `OUTPUT_FILE`, `OUTPUT_FILENAME`, `AUTO_COMMIT`, `CURRENT_DATE`, `CURRENT_MACHINE`) are unscoped globals set in the main block and referenced by functions
- **Single output file per run:** Each script invocation produces exactly one `.txt` file
- **Git assumed present:** `git_pull` and `git_commit_and_push` gracefully skip with warnings if not a git repo, but the workflow is designed around git being available
- **No locking:** Running the script from two machines simultaneously against the same remote can produce git conflicts; `git pull` at the start mitigates but does not eliminate this

## Anti-Patterns

### Globals-as-parameters

**What happens:** Functions like `generate_catalog` and `git_commit_and_push` read `OUTPUT_FILE`, `TARGET_LOCATION`, `OUTPUT_FILENAME`, etc. as global variables rather than receiving them as arguments.
**Why it's wrong:** Makes functions non-reusable and hard to test in isolation; any caller must set the globals before calling.
**Do this instead:** Pass required values as explicit function arguments: `generate_catalog "$OUTPUT_FILE"`.

## Error Handling

**Strategy:** Warn-and-continue for optional steps; hard-exit on invalid user input

**Patterns:**
- Invalid CLI flag → `echo "ERROR: ..."` + `exit 1` (`parse_arguments`, line 115)
- Invalid interactive choice → `echo "ERROR: ..."` + `exit 1` (`get_target_location`, line 163)
- Missing optional tool (Homebrew, `mas`, Setapp) → fallback message written to catalog file; script continues
- Git pull failure → warning printed; script continues with local state
- Git push failure → warning printed; local commit preserved; script exits successfully
- `mkdir -p` is used for directory creation — safe to call when directory already exists

## Cross-Cutting Concerns

**Logging:** All status output goes to stdout via `echo`; no log files produced
**Validation:** Input validated only at arg-parse and location-prompt boundaries; no validation of tool output
**Authentication:** None — relies on pre-configured git credentials and macOS tool access

---

*Architecture analysis: 2026-06-12*
