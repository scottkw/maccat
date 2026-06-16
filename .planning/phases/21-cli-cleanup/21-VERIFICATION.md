---
phase: 21-cli-cleanup
verified: 2026-06-16T00:00:00Z
status: passed
score: 4/4
overrides_applied: 0
---

# Phase 21: CLI Cleanup — Verification Report

**Phase Goal:** `--computer NAME` is the sole named-folder flag; `--personal`, `--office`, and `--machine` are completely removed from the codebase and all dead code paths are gone.
**Verified:** 2026-06-16
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--computer NAME` is the sole named-folder flag in the parser | VERIFIED | `_build_parser()` contains only one `group.add_argument` call — for `--computer`. `--help` output lists `--computer NAME` and no other selecting flags. |
| 2 | `--personal`, `--office`, `--machine` are absent from `src/maccat/` source (no dead code paths) | VERIFIED | `grep -rn -- "--personal\|--office\|--machine\|args\.personal\|args\.office\|args\.machine\|personal=\|office=\|machine=" src/maccat/` returns only one match: `naming.py:51: machine=m.group("machine")` — a regex named-group capture for the filename parser, not a CLI flag reference. Zero flag dead-code in production source. |
| 3 | Passing a removed flag produces a standard argparse "unrecognized arguments" error (exit 2) | VERIFIED | `python -m maccat --personal` → `maccat: error: unrecognized arguments: --personal`, exit 2. Same for `--office` (exit 2) and `--machine` (exit 2). |
| 4 | `resolve_computer_selection` signature is single-param `computer: str \| None` | VERIFIED | `inspect.signature(resolve_computer_selection).parameters` → `['computer']`. Function body: `if not computer: return None; validate_computer_name(computer); return computer`. |

**Score:** 4/4 truths verified

---

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| CLI-03: `--computer NAME` is the sole named-folder flag (non-interactive) | PASS | Parser contains only `--computer` in the mutually-exclusive group. `_build_parser().parse_args(['--computer', 'Laptop']).computer == 'Laptop'` — verified by `test_computer_has_own_dest`. |
| CLI-04: `--personal`, `--office`, `--machine` removed everywhere; passing removed flag yields argparse "unrecognized argument" error | PASS | Zero flag references in `src/maccat/`. `--personal`/`--office`/`--machine` each produce `SystemExit(code=2)` — verified live and by `test_personal_flag_is_unrecognized`, `test_office_flag_is_unrecognized`, `test_machine_flag_is_unrecognized`. |
| CLI-05: `--help` references only `--computer` for folder selection | PASS | `python -m maccat --help` output contains `--computer NAME` and no mention of `--personal`, `--office`, or `--machine`. Module docstring in `cli.py` Flags section lists `--computer` only. |
| CLI-06: `--rename`, `--no-commit`, `--archive-days`, `--catalog-dir`, and interactive `select_computer` behave as before (non-regression) | PASS | Full test suite: 420 passed, 5 skipped, 0 failed. Specific non-regression tests passing: `TestRenameFlag::test_rename_with_computer_exits`, `TestNoCommit` (3 tests), `TestGenerateThenSweep` (2 tests), `TestSelectComputer` (6 tests). |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/cli.py` | Argparse parser with `--computer` only; guards use `args.computer`; call site uses single keyword arg | VERIFIED | Parser has single `group.add_argument('--computer', ...)`. Config guard: `any([args.rename, args.computer])`. Rename guard: `args.rename and bool(args.computer)`. Call site: `resolve_computer_selection(computer=args.computer)`. |
| `src/maccat/identity.py` | `resolve_computer_selection(*, computer: str \| None) -> str \| None` — no `personal`, `office`, `machine` params | VERIFIED | Signature confirmed via introspection. Body is 3 lines: falsy-check, validate, return. Module docstring no longer contains stale `parse_arguments` zsh-analog row (fixed in commit `b52cf0c`). |
| `tests/test_cli.py` | Regression tests for removed flags; non-regression tests for surviving flags | VERIFIED | Three new tests (`test_personal_flag_is_unrecognized`, `test_office_flag_is_unrecognized`, `test_machine_flag_is_unrecognized`) assert `SystemExit(code=2)`. `test_rename_with_computer_exits` asserts `exc.value.code != 0` (strengthened in `b52cf0c`). |
| `tests/test_identity.py` | `TestResolveComputerSelection` uses keyword-only form; no old four-param calls | VERIFIED | All 6 test methods use `resolve_computer_selection(computer=...)`. Duplicate `test_none_returns_none_for_interactive_fallback` removed (fixed in `b52cf0c`). |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py:run()` | `identity.resolve_computer_selection` | `resolve_computer_selection(computer=args.computer)` | WIRED | Line 215 of `cli.py` — single keyword-only call site, no legacy params. |
| argparse rejected flags | `sys.exit(code=2)` | argparse unrecognized-argument path | WIRED | Verified live: all three removed flags produce exit code 2 and "unrecognized arguments" message. |

---

## Static Analysis

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Ruff | `./venv/bin/ruff check src/maccat/ tests/` | All checks passed | PASS |
| mypy --strict | `./venv/bin/mypy --strict src/maccat/` | Success: no issues found in 29 source files | PASS |
| Dead-code grep | `grep -rn "args.personal\|args.office\|args.machine\|personal=\|office=" src/maccat/` | No matches (only `naming.py:51` regex named-group, not a flag) | PASS |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--help` lists `--computer`, not removed flags | `python -m maccat --help` | Lists `--computer NAME` only for folder selection | PASS |
| `--personal` rejected with unrecognized-args error, exit 2 | `python -m maccat --personal` | `error: unrecognized arguments: --personal`, exit 2 | PASS |
| `--office` rejected with unrecognized-args error, exit 2 | `python -m maccat --office` | `error: unrecognized arguments: --office`, exit 2 | PASS |
| `--machine` rejected with unrecognized-args error, exit 2 | `python -m maccat --machine` | `error: unrecognized arguments: --machine`, exit 2 | PASS |
| `resolve_computer_selection` single-param signature | `inspect.signature(...)` | `['computer']` | PASS |
| Full test suite | `pytest tests/ -x -q` | 420 passed, 5 skipped, 0 failed | PASS |

---

## Anti-Patterns Found

None. No TBD/FIXME/XXX markers. No placeholder returns. No dead argument paths. The only `machine=` occurrence in `src/maccat/` is the regex named-group `m.group("machine")` in `naming.py` — this is filename parsing, not a CLI flag.

---

## Human Verification Required

None. All requirements are mechanically verifiable and confirmed by command output and test results.

---

## Gaps Summary

No gaps. All four requirements (CLI-03 through CLI-06) are fully satisfied. The codebase evidence — live `--help` output, live rejection of removed flags with exit code 2, signature introspection, 420 passing tests, zero ruff errors, zero mypy errors — independently confirms every claim in the SUMMARY.md files.

The REVIEW.md findings (WR-01 stale docstring, IN-01 duplicate test, IN-02 missing exit-code assertion) were all resolved in commit `b52cf0c` and `49e03bd` before this verification ran. The current codebase is clean of all three issues.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_
