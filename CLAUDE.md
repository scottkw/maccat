<!-- GSD:project-start source:PROJECT.md -->
## Project

**Mac Software List Generator**

A single Zsh script (`update-list.sh`) that catalogs everything installed on a macOS
machine into a timestamped, per-machine plain-text snapshot, auto-archives old catalogs,
and auto-commits/pushes to git. This milestone extends that coverage from "installed
applications" to also include the **extensions, plugins, MCP servers, and skills/agents**
of the user's AI coding CLIs and editors, plus **browser extensions**. It's a personal
tool for keeping a restorable, diffable history of a machine's full software + tooling state.

**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and*
tooling extensions — accurate enough to rebuild the environment from, degrading gracefully
when any source isn't installed.

### Constraints

- **Tech stack**: Pure Zsh shell script, no new runtime/deps — keep the tool single-file and
  dependency-free beyond optional CLIs it probes
- **Compatibility**: macOS-only (Zsh, BSD `date`, macOS filesystem layout)
- **Output format**: Plain-text sections appended to the existing per-machine catalog file —
  must not break existing sections or the archive/git flow
- **Detail level**: name + version + ID per extension/plugin where each is obtainable
- **Behavior**: graceful degradation is mandatory — a missing tool or browser must warn-and-continue
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Zsh shell script - `update-list.sh` (sole implementation file, ~513 lines)
- None
## Runtime
- macOS only — relies on macOS-specific `date -v` flag, `/Applications` filesystem layout, and default Zsh shell
- Zsh (shebang: `#!/bin/zsh`) — default shell on macOS 10.15+
- None — no package dependencies managed by this project itself
## Frameworks
- None — pure Zsh shell script, no framework
- None detected
- None — script is executed directly via `./update-list.sh`
## Key Dependencies
- `git` — version control operations (pull, add, commit, push); built into macOS or installed via Xcode Command Line Tools
- `date` — macOS BSD `date` with `-v` flag for date arithmetic (macOS-specific, not GNU date compatible)
- `find` — filesystem traversal for `/Applications` and archive logic; standard POSIX tool
- `hostname` — retrieves machine hostname for embedding in output filenames; standard POSIX tool
- `mkdir` — creates output and archive directories; standard POSIX tool
- `mv` — moves files to archive; standard POSIX tool
- `grep` — regex timestamp extraction from filenames; standard POSIX tool
- `awk` — reformats `mas list` output; standard POSIX tool
- `command` — checks if optional tools are installed (`command -v brew`, `command -v mas`)
- `brew` (Homebrew) — lists installed formulae (`brew list --formula`) and casks (`brew list --cask`); skipped with warning if not present
- `mas` (Mac App Store CLI) — lists App Store apps (`mas list`); skipped with warning if not present; installed via `brew install mas`
## Configuration
- No environment variables used
- No `.env` files
- Single compile-time constant in script: `ARCHIVE_AGE_DAYS=60` (line 45)
- `--personal` — save catalog to `personal/` directory
- `--office` — save catalog to `office/` directory
- `--no-commit` — skip `git commit` and `git push`
- No build step — script is run directly
- Must be executable: `chmod +x update-list.sh`
## Output Format
- Plain text (`.txt`)
- Naming convention: `mac-software-list-[{hostname}]-{YYYYMMDDHHMMSS}.txt`
- Sections delimited by `------------------------------------` separators
- Written to `personal/` or `office/` at repo root
- Files older than 60 days automatically moved to `personal/archive/` or `office/archive/`
## Platform Requirements
- macOS (tested on macOS with Zsh as default shell)
- Git configured with a remote (GitHub or other) for auto-push to work
- Xcode Command Line Tools or full Xcode (provides `git`)
- macOS only — not compatible with Linux or Windows due to BSD `date -v` flag usage and `/Applications` directory structure
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Shell Environment
## Naming Patterns
- `snake_case` with descriptive verb-noun pairs: `display_usage`, `parse_arguments`,
- `SCRIPT_DIR`, `ARCHIVE_AGE_DAYS`, `AUTO_COMMIT`, `TARGET_LOCATION`, `CURRENT_DATE`,
- Declared with `local` keyword inside functions: `target_dir`, `full_path`,
- Pattern: `mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt`
- Hostname is wrapped in square brackets in the filename
## Variable Quoting
- Variables are consistently double-quoted when there is any chance of spaces or
- Paths constructed from variables are always quoted: `"${full_path}/archive"`,
- Parameter expansion uses braces for concatenation contexts:
- Bare `$var` (no quotes) is used only for arithmetic comparisons:
## Control Flow Patterns
## Error Handling
- Invalid CLI argument in `parse_arguments`
- Invalid interactive choice in `get_target_location`
- git pull/push/commit failures
- `cd` failure in git functions
- Unparseable filename timestamp in `archive_old_catalogs`
## Output Conventions
- `echo "  Collecting Homebrew formulae..."`
- `echo "  WARNING: ..."`
- `echo "  NOTE: ..."`
## Output Redirection
- Catalog data → `>> "$OUTPUT_FILE"` (append to the output file)
- Progress/status → stdout (implicit, no redirection)
- Suppressed stderr → `2>/dev/null` for noisy commands (`git rev-parse`, `mas list`,
- Combined stdout+stderr → `2>&1` only for commands where output is shown to the user
## Function Documentation Style
#
#
## String Extraction
## Arithmetic
## Path Handling
## Style Patterns to Follow
- Use `local` for all function-scoped variables — do not use globals inside functions
- Use `[[ ]]` (double brackets) for all conditionals, not `[ ]`.
- Prefer `command -v` over `which` for tool detection.
- Always check that a directory exists before writing into it.
- Include a null-glob guard (`[[ -e "$file" ]] || continue`) in filename glob loops.
- Use `return` to exit a function on non-fatal errors; use `exit 1` only for fatal
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
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
- Single-file, single-process — no background jobs or subshells for data collection
- All state held in global shell variables (`TARGET_LOCATION`, `OUTPUT_FILE`, `OUTPUT_FILENAME`, `CURRENT_DATE`, `CURRENT_MACHINE`, `AUTO_COMMIT`)
- Functions operate by side effects (appending to `OUTPUT_FILE`, moving files, calling `git`) rather than returning values
- Graceful degradation: each optional data source (Homebrew, `mas`, Setapp) checks for availability and writes a fallback message rather than aborting
- Git operations warn-and-continue on failure; the catalog file is always produced regardless of git success
## Layers
- Purpose: Resolve runtime parameters and print usage
- Functions: `display_usage`, `parse_arguments`, `get_target_location`
- Depends on: command-line args (`$@`)
- Used by: main block
- Purpose: Sync repo state and clean stale files before generating a new catalog
- Functions: `git_pull`, `archive_old_catalogs`
- Depends on: `SCRIPT_DIR`, `TARGET_LOCATION`, `ARCHIVE_AGE_DAYS`
- Used by: main block
- Purpose: Query installed-software sources and write catalog sections to disk
- Functions: `generate_catalog`, `write_section`
- Depends on: system tools (`brew`, `mas`, `find`), global `OUTPUT_FILE`
- Used by: main block
- Purpose: Commit and push the generated artifact to git remote
- Functions: `git_commit_and_push`
- Depends on: `TARGET_LOCATION`, `OUTPUT_FILENAME`, `CURRENT_MACHINE`, `CURRENT_DATE`
- Used by: main block (conditionally — skipped when `AUTO_COMMIT=false`)
## Data Flow
### Primary Execution Path
### Archive Flow (within step 4)
## Key Abstractions
- Purpose: Timestamped, human-readable plain-text snapshot of installed software on one machine
- Naming: `mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt` where brackets are literal characters surrounding the hostname
- Sections: `Installed Mac Software List`, `Homebrew Packages`, `App Store Applications`, `Setapp Applications`, `Web-installed Applications`
- Location: `personal/` or `office/` at repo root; moved to `[location]/archive/` after 60 days
- Two valid values: `personal` and `office`
- Maps directly to directories at repo root: `personal/`, `office/`
- Determines both where the output file is written and which archive sub-directory is managed
## Entry Points
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
## Error Handling
- Invalid CLI flag → `echo "ERROR: ..."` + `exit 1` (`parse_arguments`, line 115)
- Invalid interactive choice → `echo "ERROR: ..."` + `exit 1` (`get_target_location`, line 163)
- Missing optional tool (Homebrew, `mas`, Setapp) → fallback message written to catalog file; script continues
- Git pull failure → warning printed; script continues with local state
- Git push failure → warning printed; local commit preserved; script exits successfully
- `mkdir -p` is used for directory creation — safe to call when directory already exists
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
