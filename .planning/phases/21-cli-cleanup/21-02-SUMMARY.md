---
phase: 21-cli-cleanup
plan: "02"
subsystem: tests
tags: [test-migration, cli, argparse, identity]
dependency_graph:
  requires: [21-01]
  provides: [migrated-test-suite-for-new-cli]
  affects: [tests/test_identity.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns: [keyword-only-function-call, pytest-systemexit-assertion]
key_files:
  created: []
  modified:
    - tests/test_identity.py
    - tests/test_cli.py
decisions:
  - "test_naming.py confirmed unchanged — 'personal'/'office' strings are filename fixtures, not flag references"
  - "Three test_cli.py regression tests intentionally contain '--personal'/'--office'/'--machine' string literals to prove those flags are rejected by argparse; this is correct, not a dead-code violation"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-16"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 21 Plan 02: CLI Cleanup — Test Suite Migration — Summary

**One-liner:** Migrated test_identity.py and test_cli.py from the old four-param resolve_computer_selection signature and stale --personal/--office/--machine argparse tests to the new single-param form with three new regression tests proving the removed flags now error.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migrate TestResolveComputerSelection in test_identity.py | 8996583 | tests/test_identity.py |
| 2 | Update test_cli.py — remove stale flag tests, add removed-flag regression tests | 3feff40 | tests/test_cli.py |
| 3 | Full suite gate + static analysis | (no files changed) | tests/test_naming.py (confirmed unchanged) |

## What Was Built

**Task 1 — test_identity.py:**
- Removed 7 obsolete test methods from TestResolveComputerSelection: test_personal_resolves, test_office_resolves, test_machine_alias_resolves, test_mutual_exclusion_errors_on_two_flags_personal_office, test_mutual_exclusion_errors_on_computer_and_machine, test_invalid_machine_name_raises, test_empty_string_machine_treated_as_none
- Retained and updated 2 tests: test_invalid_computer_name_raises, test_empty_string_computer_treated_as_none — both now use `resolve_computer_selection(computer=...)` keyword-only form
- Renamed test_no_flag_returns_none_for_interactive → test_none_returns_none
- Renamed test_computer_alias_resolves → test_computer_resolves
- Added 3 new tests: test_valid_name_returned_unchanged, test_name_with_spaces_is_valid, test_none_returns_none_for_interactive_fallback
- Final class has 7 tests (down from 11)

**Task 2 — test_cli.py:**
- Removed 4 stale TestArgparse tests: test_mutual_exclusion_personal_office, test_machine_has_separate_dest, test_personal_and_computer_are_mutually_exclusive, test_machine_and_office_are_mutually_exclusive
- Added 3 new TestArgparse regression tests: test_personal_flag_is_unrecognized, test_office_flag_is_unrecognized, test_machine_flag_is_unrecognized — each asserts SystemExit(code=2) from argparse
- Removed 3 stale TestRenameFlag tests: test_rename_with_personal_exits, test_rename_with_office_exits, test_rename_with_machine_exits
- Kept test_rename_with_computer_exits unchanged
- _patch_run_dependencies default computer_name: "personal" → "MyMac"
- TestNoCommit (3 tests): argv --personal → --computer MyMac; folder path personal_dir → MyMac dir
- TestGenerateThenSweep (2 tests): argv --personal → --computer MyMac; select_computer mock return_value "personal" → "MyMac"; folder path references updated

**Task 3 — Verification gate:**
- pytest: 421 passed, 5 skipped, 0 failed
- ruff check: 0 errors
- mypy --strict on identity.py + cli.py: 0 errors
- test_naming.py: confirmed unchanged (no flag references — only "personal"/"office" as filename content fixtures)
- grep for removed-flag patterns in src/maccat/: 0 matches

## Verification Results

1. `pytest tests/ -x -q` — 421 passed, 5 skipped, 0 failures
2. `ruff check src/maccat/ tests/` — all checks passed
3. `mypy --strict src/maccat/identity.py src/maccat/cli.py` — success, 0 issues
4. grep for `args.personal|args.office|args.machine|personal=|office=` in src/maccat/ — no matches
5. Three new tests confirm `--personal`/`--office`/`--machine` each yield SystemExit(2)

## Deviations from Plan

None — plan executed exactly as written.

test_naming.py was confirmed unchanged as expected (no flag references present).

## Known Stubs

None — pure test migration, no new production code introduced.

## Threat Flags

None — no new trust boundaries introduced; tests use disposable_catalog_repo fixture throughout.

## Self-Check: PASSED

- tests/test_identity.py — exists, modified (8996583)
- tests/test_cli.py — exists, modified (3feff40)
- tests/test_naming.py — exists, unchanged (confirmed no edits needed)
- Commit 8996583 — Task 1 commit verified
- Commit 3feff40 — Task 2 commit verified
- pytest 421 passed — verified
- ruff clean — verified
- mypy clean — verified
