---
phase: 16-git-cli-distribution
verified: 2026-06-14T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 16: Git CLI Distribution Verification Report

**Phase Goal:** The tool runs end-to-end from a `.pyz` zipapp against a user-configured catalog repo, with correct generate-then-sweep ordering, git integration, and all operational flags wired.
**Verified:** 2026-06-14
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `./maccat.pyz --help` and `./maccat.pyz --version` work from any directory with no `__file__`-relative path errors; the .pyz contains no `.so`/`.dylib` | VERIFIED | Built artifact runs `maccat 1.0.0` from `/tmp`; `--help` exits 0; zipfile inspection confirms 0 native libs across 34 entries; `cli.py:220` comments explicitly prohibit `__file__` resolution; `config.py:37` docstring confirms no `Path(__file__).parent` usage |
| 2 | A full run executes in order: git pull → generate catalog → retain newest → prune archives → git commit/push; the just-written catalog is never archived on the same run | VERIFIED | `cli.py:259-303` shows unconditional `git_pull` → `timestamp = datetime.now()` → catalog write → `retain_newest_per_host` → `prune_old_archives` → conditional `git_commit_and_push`; `TestGenerateThenSweep` (2 tests) exercise this in isolation with real retention running |
| 3 | `--no-commit` skips git while all disk operations (generate, retain, prune) still run | VERIFIED | `cli.py:226` sets `auto_commit = not args.no_commit`; retain (line 292) and prune (line 297) are unconditional; `git_commit_and_push` guarded at line 302 by `if auto_commit`; `git_pull` at line 259 is also unconditional (pull still runs); `TestNoCommit` (4 tests) assert this |
| 4 | `git add` uses `-- <pathspec>` so leading-dash folder names stage correctly; `--rename` produces a single commit staging old-folder deletes, new-folder adds, and map update | VERIFIED | `gitops.py:119,125,197,203,209` — every `git add` call includes `"--"` before the pathspec; `git_commit_rename` stages `old_name/`, `new_name/`, and `machine-labels.tsv` in a single commit at line 223; `identity.py:625-628` wires the deferred import and calls `gitops.git_commit_rename` when `auto_commit=True`; `TestGitCommitRename` + `TestRenameIdentityIntegration` cover both code paths |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/gitops.py` | git_pull, git_commit_and_push, git_commit_rename | VERIFIED | 252 lines; all three functions fully implemented; shell=False list-form args throughout; warn-and-continue on all failures |
| `src/maccat/cli.py` | argparse parser + end-to-end run orchestration | VERIFIED | 313 lines; `_build_parser()` + `run()` with 13-step NON-NEGOTIABLE order documented inline |
| `src/maccat/__main__.py` | Stub replaced with real `run()` call | VERIFIED | Line 19-21: `def main(): from maccat.cli import run; run()` — `NotImplementedError("Phase 16")` is gone |
| `src/maccat/identity.py:625-628` | Rename git commit wired | VERIFIED | `if auto_commit: from maccat import gitops; gitops.git_commit_rename(...)` |
| `scripts/build-pyz.sh` | Build script producing .pyz artifact | VERIFIED | 27 lines; `set -euo pipefail`; script-relative paths; correct `src/` source dir; `python3 -m zipapp` with `--main "maccat.__main__:main"` |
| `tests/test_gitops.py` | 10 tests for all three git functions | VERIFIED | 219 lines; TestGitPull (2), TestGitCommitAndPush (4), TestGitCommitRename (2), TestRenameIdentityIntegration (2); all pass |
| `tests/test_cli.py` | 28 tests for CLI orchestration | VERIFIED | 498 lines; all 28 tests pass; covers argparse, --no-commit, generate-then-sweep, config dispatch, quit path |
| `tests/test_pyz.py` | 5 PKG-03 smoke tests | VERIFIED | 149 lines; all 5 tests pass against the built artifact; skip guard active when .pyz absent |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__main__.py` | `cli.run()` | deferred import `from maccat.cli import run` | WIRED | Line 20-21 |
| `cli.run()` | `gitops.git_pull` | `from maccat import gitops; gitops.git_pull(catalog_repo)` | WIRED | Lines 153, 259 |
| `cli.run()` | `gitops.git_commit_and_push` | same module import; line 303 | WIRED | Lines 153, 303 |
| `cli.run()` | `retain_newest_per_host` | `from maccat.retention import ...` at line 171 | WIRED | Line 292 |
| `cli.run()` | `prune_old_archives` | same import | WIRED | Line 297 |
| `identity.rename_machine` | `gitops.git_commit_rename` | deferred `from maccat import gitops` at line 627 | WIRED | Lines 626-628 |
| `.pyz` → `maccat.__main__:main` | invoked as zipapp entry point | `--main "maccat.__main__:main"` in build-pyz.sh line 24 | WIRED | Confirmed via subprocess test from /tmp |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no UI/rendering components. All artifacts are CLI orchestration, git subprocess wrappers, and build tooling. Data flows through subprocess calls to actual git processes and disk writes; both are confirmed by test_gitops.py running against real disposable git repos.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--version` from unrelated cwd | `cd /tmp && /path/to/maccat.pyz --version` | `maccat 1.0.0` (exit 0) | PASS |
| `--help` from unrelated cwd | `cd /tmp && /path/to/maccat.pyz --help` | usage text (exit 0) | PASS |
| No native libs in archive | zipfile.namelist() scan | 0 `.so`/`.dylib` across 34 entries | PASS |
| Full test suite | `PYTHONPATH=src ./venv/bin/pytest -q` | 400 passed, 0 failed | PASS |
| mypy --strict | `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` | Success: no issues found in 29 source files | PASS |

### Probe Execution

No probe scripts declared in PLAN frontmatter. No `scripts/*/tests/probe-*.sh` present. Behavioral spot-checks above cover the equivalent ground.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PKG-03 | 16-03 | `.pyz` zipapp runnable from any directory, no `__file__`-relative catalog resolution, no native libs | SATISFIED | Build confirmed; `--version`/`--help` from `/tmp`; 0 `.so`/`.dylib`; `cli.py` explicitly prohibits `__file__` fallback; 5 smoke tests all pass |
| PKG-05 | 16-02 | `--version` and `--help` flags | SATISFIED | argparse `action="version"` at cli.py:52-55; `--help` implicit; both confirmed via subprocess from unrelated cwd |
| OPS-06 | 16-01 | Git pull → generate → commit/push as single commit; `--no-commit` skips git, disk ops still run | SATISFIED | Orchestration order in cli.py:259-303; `--` pathspec safety in gitops.py; `--no-commit` guard at line 302; 4 TestNoCommit tests confirm |

All 3 phase-16 requirements satisfied. No orphaned requirements found (REQUIREMENTS.md traceability table maps PKG-03, PKG-05, OPS-06 exclusively to Phase 16).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found |

Scan results: zero TBD/FIXME/XXX markers in any phase-16-touched file. Zero stub patterns (`NotImplementedError`, `return {}`, `return []`). The `NotImplementedError("Phase 16")` that existed in `__main__.py` is confirmed removed.

### Human Verification Required

None. All behaviors are fully verifiable programmatically:
- Zipapp execution confirmed via subprocess from isolated cwd
- Git ordering confirmed via call-order side-effect tests
- `--no-commit` confirmed via mock-assert tests
- `--rename` single-commit staging confirmed via git log inspection in test

### Gaps Summary

No gaps. All four must-have truths are VERIFIED by codebase evidence. All three requirement IDs are satisfied. All 7 SUMMARY-claimed commits exist in git history. Full test suite passes (400/400). mypy --strict clean on all 29 source files.

---

_Verified: 2026-06-14_
_Verifier: Claude (gsd-verifier)_
