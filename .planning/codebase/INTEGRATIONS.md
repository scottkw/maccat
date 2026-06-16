# External Integrations

**Analysis Date:** 2026-06-12

## Package Managers & Software Sources

**Homebrew:**
- Purpose: Enumerate installed CLI formulae and GUI casks
- Command invoked: `brew list --formula`, `brew list --cask`
- Availability check: `command -v brew`
- Failure mode: Writes "Homebrew is not installed." to catalog and prints warning; continues
- Install path (referenced in README): `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh`

**Mac App Store (via `mas` CLI):**
- Purpose: Enumerate apps installed from the Mac App Store
- Command invoked: `mas list 2>/dev/null | awk '{print $2, $3}'`
- Availability check: `command -v mas`
- Failure mode: Writes advisory message and install instructions to catalog; continues
- Prerequisite: `brew install mas`

**Setapp:**
- Purpose: Enumerate apps installed via the Setapp subscription service
- Detection method: Checks for existence of `/Applications/Setapp` directory
- Command invoked: `find "/Applications/Setapp" -maxdepth 1 -type d -exec basename {} \; | sort`
- Failure mode: Writes "Setapp is not installed or detected." to catalog; continues

## Filesystem Integrations

**macOS `/Applications` directory:**
- Purpose: Enumerate web-installed (DMG/PKG) apps not covered by Homebrew, App Store, or Setapp
- Command invoked: `find "/Applications" -maxdepth 1 -type d -not -path "/Applications/Setapp*" -not -path "/Applications/*App Store*" -exec basename {} \; | sort`
- Exclusions: Setapp subdirectory, App Store subdirectory

## Version Control Integration

**Git (remote repository):**
- Purpose: Sync catalogs across multiple machines (personal and office Macs)
- Operations performed:
  - `git pull` — pulls latest changes from remote before generating catalog
  - `git add {TARGET_LOCATION}/{OUTPUT_FILENAME}` — stages new catalog file
  - `git add {TARGET_LOCATION}/archive/` — stages any newly archived files
  - `git diff --cached --quiet` — checks whether there is anything to commit
  - `git commit -m "Added {location} catalog for [{hostname}] at {timestamp}"` — commits catalog
  - `git push` — pushes to remote
- Availability check: `git rev-parse --git-dir`
- Failure mode: Each git operation (pull, commit, push) warns and continues on failure; catalog file is always written regardless of git outcome
- Disabled with: `--no-commit` flag

**Commit message format:**
```
Added {personal|office} catalog for [{hostname}] at {YYYYMMDDHHMMSS}
```
Example: `Added personal catalog for [computer-one.local] at 20260612130331`

## Data Storage

**Databases:**
- None — all data stored as plain-text `.txt` files in the repository

**File Storage:**
- Local filesystem + git repository
- Active catalogs: `personal/*.txt`, `office/*.txt`
- Archived catalogs: `personal/archive/*.txt`, `office/archive/*.txt`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None — relies on whatever git credentials are configured in the local environment (SSH key, credential helper, etc.)
- The script does not manage git authentication itself

## Monitoring & Observability

**Error Tracking:**
- None — errors are written to stdout with "WARNING:" or "ERROR:" prefixes

**Logs:**
- All output goes to stdout/stderr
- No persistent log files

## CI/CD & Deployment

**Hosting:**
- Git remote (GitHub or similar) — stores catalog history; remote URL not hardcoded in script

**CI Pipeline:**
- None — script is run manually or on a schedule by the user directly on each Mac

## Environment Configuration

**Required env vars:**
- None

**Secrets location:**
- Not applicable — no secrets used

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-06-12*
