---
phase: 16-git-cli-distribution
plan: 01
subsystem: infra
tags: [git, subprocess, shell=False, gitops, identity, rename]

# Dependency graph
requires:
  - phase: 14-config-identity-retention
    provides: rename_machine function with auto_commit stub at line 625
provides:
  - git_pull, git_commit_and_push, git_commit_rename in src/maccat/gitops.py
  - identity.py:625 stub wired via deferred local import of gitops
  - tests/test_gitops.py with 10 tests covering all three git functions
affects: [16-02-cli, 16-03-zipapp, 17-parity-safety]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "subprocess list-form shell=False cwd=catalog_repo — mirrors zsh cd $SCRIPT_DIR pattern"
    - "shutil.which guard before all public git functions — mirrors homebrew.available() pattern"
    - "warn-and-continue: all git failures print WARNING and return, never raise"
    - "'--' before every pathspec in git add — T-16-01 leading-dash folder safety"
    - "deferred local import of gitops inside rename_machine body — avoids circular import"

key-files:
  created:
    - src/maccat/gitops.py
    - tests/test_gitops.py
  modified:
    - src/maccat/identity.py

key-decisions:
  - "git add uses '--' end-of-options marker before every pathspec; trailing slash on folder paths (zsh:2397 byte parity)"
  - "No check=True on any git subprocess call — all failures warn-and-continue per zsh || true / 2>/dev/null"
  - "bare 'git pull' only — no --rebase, no strategy flags (zsh:2346 parity)"
  - "deferred import 'from maccat import gitops' inside rename_machine body avoids top-level circular import"
  - "TestRenameIdentityIntegration monkeypatches gitops_mod.git_commit_rename at the module level (not identity.gitops) to intercept the deferred import"

patterns-established:
  - "Pattern: git subprocess list-form, cwd=catalog_repo replaces zsh's 'cd $SCRIPT_DIR' before each git call"
  - "Pattern: _git_available() + _is_git_repo() private helpers deduplicate the guard logic across all three public functions"

requirements-completed: [OPS-06]

# Metrics
duration: 4min
completed: 2026-06-15
---

# Phase 16 Plan 01: gitops.py + identity.py:625 Rename Commit Summary

**stdlib subprocess git integration with shell=False list-form args, '--' pathspec safety, and warn-and-continue behavior mirroring zsh:2327/2374/867**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-15T02:09:36Z
- **Completed:** 2026-06-15T02:13:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `src/maccat/gitops.py` with `git_pull`, `git_commit_and_push`, `git_commit_rename` — all three mirror zsh byte/behavior spec (lines 2327, 2374, 867)
- Wired `identity.py:625` stub to call `gitops.git_commit_rename` via deferred local import when `auto_commit=True`
- 10 tests in `tests/test_gitops.py` (TDD RED→GREEN) prove: `--` present in every git add; warn-and-continue on push failure / no remote; no-op guard skips empty commit; rename commit stages old+new+TSV

## Task Commits

1. **Task 1 RED: Failing tests for gitops.py** - `ff83b6f` (test)
2. **Task 1 GREEN: gitops.py implementation** - `072853b` (feat)
3. **Task 2: Wire identity.py stub + finalize tests** - `b7cc9e7` (feat)

## Files Created/Modified

- `/Users/ken/dev/mac-software-list/src/maccat/gitops.py` — git_pull, git_commit_and_push, git_commit_rename; all subprocess calls shell=False list-form cwd=catalog_repo
- `/Users/ken/dev/mac-software-list/src/maccat/identity.py` — line 625 stub replaced with deferred import + gitops.git_commit_rename call
- `/Users/ken/dev/mac-software-list/tests/test_gitops.py` — 10 tests: TestGitPull (2), TestGitCommitAndPush (4), TestGitCommitRename (2), TestRenameIdentityIntegration (2)

## Decisions Made

- `_git_available()` and `_is_git_repo()` extracted as private helpers to share guard logic across all three public functions — avoids repeating the 6-line pattern three times
- `git_commit_rename` does not print the header banner (no separator output) since it's called silently from within `rename_machine`; only `git_pull` and `git_commit_and_push` print banners
- TestRenameIdentityIntegration uses `monkeypatch.setattr(gitops_mod, "git_commit_rename", ...)` targeting the module object (not `identity.gitops`) so the mock intercepts the deferred import correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Integration test fixture used wrong filename pattern**
- **Found during:** Task 1 (TestRenameIdentityIntegration GREEN phase)
- **Issue:** Tests seeded `personal/catalog.txt` but `discover_computer_folders` looks for `mac-software-list-*.txt`; test found "No computers found", making auto_commit=True path untestable
- **Fix:** Extracted `_seed_catalog_repo()` helper that uses `make_catalog_filename` to create a properly-named catalog file; both integration tests use it
- **Files modified:** tests/test_gitops.py
- **Verification:** `test_auto_commit_true_calls_git` passes (len(calls) == 1)
- **Committed in:** b7cc9e7 (Task 2 commit)

**2. [Rule 1 - Bug] E501 line-length violations in test_gitops.py**
- **Found during:** Task 2 ruff check
- **Issue:** 4 method signatures exceeded 100-char line limit (pytest.CaptureFixture[str] on one line)
- **Fix:** Split long signatures across two lines
- **Files modified:** tests/test_gitops.py
- **Verification:** `ruff check` clean
- **Committed in:** b7cc9e7 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes required for correctness. No scope creep.

## Issues Encountered

None — plan executed with expected issues only (the TDD RED→GREEN flow exposed the fixture bug before production code was written).

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — all git functions are fully implemented. The identity.py stub has been wired.

## Next Phase Readiness

- `gitops.py` exports `git_pull`, `git_commit_and_push`, `git_commit_rename` — ready for use by `cli.py` (Plan 16-02)
- `rename_machine(catalog_repo, auto_commit=True)` now performs the git commit after folder rename
- All 361 tests pass; mypy --strict + ruff clean on all touched files

---
*Phase: 16-git-cli-distribution*
*Completed: 2026-06-15*
