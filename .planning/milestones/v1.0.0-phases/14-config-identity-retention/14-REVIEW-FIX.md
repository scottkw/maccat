---
phase: 14-config-identity-retention
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/14-config-identity-retention/14-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/14-config-identity-retention/14-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (2 Critical + 6 Warning)
- Fixed: 8
- Skipped: 0

Scope was `critical_warning`, so the 4 Info findings (IN-01..IN-04) were not
in scope. Note: IN-02 (duplicated atomic TSV-write block) was nevertheless
resolved as a side effect of the CR-01 fix — both copies now route through a
single `_atomic_write_lines` helper.

All 8 in-scope findings were fixed. After all fixes:
- `PYTHONPATH=src ./venv/bin/pytest -q` → 193 passed (179 baseline + 14 new
  regression tests).
- `./venv/bin/ruff check src/maccat tests` → All checks passed.
- `./venv/bin/mypy --strict src/maccat` → only the known, accepted Phase-16
  `maccat.cli` stub import error in `__main__.py` remains; all files touched by
  this fix pass clean.

## Fixed Issues

### CR-01: `upsert_machine_label` header creation is NON-atomic

**Files modified:** `src/maccat/identity.py`, `tests/test_identity.py`
**Commit:** a4b1626
**Status:** fixed
**Applied fix:** Removed the separate non-atomic `write_text` header creation
plus read-after-write. The function now builds the complete desired content
(header if absent + merged entries) entirely in memory, then performs a single
atomic `mkstemp` + `rename` via a new `_atomic_write_lines(path, lines, tmp_dir)`
helper. The helper removes the temp file on any failure (`except BaseException`),
so a crash leaves at most a stray `.tmp` and never a partial `machine-labels.tsv`.
This matches the zsh original, which builds the whole file into one temp and
renames once. Regression tests assert (a) creation does not call `write_text` on
the TSV, and (b) a forced rename failure cleans the temp file and leaves the
original file untouched.

### CR-02: `prune_old_archives` lexicographic vs numeric comparison

**Files modified:** `src/maccat/retention.py`, `tests/test_retention.py`
**Commit:** aab5b0f
**Status:** fixed: requires human verification
**Applied fix:** Replaced the string `file_yyyymmdd < cutoff` with integer
comparison (`int(file_yyyymmdd) < int(cutoff)`), matching the zsh `-lt`
arithmetic (update-list.sh:1049). On an int-parse failure of either operand the
file is skipped with a warning, preserving the "cannot classify → never delete"
invariant on this destructive path. Verified against the zsh prune date math
(`cut -c1-8` → 8-char YYYYMMDD → `-lt` cutoff). This is a logic change on a
delete path; flagged for human confirmation of the comparison/boundary
semantics. Regression tests cover: an all-zero parseable date is still pruned,
and a non-numeric cutoff skips all files with a warning.

### WR-01: `prune_old_archives` `unlink()` has no error handling

**Files modified:** `src/maccat/retention.py`, `tests/test_retention.py`
**Commit:** aab5b0f
**Status:** fixed
**Applied fix:** Wrapped `f.unlink()` in `try/except OSError`; on failure it
prints `WARNING: Could not prune: {name} — leaving in place` and continues,
matching zsh's `rm`-guarded warn-and-continue (update-list.sh:1050-1055).
Regression test simulates an `OSError` on the first file's unlink and asserts no
exception escapes, a warning is printed, and the second file is still pruned (the
pass did not abort).

### WR-02: `select_computer` EOF/quit skips "No catalog written."

**Files modified:** `src/maccat/identity.py`, `tests/test_identity.py`
**Commit:** a4b1626
**Status:** fixed
**Applied fix:** EOF on the main menu now sets `choice = str(quit_idx)` and
breaks, routing through the existing Quit branch that prints "No catalog
written." then returns None — matching zsh (update-list.sh:425-426, 463-465).
Updated the step-5 docstring accordingly. Regression test feeds `EOFError` and
asserts the "No catalog written." message is printed and None is returned.

### WR-03: duplicated TSV-parsing logic / empty-label parity

**Files modified:** `src/maccat/identity.py`, `tests/test_identity.py`
**Commit:** a4b1626
**Status:** fixed
**Applied fix:** Added a single `_iter_tsv_entries(map_file)` reader that skips
blank lines, comment lines, lines without a TAB, and (matching zsh
update-list.sh:376) lines with an empty host OR empty label column. Refactored
`discover_computer_folders` and `select_computer`'s saved-folder lookup to use
it. (The `rename_machine` map-rewrite loop intentionally retains its own
verbatim-preserving rewrite logic — it must preserve comment/blank formatting,
which a data-only reader cannot do.) Regression tests cover comment/blank/no-tab
skipping, empty host/label skipping, missing-file → empty, and that
`discover_computer_folders` drops empty-label rows.

### WR-04: `rename_machine` folder move is unguarded

**Files modified:** `src/maccat/identity.py`, `tests/test_identity.py`
**Commit:** a4b1626
**Status:** fixed
**Applied fix:** Wrapped `old_dir.rename(new_dir)` in `try/except OSError`,
raising a clean `SystemExit` with an actionable "Could not rename folder ...
Nothing renamed." message instead of surfacing a traceback (covers EXDEV,
permission errors, and the clobber-check → rename race). Regression test forces
an `OSError` on the folder move and asserts a `SystemExit` with the actionable
message, that the old folder remains, and that the new folder is not created.

### WR-05: `SystemExit("\nAborted.")` leading-newline coupling

**Files modified:** `src/maccat/config.py`, `tests/test_config.py`
**Commit:** a8b86c6
**Status:** fixed
**Applied fix:** In both `config_init` and `resolve_archive_days`, the EOF
handler now `print()`s the prompt-terminating newline separately and raises a
clean `SystemExit("Aborted.")`, decoupling presentation from the exit value.
Updated the `config_init` docstring. Regression test asserts the exit value is
exactly `"Aborted."` with no leading newline (the existing substring test still
passes).

### WR-06: `_is_git_repo` too permissive (parent repo passes)

**Files modified:** `src/maccat/config.py`, `tests/test_config.py`
**Commit:** a8b86c6
**Status:** fixed
**Applied fix:** Switched from `git rev-parse --git-dir` (succeeds anywhere
inside any working tree, including a parent repo) to `git rev-parse
--show-toplevel`, and require its resolved output to equal the resolved input
path. This enforces that the catalog dir is the repo top-level — matching the zsh
tool's implicit SCRIPT_DIR-is-repo-root assumption — so auto-commit/push cannot
land in an unrelated parent repository. Regression tests cover: a subdir under a
parent git repo is rejected (both `_is_git_repo` False and `validate_catalog_repo`
SystemExit), and the repo top-level itself is accepted.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
