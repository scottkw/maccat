# Codebase Concerns

**Analysis Date:** 2026-06-12

## Tech Debt

**Archiving creates unstaged git deletions on every run:**
- Issue: `archive_old_catalogs()` uses `mv` to move files out of `personal/` and `office/` into their `archive/` subdirectories. `git_commit_and_push()` then runs `git add "${TARGET_LOCATION}/archive/"` which stages the new files in `archive/`, but never stages the corresponding deletions from the parent directory. The `mv` leaves those paths as unstaged deletions in the git index.
- Files: `update-list.sh` lines 231 (mv), 417–421 (git add)
- Impact: Deletions accumulate silently in the working tree. Currently 20 such unstaged deletions exist (`git status` shows `D personal/mac-software-list-[...].txt` for all recently archived files). The repo's working tree and index diverge over time.
- Fix approach: Replace the two `git add` calls in `git_commit_and_push()` with `git add -u "${TARGET_LOCATION}/"` followed by `git add "${TARGET_LOCATION}/archive/"`, or use `git rm` on moved files and `git add` for the new archive location.

**No `set -euo pipefail` safety flags:**
- Issue: The script is `#!/bin/zsh` with no `set -e`, `set -u`, or `set -o pipefail`. Silent failures in command substitutions (e.g., `$(hostname)`, `$(date ...)`) will produce empty strings that propagate through filename construction without any error.
- Files: `update-list.sh` line 1
- Impact: A failed `hostname` call produces `OUTPUT_FILENAME="mac-software-list-[]-YYYYMMDDHHMMSS.txt"` and proceeds to commit. A failed `date` call similarly silently corrupts the filename.
- Fix approach: Add `set -euo pipefail` after the shebang, or at minimum add explicit guards around `$(hostname)` and `$(date ...)`.

**No `.gitignore` file:**
- Issue: The repo has no `.gitignore`. Untracked noise files are present: `.DS_Store`, `.playwright-mcp/` (a browser automation log directory), and `.planning/` (this planning directory). The script's manual commit hint at line 505 uses `git add .`, which would accidentally commit all of these.
- Files: `update-list.sh` line 505; repo root
- Impact: `.DS_Store` and `.playwright-mcp/` could be committed accidentally if the manual-commit path is used. `.planning/` contains internal planning documents that should not be in the catalog history.
- Fix approach: Add a `.gitignore` with at minimum: `.DS_Store`, `.planning/`, `.playwright-mcp/`, `.claude/`.

**Unbounded repository growth with no pruning strategy:**
- Issue: The archive directories are never pruned from git history. There are currently 124 committed `.txt` catalog files (80 in `personal/`, 44 in `office/`), plus the full history of every version of each file. The repo has 128 commits and is already at 473 loose objects / 1.86 MiB. At the current run rate (roughly weekly per machine, multiple machines), this grows without bound.
- Files: `personal/archive/`, `office/archive/`
- Impact: `git clone` and `git pull` become progressively slower. The catalogs themselves (~500 lines each) are largely redundant across runs.
- Fix approach: Periodically run `git gc` and `git repack`. Consider using a `.gitattributes` export-ignore on archive/ or implementing a shallow-clone strategy. Long-term: consider storing only the latest catalog per machine in git, with historical files outside the repo.

## Known Bugs

**Archiving runs before `OUTPUT_FILENAME` is set, then the unstaged deletions are never cleaned up:**
- Symptoms: Every time a file is archived, the deletion is left unstaged. After enough runs, `git status` accumulates many `D` entries that are never committed.
- Files: `update-list.sh` lines 472 (archive_old_catalogs call), 476–478 (OUTPUT_FILENAME set after)
- Trigger: Any run where a catalog older than 60 days exists in the active directory.
- Workaround: Manually run `git add -u && git commit -m "stage archived deletions"` in the repo root.

**`git pull` merge conflicts are silently swallowed:**
- Symptoms: If `git pull` exits 0 but introduces conflict markers (e.g., during an auto-merge that fails on text), the script continues and calls `git commit`, which either fails silently (caught at line 434) or produces a commit containing conflict markers in a catalog file.
- Files: `update-list.sh` lines 369–376 (git_pull), 434 (git commit suppresses stderr)
- Trigger: Two machines run the script nearly simultaneously and both push before the second one pulls.
- Workaround: Run `git status` before running the script to confirm a clean state.

**`find /Applications` lists non-`.app` directories:**
- Symptoms: The "Web-installed Applications" section includes any top-level directory in `/Applications`, not just `.app` bundles. On systems with directories like `Utilities` or `Adobe` (non-bundle subdirectories), these appear as if they are applications.
- Files: `update-list.sh` line 334
- Trigger: Always, on systems with non-`.app` subdirectories in `/Applications`.
- Workaround: None currently.

## Security Considerations

**System inventory committed to a remote git server:**
- Risk: Every catalog file contains the complete list of installed software for the machine. This is committed and pushed to `a private catalog remote`. If that remote is ever exposed publicly, or credentials are compromised, the full software inventory of both personal and office machines is exposed — including security tools, VPN clients, development tools, and any software that could reveal attack surface.
- Files: `personal/*.txt`, `office/*.txt`
- Current mitigation: a private Git host appears to be a private self-hosted instance. Access requires authentication.
- Recommendations: Verify the a private Git host repo is set to private. Rotate a private Git host credentials periodically. Consider whether the office machine catalogs (`office/` directory) fall under any employer data policies before committing to an external server.

**Hostname embedded in filenames and commit messages:**
- Risk: Machine hostnames (`computer-one.local`, `computer-two.local`, `computer-two.local`) are embedded in every filename and every commit message. These reveal machine naming conventions and network topology. All 128 commits include hostname data.
- Files: `update-list.sh` line 431, 478; all catalog files
- Current mitigation: Private a private Git host instance.
- Recommendations: If the repo is ever made public or shared, hostnames in git history cannot be removed without a full history rewrite.

**`git add "${TARGET_LOCATION}/archive/" 2>/dev/null || true` silences errors:**
- Risk: The `|| true` on line 421 means any git error (corrupted index, permissions issue, full disk) is silently ignored. Combined with the `&>/dev/null` on `git commit` at line 434, failures in the commit process produce no actionable output.
- Files: `update-list.sh` lines 421, 434
- Current mitigation: None.
- Recommendations: Remove silent error suppression from git operations. Let failures surface so they can be investigated.

## Performance Bottlenecks

**`brew list` is slow on large Homebrew installs:**
- Problem: `brew list --formula` and `brew list --cask` are called sequentially with no timeout. On machines with many packages, each can take 5–15 seconds.
- Files: `update-list.sh` lines 287–289
- Cause: Homebrew's `list` command verifies installation state for every package.
- Improvement path: No immediate fix; this is a Homebrew constraint. Could run both in parallel with `&` and `wait` if order in output file is not required.

## Fragile Areas

**Filename timestamp extraction uses regex on filename string:**
- Files: `update-list.sh` line 220
- Why fragile: `grep -oE '[0-9]{14}\.txt$' | cut -c1-8` extracts the 14-digit timestamp by finding a digit sequence at the end of the filename. If a hostname itself contained a 14-digit numeric sequence, the regex would match the wrong part of the filename. The pattern also silently skips any file that doesn't match (line 222–224) rather than aborting.
- Safe modification: Add an explicit filename pattern anchor or use a more specific regex that matches only the known `]-YYYYMMDDHHMMSS.txt` suffix.
- Test coverage: None.

**`archive_old_catalogs` uses string comparison for date math:**
- Files: `update-list.sh` lines 203, 230
- Why fragile: Dates are compared as integers (`[[ "$timestamp" -lt "$cutoff_date" ]]`) using YYYYMMDD strings. This works for well-formed dates but silently misbehaves if `timestamp` extraction returns an empty string (treated as 0, which is always less than cutoff, archiving every file) or a malformed value.
- Safe modification: Validate that `$timestamp` matches `[0-9]{8}` before the comparison.
- Test coverage: None.

**`cd "$SCRIPT_DIR"` side-effects persist within function scope:**
- Files: `update-list.sh` lines 357, 404
- Why fragile: Both `git_pull()` and `git_commit_and_push()` `cd` to `$SCRIPT_DIR` without using a subshell. In zsh, this changes the working directory of the calling scope. If either function returns early (the `return` on line 360 or 407), the subsequent function runs from an unexpected directory if the `cd` failed.
- Safe modification: Wrap git operations in a subshell `(cd "$SCRIPT_DIR" && ...)` or use `git -C "$SCRIPT_DIR"` throughout.
- Test coverage: None.

## Scaling Limits

**Git object count grows without packing:**
- Current capacity: 473 loose objects, 1.86 MiB, 128 commits.
- Limit: Loose object directories degrade `git status` and `git add` performance at high object counts (tens of thousands). At current growth rate (~2 commits/week across machines), this is a concern in 2–3 years without periodic `git gc`.
- Scaling path: Run `git gc --aggressive` periodically, or add a post-commit hook that packs objects after N new loose objects.

## Dependencies at Risk

**`mas` CLI is optional but silently degrades output:**
- Risk: `mas` is not a first-party Apple tool. It depends on App Store API internals that Apple does not document and has broken `mas` in past OS updates (e.g., macOS 12.x broke `mas list`).
- Impact: When broken, the App Store section is silently replaced with a single "mas is not installed" line, giving a false impression of completeness with no indication of failure vs. absence.
- Migration plan: Add a `mas` version check and explicit warning if the `mas list` output is empty or the exit code is non-zero after the pipe.

## Missing Critical Features

**No idempotency guard:**
- Problem: Running the script twice in the same second (or with the same `CURRENT_DATE`) would produce two identically-named files, with the second overwriting the first silently. The `>> "$OUTPUT_FILE"` append in `generate_catalog()` means if the file already exists (from a prior partial run), data is appended rather than overwritten.
- Blocks: Reliable re-runs after failures.

**No `--dry-run` mode:**
- Problem: There is no way to test the script's behavior without actually generating a catalog file and committing it to git.
- Blocks: Safe testing of the archive logic or git commit logic without producing real commits.

**Archive directory is not gitignored; it grows in the git object store permanently:**
- Problem: Once files are in `archive/`, they remain tracked objects in the git object store forever, even if the files themselves are later deleted from the archive. The archive directories in both `personal/archive/` and `office/archive/` together hold 116 committed catalog files that can never be removed without rewriting history.
- Blocks: Keeping the repo lean over the long term.

## Test Coverage Gaps

**No tests of any kind:**
- What's not tested: Archive date comparison logic, filename timestamp extraction regex, git staging behavior when files are archived, argument parsing edge cases, error handling paths.
- Files: `update-list.sh` (entire script)
- Risk: Any change to archiving logic, filename format, or git operations could silently break without detection.
- Priority: High for the archive/git staging bug; Medium for the rest given the personal-use scope of the tool.

---

*Concerns audit: 2026-06-12*
