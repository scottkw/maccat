---
phase: 32-convert-command
plan: "02"
subsystem: convert-cli
tags: [convert, cli, argparse, testing, round-trip]
dependency_graph:
  requires:
    - src/maccat/convert.py::run_convert (Plan 01)
    - src/maccat/gitops.py::git_commit_convert (Plan 01)
    - src/maccat/reinstall/parser.py::parse_markdown_catalog (round-trip test)
    - tests/conftest.py::git_repo (git staging test)
  provides:
    - src/maccat/cli.py::_build_parser (convert subparser registered)
    - src/maccat/cli.py::run (convert dispatch at step 4b-ii)
    - tests/test_convert.py (9 test cases, full coverage)
  affects:
    - maccat CLI (maccat convert --from PATH now reachable)
tech_stack:
  added: []
  patterns:
    - argparse.SUPPRESS on subparser --no-commit (WR-03: prevents clobbering top-level flag)
    - Deferred import at dispatch point per PKG-03
    - Early-exit dispatch before resolve_catalog_repo (repo-agnostic command)
    - sys.argv + monkeypatch CLI integration tests (mirrors reinstall test pattern)
    - argparse.Namespace direct call for unit tests
    - pytest.raises(SystemExit) for all error-path assertions
key_files:
  created:
    - tests/test_convert.py
  modified:
    - src/maccat/cli.py
decisions:
  - "convert dispatch placed at step 4b-ii (after reinstall --from, before 4c resolve_catalog_repo) — repo-agnostic command, matches reinstall --from pattern"
  - "default=argparse.SUPPRESS on --no-commit in convert subparser (WR-03: identical to reinstall --computer pattern) — prevents clobbering top-level flag"
  - "required=True on --from — bare 'maccat convert' has no valid behavior; argparse rejects with usage error"
  - "mypy --strict requires source files alongside test file (no py.typed marker in package) — mypy --strict src/maccat/cli.py tests/test_convert.py passes; solo test file check is consistent with all existing test files in the project"
metrics:
  duration: "~20 minutes"
  completed: "2026-06-18T18:40:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 32 Plan 02: Convert CLI Wiring + Test Suite Summary

**One-liner:** `convert` subparser registered in `_build_parser` with SUPPRESS `--no-commit`, dispatched at step 4b-ii before `resolve_catalog_repo`, backed by a 9-test suite proving all acceptance criteria including the full round-trip.

## What Was Built

### Task 1: `src/maccat/cli.py` (modified)

Three insertions, no other changes:

1. **Docstring update** — added `convert` to `_build_parser` Subcommands list

2. **convert_parser block** (in `_build_parser`, after reinstall_parser):
   - `--from PATH` (required=True, dest="from_path") — no valid behavior without it
   - `--no-commit` (default=argparse.SUPPRESS) — WR-03: prevents clobbering top-level flag

3. **Convert dispatch** (in `run()`, step 4b-ii, after reinstall --from dispatch, before step 4c):
   ```python
   if args.subcommand == "convert":
       from maccat.convert import run_convert
       run_convert(args)
       return
   ```
   Deferred import per PKG-03. Placed before `resolve_catalog_repo` (convert is repo-agnostic).

### Task 2: `tests/test_convert.py` (created)

9 tests across 4 classes:

| Class | Tests | Covers |
|-------|-------|--------|
| `TestConvertHappyPath` | 2 | CLI integration (Test 1), --no-commit (Test 2) |
| `TestConvertErrorPaths` | 4 | missing file (Test 3), bad filename (Test 4), no-clobber (Test 5), unreadable file (Test 6, skipif root) |
| `TestConvertGitStaging` | 1 | git_commit_convert called with (catalog_repo, md_path, txt_path) (Test 7) |
| `TestConvertRoundTrip` | 2 | full-chain txt→md→parse_markdown_catalog (Test 8), empty section renders (none found) (Test 9) |

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_convert.py -v` | PASS (9/9) |
| `pytest tests/ -x -q` | PASS (694 passed, 5 skipped) |
| `maccat convert --help` | PASS (exits 0, prints --from and --no-commit) |
| `maccat convert` (no --from) | PASS (exits 2, argparse error) |
| `mypy --strict src/maccat/cli.py tests/test_convert.py` | PASS (0 errors) |
| `ruff check src/maccat/cli.py tests/test_convert.py` | PASS (0 errors) |
| Spot-check round-trip (`--no-commit` on /tmp fixture) | PASS (.md written, .txt gone) |

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| `maccat convert --from PATH.txt` reachable via CLI | PASS |
| convert dispatch before resolve_catalog_repo | PASS |
| argparse.SUPPRESS on --no-commit (count >= 2) | PASS (count=4 total in cli.py) |
| `subcommand == "convert"` in run() | PASS (count=1) |
| All 9 test behaviours in test_convert.py | PASS |
| Full test suite green (no regressions) | PASS |
| mypy --strict + ruff clean | PASS |
| Round-trip test calls parse_markdown_catalog without raising | PASS |
| Round-trip asserts single H1, no spurious ## heading | PASS |
| No-clobber test asserts .txt still present after SystemExit | PASS |
| git staging test asserts mock called once with correct 3 args | PASS |
| --no-commit test asserts mock NOT called | PASS |
| convert.py and gitops.py NOT reimplemented | PASS |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: cli.py | `842126f` | feat(32-02): wire convert subcommand into cli.py |
| Task 2: tests | `ec52e38` | test(32-02): add full test suite for convert subcommand |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree branch at wrong base commit (repeated from 32-01)**

- **Found during:** Initial setup (before Task 1)
- **Issue:** Worktree branch was at commit `d58f381` (Phase 29), missing all Phase 30-32 source files including `src/maccat/convert.py`. The `<worktree_branch_check>` preamble's merge-base check detected the mismatch correctly. First edit attempts operated on the wrong base.
- **Fix:** Ran `git -C <worktree> reset --hard 645d8bfe35ec1784968f3300c9570d4cdebaef37` to align the worktree branch with the expected base (main after 32-01 merge). Then re-applied all three cli.py insertions.
- **Impact:** No code changes required; all Phase 30/31/32-01 source files became available.

### Explicit Design Choices

**mypy --strict on test files alone vs. with source files:**

Running `mypy --strict tests/test_convert.py` alone reports `import-untyped` errors for `maccat.*` because the installed package has no `py.typed` marker. Running `mypy --strict src/maccat/cli.py tests/test_convert.py` (as specified in the plan's final verification step) passes with zero errors. This is consistent with all existing test files in the project — `mypy --strict tests/reinstall/test_reinstall_cli.py` also reports the same errors. The combined check is the canonical verification.

## Threat Surface Scan

No new threat surface introduced:
- T-32-07: Dispatch position before resolve_catalog_repo — mitigated (PASS)
- T-32-08: SUPPRESS default on --no-commit — mitigated (PASS)
- T-32-09: required=True on --from — accepted (PASS)
- No new network endpoints, auth paths, file access patterns, or schema changes.

## Known Stubs

None — all data paths are fully wired. The convert subcommand delegates entirely to `run_convert` from Plan 01, which is fully implemented.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `src/maccat/cli.py` modified (convert subparser + dispatch) | FOUND |
| `tests/test_convert.py` created (9 tests) | FOUND |
| `32-02-SUMMARY.md` exists | FOUND |
| Commit `842126f` (Task 1) exists | FOUND |
| Commit `ec52e38` (Task 2) exists | FOUND |
