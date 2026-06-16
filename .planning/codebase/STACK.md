# Technology Stack

**Analysis Date:** 2026-06-12

## Languages

**Primary:**
- Zsh shell script - `update-list.sh` (sole implementation file, ~513 lines)

**Secondary:**
- None

## Runtime

**Environment:**
- macOS only — relies on macOS-specific `date -v` flag, `/Applications` filesystem layout, and default Zsh shell

**Shell:**
- Zsh (shebang: `#!/bin/zsh`) — default shell on macOS 10.15+

**Package Manager:**
- None — no package dependencies managed by this project itself

## Frameworks

**Core:**
- None — pure Zsh shell script, no framework

**Testing:**
- None detected

**Build/Dev:**
- None — script is executed directly via `./update-list.sh`

## Key Dependencies

**Required system tools:**
- `git` — version control operations (pull, add, commit, push); built into macOS or installed via Xcode Command Line Tools
- `date` — macOS BSD `date` with `-v` flag for date arithmetic (macOS-specific, not GNU date compatible)
- `find` — filesystem traversal for `/Applications` and archive logic; standard POSIX tool
- `hostname` — retrieves machine hostname for embedding in output filenames; standard POSIX tool
- `mkdir` — creates output and archive directories; standard POSIX tool
- `mv` — moves files to archive; standard POSIX tool
- `grep` — regex timestamp extraction from filenames; standard POSIX tool
- `awk` — reformats `mas list` output; standard POSIX tool
- `command` — checks if optional tools are installed (`command -v brew`, `command -v mas`)

**Optional tools (graceful degradation when absent):**
- `brew` (Homebrew) — lists installed formulae (`brew list --formula`) and casks (`brew list --cask`); skipped with warning if not present
- `mas` (Mac App Store CLI) — lists App Store apps (`mas list`); skipped with warning if not present; installed via `brew install mas`

## Configuration

**Environment:**
- No environment variables used
- No `.env` files
- Single compile-time constant in script: `ARCHIVE_AGE_DAYS=60` (line 45)

**Runtime flags:**
- `--personal` — save catalog to `personal/` directory
- `--office` — save catalog to `office/` directory
- `--no-commit` — skip `git commit` and `git push`

**Build:**
- No build step — script is run directly
- Must be executable: `chmod +x update-list.sh`

## Output Format

**Catalog files:**
- Plain text (`.txt`)
- Naming convention: `mac-software-list-[{hostname}]-{YYYYMMDDHHMMSS}.txt`
- Sections delimited by `------------------------------------` separators
- Written to `personal/` or `office/` at repo root
- Files older than 60 days automatically moved to `personal/archive/` or `office/archive/`

## Platform Requirements

**Development:**
- macOS (tested on macOS with Zsh as default shell)
- Git configured with a remote (GitHub or other) for auto-push to work
- Xcode Command Line Tools or full Xcode (provides `git`)

**Production:**
- macOS only — not compatible with Linux or Windows due to BSD `date -v` flag usage and `/Applications` directory structure

---

*Stack analysis: 2026-06-12*
