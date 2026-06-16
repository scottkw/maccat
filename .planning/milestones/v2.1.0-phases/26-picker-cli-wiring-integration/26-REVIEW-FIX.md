---
phase: 26-picker-cli-wiring-integration
fixed_at: 2026-06-16T00:00:00Z
review_path: .planning/phases/26-picker-cli-wiring-integration/26-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 26: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/26-picker-cli-wiring-integration/26-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Warnings; Info IN-01/IN-02 out of critical_warning scope)
- Fixed: 4
- Skipped: 0

All fixes were applied in an isolated git worktree, verified with
`PYTHONPATH=src pytest` (548 passed, 5 skipped), `MYPYPATH=src mypy --strict`
(clean), and `ruff check` (clean). The 13-step gen path was not touched, no
subprocess execution of the generated script was added, and
`catalog/format.py`, `reinstall/parser.py`, and `reinstall/emitter.py` were
left unmodified.

## Fixed Issues

### WR-03: `maccat reinstall --computer NAME` failed with "unrecognized arguments"

**Files modified:** `src/maccat/cli.py`
**Commit:** d9f0d2d
**Applied fix:** Added a `--computer NAME` argument to the `reinstall`
subparser (sharing `dest="computer"` with the top-level flag) so the
documented post-subcommand placement parses instead of erroring. The
subparser flag uses `default=argparse.SUPPRESS` — a plain `default=None`
would clobber a value set by the pre-subcommand top-level flag back to None
during subparser parsing. With SUPPRESS, precedence is clean and explicit:
`maccat reinstall --computer X` -> X (now works), `maccat --computer Y
reinstall` -> Y (still works, value survives), both given -> the
post-subcommand value wins. The top-level `default=None` guarantees
`args.computer` is always present. Precedence is documented in the subparser
flag's `--help` text. Verified by namespace inspection across all four cases.

### WR-01: Unreadable `--from` file crashed with a raw `PermissionError` traceback

**Files modified:** `src/maccat/reinstall/picker.py`, `src/maccat/reinstall/cli.py`, `tests/reinstall/test_picker_and_reinstall_cli.py`
**Commit:** 481b2d5
**Applied fix:** `Path.is_file()` returns `True` for a file the user cannot
read (mode `0o000`), so the `--from` branch previously let
`parse_catalog -> read_text` raise an uncaught `PermissionError`. Added an
`os.access(p, os.R_OK)` readability probe in `resolve_catalog_path`'s `--from`
branch that exits with `ERROR: Catalog file is not readable: {p}`. As a
catch-all (covering picker-resolved catalogs too), wrapped `parse_catalog` in
`run_reinstall` to convert `OSError` into `sys.exit("ERROR: ...")`. Added a
`0o000`-chmod unit test guarded with `skipif(os.geteuid() == 0)` (root bypasses
permission checks). Also removed two pre-existing unused imports (`sys`,
`MagicMock`) from the touched test file so it stays ruff-clean.

### WR-04: Picker-mode reinstall mutated the catalog repo (mkdir + machine-labels.tsv)

**Files modified:** `src/maccat/reinstall/picker.py`
**Commit:** 924cf44
**Applied fix:** Reinstall is read-only, but the picker branch reused
`select_computer`, whose flag path `mkdir`s the folder and `upsert`s
`machine-labels.tsv`, and which on an unknown name left a stray empty
directory before exiting with "No catalog files found". Restructured the
picker branch: when `--computer NAME` is supplied, the name is resolved
against existing folders via `discover_computer_folders(catalog_repo)` and an
unknown name fails cleanly with `ERROR: No catalog folder named ...` WITHOUT
creating a folder or rewriting the TSV. The interactive (no `--computer`)
path still uses `select_computer` per the locked CONTEXT decision; its
no-catalog-in-folder case is handled cleanly by `_find_newest_catalog`. This
keeps the existing picker for genuine interactive selection (honoring CONTEXT)
while eliminating the surprising mutation/stray-artifact for the scriptable
named path.

### WR-02: Picker-mode dispatch (step 4d) had no integration test through `run()`

**Files modified:** `tests/reinstall/test_reinstall_cli.py`
**Commit:** 83c8285
**Applied fix:** Added integration tests that drive `cli.run()` in picker mode
(no `--from`), locking the 4c (repo resolve/validate) + 4d (`run_reinstall`
threading `catalog_repo`) wiring that the existing `--from` tests never
reached: (a) `select_computer` stubbed to return a folder with two catalogs,
asserting `reinstall.sh` provenance names the NEWEST one; (b) picker-quit
(`select_computer -> None`) writes no file and returns cleanly. The same
appended test block also carries the WR-03 `--computer`-after-subcommand
parse/precedence cases (including a `run()`-level forwarding check) and the
WR-04 unknown-`--computer` clean-failure / no-stray-dir / no-TSV-mutation
assertion. These were committed together because the additions form a single
contiguous append-only hunk in the test file that cannot be split by
`git add -p`.

## Notes on Info findings (out of scope)

- **IN-01** (non-deterministic tie-break in `_find_newest_catalog` when two
  catalogs share an identical timestamp): not addressed — Info severity,
  outside `critical_warning` scope.
- **IN-02** (duplicated `--rename`+reinstall guard string at cli.py 4b/4d):
  not addressed — Info severity, outside scope.

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
