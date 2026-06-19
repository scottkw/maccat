---
phase: "30-markdown-emitter-md-plumbing"
plan: 2
subsystem: naming/retention/identity/tests
tags: [extension-change, glob, naming, retention, identity, file-io, md-plumbing]
dependency_graph:
  requires: []
  provides: [".md filename convention", ".md retention globs", ".md identity discovery globs", "test assertions aligned to .md"]
  affects: ["src/maccat/naming.py", "src/maccat/retention.py", "src/maccat/identity.py", "tests/test_naming.py", "tests/test_safety_invariants.py"]
tech_stack:
  added: []
  patterns: ["glob string swap (txt→md, 5 sites)", "regex extension swap (1 site)"]
key_files:
  created: []
  modified:
    - src/maccat/naming.py
    - src/maccat/retention.py
    - src/maccat/identity.py
    - tests/test_naming.py
    - tests/test_safety_invariants.py
decisions:
  - "txt→md extension is a replace-not-duplicate change; stray .txt files become invisible to .md globs (FILE-01)"
  - "test_safety_invariants.py invariant preserved: literal filename updated to .md so the glob-matches-but-unparseable branch still fires"
metrics:
  duration: "7 minutes"
  completed: "2026-06-18"
  tasks_completed: 2
  files_modified: 5
---

# Phase 30 Plan 2: `.txt` → `.md` Extension Plumbing Summary

**One-liner:** Regex, format string, and five glob sites changed from `.txt` to `.md` across naming.py, retention.py, and identity.py; test assertions updated to match.

## What Was Built

Moved the filename extension and all glob patterns from `.txt` to `.md` (requirements FILE-01, MD-01):

- **`src/maccat/naming.py`:** `_FILENAME_RE` regex `\.txt$` → `\.md$`; `make_catalog_filename` f-string `.txt` → `.md`; module docstring and return-value docstring updated.
- **`src/maccat/retention.py`:** Three glob sites changed to `mac-software-list-*.md` (lines 64, 75 in `retain_newest_per_host`; line 118 in `prune_old_archives`). Docstrings at lines 41 and 96 updated.
- **`src/maccat/identity.py`:** Two glob sites changed to `mac-software-list-*.md` (line 158 `discover_computer_folders`; line 549 `rename_machine` rewrite loop). Line 144 docstring updated.
- **`tests/test_naming.py`:** All literal `.txt` filename arguments and expected values updated to `.md` (lines 20, 25, 30, 35, 41, 59, 63, 67, 76, 80, 86, 109). Round-trip tests auto-inherit via `make_catalog_filename`.
- **`tests/test_safety_invariants.py`:** Literal filename at line 60 changed to `mac-software-list-[alpha]-2026.md` so the file matches the `*.md` glob but still fails `parse_catalog_filename` (4-digit timestamp); surrounding comments updated to reference `*.md`.

## Verification

All success criteria met:

- `make_catalog_filename("x","20260614120000")` returns `"mac-software-list-[x]-20260614120000.md"` ✓
- `parse_catalog_filename("mac-software-list-[x]-20260614120000.txt")` is `None` ✓
- `parse_catalog_filename("mac-software-list-[x]-20260614120000.md")` is not `None` ✓
- All three retention.py glob strings are `"mac-software-list-*.md"` ✓
- Both identity.py glob strings are `"mac-software-list-*.md"` ✓
- 88 tests passing (test_naming.py, test_retention.py, test_safety_invariants.py, test_identity.py) ✓
- ruff + mypy --strict clean on all three modified source files ✓

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update naming.py, retention.py, identity.py glob sites | f41f843 | src/maccat/naming.py, src/maccat/retention.py, src/maccat/identity.py |
| 2 | Update test_naming.py and test_safety_invariants.py assertions | da8a6bc | tests/test_naming.py, tests/test_safety_invariants.py |

## Deviations from Plan

None — plan executed exactly as written. The worktree uses the main repo's venv via editable install; tests were run with `PYTHONPATH` pointing to the worktree `src/` directory to pick up worktree changes, which is the correct behavior for parallel-wave execution.

## Known Stubs

None.

## Threat Flags

None. The glob change is narrower than before (`.md` only); legacy `.txt` files are invisible to the new glob (not touched, not deleted) — T-30-05 mitigation confirmed.

## Self-Check: PASSED

- src/maccat/naming.py: modified ✓
- src/maccat/retention.py: modified ✓
- src/maccat/identity.py: modified ✓
- tests/test_naming.py: modified ✓
- tests/test_safety_invariants.py: modified ✓
- Task 1 commit f41f843: exists ✓
- Task 2 commit da8a6bc: exists ✓
- No stray `mac-software-list-*.txt` glob strings in source files ✓
